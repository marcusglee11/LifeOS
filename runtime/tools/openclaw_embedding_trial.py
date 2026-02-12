#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

SUPPORTED_PROVIDERS = ("local", "openai", "gemini", "voyage")
DEFAULT_QUERY = "lobster-memory-seed-001"


def utc_ts_compact() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _provider_model_key(provider: str) -> Tuple[str, str]:
    if provider == "local":
        return "local", "modelPath"
    if provider in {"openai", "gemini", "voyage"}:
        return provider, "model"
    raise ValueError(f"unsupported provider: {provider}")


def build_trial_config(base_cfg: Mapping[str, Any], provider: str, model: str | None) -> Dict[str, Any]:
    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(f"unsupported provider: {provider}")

    cfg = copy.deepcopy(dict(base_cfg))
    agents = cfg.get("agents")
    if not isinstance(agents, dict):
        agents = {}
        cfg["agents"] = agents

    defaults = agents.get("defaults")
    if not isinstance(defaults, dict):
        defaults = {}
        agents["defaults"] = defaults

    memory = defaults.get("memorySearch")
    if not isinstance(memory, dict):
        memory = {}

    memory["enabled"] = True
    memory["provider"] = provider
    memory["fallback"] = "none"
    memory["sources"] = ["memory"]

    query = memory.get("query")
    if not isinstance(query, dict):
        query = {}
    hybrid = query.get("hybrid")
    if not isinstance(hybrid, dict):
        hybrid = {}
    hybrid["enabled"] = True
    query["hybrid"] = hybrid
    memory["query"] = query

    cache = memory.get("cache")
    if not isinstance(cache, dict):
        cache = {}
    cache["enabled"] = True
    memory["cache"] = cache

    sync = memory.get("sync")
    if not isinstance(sync, dict):
        sync = {}
    sync["watch"] = True
    memory["sync"] = sync

    if model:
        section_key, model_key = _provider_model_key(provider)
        section = memory.get(section_key)
        if not isinstance(section, dict):
            section = {}
        section[model_key] = model
        memory[section_key] = section

    defaults["memorySearch"] = memory
    return cfg


def _write_json_0600(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def _run_capture(cmd: List[str], timeout_sec: int, env: Mapping[str, str], out_path: Path) -> int:
    try:
        proc = subprocess.run(
            cmd,
            env=dict(env),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_sec,
            check=False,
        )
        out_path.write_text(proc.stdout, encoding="utf-8")
        return int(proc.returncode)
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        out_path.write_text(f"{output}\n[timeout]={timeout_sec}\n", encoding="utf-8")
        return 124


def _extract_hits(raw: str) -> List[str]:
    pattern = re.compile(r"(^|[ \t])([^\s:]+:[0-9]+-[0-9]+)\b", re.MULTILINE)
    return sorted({m.group(2) for m in pattern.finditer(raw)})


def run_trial(
    base_config_path: Path,
    out_dir: Path,
    provider: str,
    model: str | None,
    agent: str,
    query: str,
    timeout_sec: int,
    run_index: bool,
    keep_overlay: bool,
) -> Tuple[int, Dict[str, Any]]:
    cfg = json.loads(base_config_path.read_text(encoding="utf-8"))
    overlay_cfg = build_trial_config(cfg, provider=provider, model=model)

    out_dir_effective = out_dir
    out_dir_note = ""
    try:
        out_dir_effective.mkdir(parents=True, exist_ok=True)
        os.chmod(out_dir_effective, 0o700)
    except PermissionError:
        out_dir_effective = Path("/tmp/openclaw-embedding-trials") / utc_ts_compact()
        out_dir_effective.mkdir(parents=True, exist_ok=True)
        os.chmod(out_dir_effective, 0o700)
        out_dir_note = "out_dir_fallback:/tmp/openclaw-embedding-trials"

    overlay_path = out_dir_effective / "openclaw_embedding_trial_overlay.json"
    _write_json_0600(overlay_path, overlay_cfg)

    status_out = out_dir_effective / "memory_status_deep.txt"
    index_out = out_dir_effective / "memory_index_verbose.txt"
    search_out = out_dir_effective / "memory_search.txt"
    summary_out = out_dir_effective / "summary.json"

    cmd_env = dict(os.environ)
    cmd_env["OPENCLAW_CONFIG_PATH"] = str(overlay_path)
    cmd_env["OPENCLAW_EMBED_TRIAL_PROVIDER"] = provider
    if model:
        cmd_env["OPENCLAW_EMBED_TRIAL_MODEL"] = model

    rc_status = _run_capture(
        ["coo", "openclaw", "--", "memory", "status", "--deep", "--agent", agent],
        timeout_sec=timeout_sec,
        env=cmd_env,
        out_path=status_out,
    )

    rc_index = 0
    if run_index:
        rc_index = _run_capture(
            ["coo", "openclaw", "--", "memory", "index", "--agent", agent, "--verbose"],
            timeout_sec=timeout_sec,
            env=cmd_env,
            out_path=index_out,
        )
    else:
        index_out.write_text("index_skipped=true\n", encoding="utf-8")

    rc_search = _run_capture(
        ["coo", "openclaw", "--", "memory", "search", query, "--agent", agent],
        timeout_sec=timeout_sec,
        env=cmd_env,
        out_path=search_out,
    )

    hits = _extract_hits(search_out.read_text(encoding="utf-8", errors="replace"))
    passed = rc_status == 0 and rc_search == 0 and (not run_index or rc_index == 0) and len(hits) > 0

    summary = {
        "ts_utc": utc_ts_compact(),
        "provider": provider,
        "model": model or "provider_default",
        "agent": agent,
        "query": query,
        "run_index": bool(run_index),
        "status_exit": rc_status,
        "index_exit": rc_index,
        "search_exit": rc_search,
        "hit_count": len(hits),
        "hits": hits,
        "status_out": str(status_out),
        "index_out": str(index_out),
        "search_out": str(search_out),
        "overlay_path": str(overlay_path),
        "out_dir_requested": str(out_dir),
        "out_dir_effective": str(out_dir_effective),
        "notes": out_dir_note,
        "pass": bool(passed),
    }

    overlay_deleted = False
    if not keep_overlay:
        try:
            overlay_path.unlink(missing_ok=True)
            overlay_deleted = True
        except Exception:
            overlay_deleted = False
    summary["overlay_deleted"] = overlay_deleted

    summary_out.write_text(json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n", encoding="utf-8")
    summary["summary_out"] = str(summary_out)

    return (0 if passed else 1), summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run an opt-in OpenClaw memory embedding provider trial via temporary overlay config.")
    parser.add_argument("--provider", required=True, choices=SUPPORTED_PROVIDERS)
    parser.add_argument("--model", default=None, help="Optional provider-specific embedding model identifier.")
    parser.add_argument("--agent", default="main")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--timeout-sec", type=int, default=25)
    parser.add_argument("--index", action="store_true", help="Also run memory index before search.")
    parser.add_argument("--keep-overlay", action="store_true", help="Keep generated overlay config file.")
    parser.add_argument("--base-config", default=os.environ.get("OPENCLAW_CONFIG_PATH", str(Path.home() / ".openclaw" / "openclaw.json")))
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    base_config_path = Path(args.base_config).expanduser()
    if not base_config_path.exists():
        print(f"ERROR: base config not found: {base_config_path}")
        return 1

    ts = utc_ts_compact()
    default_out = Path(os.environ.get("OPENCLAW_STATE_DIR", str(Path.home() / ".openclaw"))) / "embedding-trials" / ts
    out_dir = Path(args.out_dir).expanduser() if args.out_dir else default_out

    rc, summary = run_trial(
        base_config_path=base_config_path,
        out_dir=out_dir,
        provider=args.provider,
        model=args.model,
        agent=args.agent,
        query=args.query,
        timeout_sec=max(5, int(args.timeout_sec)),
        run_index=bool(args.index),
        keep_overlay=bool(args.keep_overlay),
    )
    if args.json:
        print(json.dumps(summary, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(f"trial_pass={str(summary['pass']).lower()} provider={summary['provider']} hit_count={summary['hit_count']} summary={summary['summary_out']}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
