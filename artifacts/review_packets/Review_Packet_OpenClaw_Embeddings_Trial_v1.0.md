# Review Packet — OpenClaw Embeddings Trial v1.0

- Mission: Add opt-in external embedding A/B trial path without changing enforced local-first default policy.
- Branch: build/ux-coo-single-command
- Head (pre-commit): 2d51c4d feat(coo): single-command OpenClaw UX (start/tui/app/stop) + embedded model policy preflight
- Evidence Dir: artifacts/evidence/openclaw/embedding_trial/20260212T134524Z

## What Changed
- Added runtime/tools/openclaw_embedding_trial.py (temporary overlay-based embedding provider trial).
- Added runtime/tests/test_openclaw_embedding_trial.py (safe-default and provider-setting unit tests).
- Updated runtime/tools/OPENCLAW_COO_RUNBOOK.md with copy/paste trial commands and interpretation.

## Outcome
- Default policy remains unchanged and enforced (provider=local, fallback=none).
- External providers are now testable in isolated, opt-in trial mode only.

## Evidence Files
- artifacts/evidence/openclaw/embedding_trial/20260212T134524Z/git_status_after.txt
- artifacts/evidence/openclaw/embedding_trial/20260212T134524Z/git_diff_name_only.txt
- artifacts/evidence/openclaw/embedding_trial/20260212T134524Z/pytest.txt
- artifacts/evidence/openclaw/embedding_trial/20260212T134524Z/local_trial.json
- artifacts/evidence/openclaw/embedding_trial/20260212T134524Z/recommendation_note.md

## Appendix A — Flattened Code

### runtime/tools/openclaw_embedding_trial.py
```text
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

```

### runtime/tests/test_openclaw_embedding_trial.py
```text
from runtime.tools.openclaw_embedding_trial import build_trial_config


def _base_cfg() -> dict:
    return {
        "agents": {
            "defaults": {
                "workspace": "/home/tester/.openclaw/workspace",
                "memorySearch": {
                    "enabled": True,
                    "provider": "local",
                    "fallback": "auto",
                    "sources": ["memory", "sessions"],
                },
            }
        }
    }


def test_trial_config_enforces_safe_defaults_for_remote_provider():
    cfg = build_trial_config(_base_cfg(), provider="openai", model="text-embedding-3-small")
    memory = cfg["agents"]["defaults"]["memorySearch"]
    assert memory["enabled"] is True
    assert memory["provider"] == "openai"
    assert memory["fallback"] == "none"
    assert memory["sources"] == ["memory"]
    assert memory["openai"]["model"] == "text-embedding-3-small"
    assert memory["query"]["hybrid"]["enabled"] is True
    assert memory["cache"]["enabled"] is True
    assert memory["sync"]["watch"] is True


def test_trial_config_sets_local_model_path_when_requested():
    cfg = build_trial_config(_base_cfg(), provider="local", model="hf:BAAI/bge-small-en-v1.5")
    memory = cfg["agents"]["defaults"]["memorySearch"]
    assert memory["provider"] == "local"
    assert memory["local"]["modelPath"] == "hf:BAAI/bge-small-en-v1.5"


def test_trial_config_keeps_provider_default_when_model_not_set():
    cfg = build_trial_config(_base_cfg(), provider="gemini", model=None)
    memory = cfg["agents"]["defaults"]["memorySearch"]
    assert memory["provider"] == "gemini"
    assert "gemini" not in memory or "model" not in memory.get("gemini", {})

```

### runtime/tools/OPENCLAW_COO_RUNBOOK.md
```text
# OpenClaw COO Runbook

## Canonical Commands

- OpenClaw operations: `coo openclaw -- <args>`
- Shell/process operations: `coo run -- <command>`

## Receipts (Runtime Default)

Canonical operator path is runtime-only receipts (no repo writes by default):

- `$OPENCLAW_STATE_DIR/receipts/<UTC_TS>/Receipt_Bundle_OpenClaw.md`
- `$OPENCLAW_STATE_DIR/receipts/<UTC_TS>/receipt_manifest.json`
- `$OPENCLAW_STATE_DIR/receipts/<UTC_TS>/openclaw_run_ledger_entry.jsonl`
- `$OPENCLAW_STATE_DIR/ledger/openclaw_run_ledger.jsonl`

If `$OPENCLAW_STATE_DIR` is not writable, scripts fall back to `/tmp/openclaw-runtime/...`.

Run default mode:

```bash
runtime/tools/openclaw_receipts_bundle.sh
```

Optional explicit repo export (copy-only):

```bash
runtime/tools/openclaw_receipts_bundle.sh --export-repo
```

Export path:

- `artifacts/evidence/openclaw/receipts/Receipt_Bundle_OpenClaw_<UTC_TS>.md`

Export is optional and should only be used when a repo-local evidence copy is required.

## Verify Surface

Run full verify flow (security/model/sandbox/gateway checks + receipt generation + ledger append + leak scan):

```bash
runtime/tools/openclaw_verify_surface.sh
```

Expected output:

- `PASS security_audit_mode=<mode> confinement_detected=<true|false> ... runtime_receipt=<path> ledger_path=<path>`
- or `FAIL security_audit_mode=<mode> confinement_detected=<true|false> ... runtime_receipt=<path> ledger_path=<path>`

Security audit strategy:

- `security audit --deep` is attempted first.
- If deep fails with known host confinement signature
  `uv_interface_addresses returned Unknown system error 1`,
  verify runs bounded fallback `security audit` (non-deep).
- Any other deep failure remains fail-closed and verify returns non-zero.
- When fallback triggers, verify and ledger include:
  `confinement_detected=true` and
  `confinement_flag=uv_interface_addresses_unknown_system_error_1`.

Model policy assertion:

```bash
python3 runtime/tools/openclaw_policy_assert.py --json
```

Optional memory verifier (not part of P0 security PASS path):

```bash
runtime/tools/openclaw_verify_memory.sh
```

Expected output:

- `PASS memory_policy_ok=true provider=local fallback=none ...`
- or `FAIL memory_policy_ok=false provider=<x> fallback=<y> ...`

Safe memory indexing wrapper (guarded):

```bash
runtime/tools/openclaw_memory_index_safe.sh
```

Behavior:

- Runs `runtime/tools/openclaw_memory_policy_guard.py` first (fail-closed).
- Runs `coo openclaw -- memory index --agent main --verbose` only when guard passes.

## Embedding Provider Trial (Opt-In, No Default Drift)

Default policy stays enforced as local-only memory embeddings:

- `memorySearch.provider=local`
- `memorySearch.fallback=none`

Use this trial command only for A/B checks. It runs with a temporary overlay config under `$OPENCLAW_STATE_DIR/embedding-trials/` and does not mutate your base config:

```bash
python3 runtime/tools/openclaw_embedding_trial.py --provider openai --model text-embedding-3-small --index --json
```

Other provider trials:

```bash
python3 runtime/tools/openclaw_embedding_trial.py --provider gemini --model gemini-embedding-001 --index --json
python3 runtime/tools/openclaw_embedding_trial.py --provider voyage --model voyage-3.5-lite --index --json
```

Interpretation:

- `trial_pass=true` with `hit_count>=1` means the provider worked for current corpus/search.
- `trial_pass=false` means auth/model/provider failed in trial mode; baseline local policy remains unchanged.

Optional interfaces verifier (Telegram hardening posture):

```bash
runtime/tools/openclaw_verify_interfaces.sh
```

Expected output:

- `PASS telegram_posture=allowlist+requireMention replyToMode=first ...`
- or `FAIL telegram_posture=allowlist+requireMention replyToMode=<x> ...`

Grounded recall verifier (memory ↔ interface contract):

```bash
runtime/tools/openclaw_verify_recall_e2e.sh
```

Expected output:

- `PASS recall_mode=telegram_sim|cli_only sources_present=true MANUAL_SMOKE_REQUIRED=<true|false> ...`
- or `FAIL recall_mode=... sources_present=false ...`

Recall contract:

- Recall/decision intents must use memory search first.
- Answers must include a `Sources:` section with `file:line-range` pointers.
- If no hits, response must be: `No grounded memory found. Which timeframe or document should I check?`
- Receipts/ledger store recall metadata only (`query_hash`, hit count, sources), never raw query content.

## Manual Telegram Smoke (Metadata-Only)

Operator step (allowed Telegram DM only):

1. Send exactly:
   `what did we decide last week about lobster-memory-seed-001?`
2. Expected behavior:
   - grounded answer returned
   - `Sources:` section includes `memory/daily/2026-02-10.md:1-5`
3. Record metadata only (no message text, no IDs/usernames/phone numbers):

```bash
coo run -- bash -lc 'cd /mnt/c/Users/cabra/Projects/LifeOS && P1_5_EVDIR=artifacts/evidence/openclaw/p1_5/<UTC_TS> runtime/tools/openclaw_record_manual_smoke.sh --surface telegram_dm --result pass --sources memory/daily/2026-02-10.md:1-5'
```

Fail branch:

```bash
coo run -- bash -lc 'cd /mnt/c/Users/cabra/Projects/LifeOS && P1_5_EVDIR=artifacts/evidence/openclaw/p1_5/<UTC_TS> runtime/tools/openclaw_record_manual_smoke.sh --surface telegram_dm --result fail --sources "(none)"'
```

## P1 Acceptance Verifier

Run:

```bash
coo run -- bash -lc 'cd /mnt/c/Users/cabra/Projects/LifeOS && P1_5_EVDIR=artifacts/evidence/openclaw/p1_5/<UTC_TS> runtime/tools/openclaw_verify_p1_acceptance.sh'
```

Expected:

- `PASS p1_acceptance=true manual_smoke=pass source_pointer=memory/daily/2026-02-10.md:1-5 ...`

## Multi-User Posture Verifier

Run:

```bash
runtime/tools/openclaw_verify_multiuser_posture.sh
```

Expected:

- `PASS multiuser_posture_ok=true enabled_channels_count=<n> allowlist_counts=<k=v,...> ...`
- or `FAIL ...` when any allowlist/owner boundary/Telegram posture invariant drifts.

## Operator Onboarding (Controlled + Auditable)

Generate an onboarding checklist with a non-sensitive internal reference label:

```bash
runtime/tools/openclaw_onboard_operator.sh --candidate-ref operator-two-change-request
```

Notes:

- The helper stores only `candidate_ref_sha256` and never raw identifiers.
- Apply config changes manually via reviewed PR/commit; then run:
  - `python3 runtime/tools/openclaw_multiuser_posture_assert.py --json`
  - `runtime/tools/openclaw_verify_multiuser_posture.sh`

## Telegram Hardening

- `channels.telegram.allowFrom` must be non-empty and must not include `"*"`.
- `channels.telegram.groups` must use explicit group IDs (no `"*"`), with `requireMention: true`.
- `agents.list[].groupChat.mentionPatterns` should include stable mention triggers (for example `@openclaw`, `openclaw`).
- `messages.groupChat.historyLimit` should stay conservative (30-50).
- `channels.telegram.replyToMode` uses `first` for predictable threading.

## Slack Scaffold (Blocked Until Tokens)

Slack is scaffolded in secure-by-default mode only:

- `channels.slack.enabled=false`
- optional HTTP wiring keys only (`mode="http"`, `webhookPath="/slack/events"`)
- no `botToken`, `appToken`, or `signingSecret` in config

Slack enablement uses env-only overlay generation. Tokens are never written into
`~/.openclaw/openclaw.json`, repo files, or evidence artifacts.

Socket mode enablement (when provisioning is approved):

1. Export env vars in shell/session only:
   - `OPENCLAW_SLACK_MODE=socket`
   - `OPENCLAW_SLACK_APP_TOKEN`
   - `OPENCLAW_SLACK_BOT_TOKEN`
2. Launch with overlay:
   - `runtime/tools/openclaw_slack_launch.sh --apply`
3. Run post-enable checks:
   - `runtime/tools/openclaw_verify_interfaces.sh`
   - `runtime/tools/openclaw_verify_multiuser_posture.sh`
   - `runtime/tools/openclaw_verify_slack_guards.sh`

HTTP mode enablement (when provisioning is approved):

1. Export env vars in shell/session only:
   - `OPENCLAW_SLACK_MODE=http`
   - `OPENCLAW_SLACK_BOT_TOKEN`
   - `OPENCLAW_SLACK_SIGNING_SECRET`
2. Ensure request URL uses `/slack/events` and signature verification remains enabled.
3. Launch with overlay:
   - `runtime/tools/openclaw_slack_launch.sh --apply`
4. Run same post-enable checks as socket mode.

## Safety Invariants

- Default receipt generation must not write to repo paths.
- Ledger and receipts must remain redacted-safe.
- Leak scan must pass for runtime receipt + runtime ledger entry.
- Verify is fail-closed on security audit, sandbox invariants, and policy assertion.
- Receipts include a non-deep memory status capture; they do not run memory index by default.
- Receipts include memory policy guard summary status (`memory_policy_ok`, violation count).
- Receipts include recall trace metadata (`recall_trace_enabled`, `last_recall`).
- Receipts include a non-deep channels status capture and never include Slack secrets.
- Receipts include multi-user posture status (`multiuser_posture_ok`, channel names, allowlist counts, violations count) and never include allowlist values.
- Receipts include Slack guard posture (`slack_ready_to_enable`, `slack_base_enabled`, `slack_env_present`, `slack_overlay_last_mode`) with booleans/counts only.

```

