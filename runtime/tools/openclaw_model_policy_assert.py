#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

EXECUTION_BASE = [
    "openai-codex/gpt-5.3-codex",
    "google-gemini-cli/gemini-3-flash-preview",
    "openrouter/pony-alpha",
]
THINKING_BASE = [
    "openai-codex/gpt-5.3-codex",
    "github-copilot/claude-opus-4.6",
    "openrouter/deepseek-v3.2",
]
DISALLOWED_FALLBACK_RE = re.compile(r"(haiku|small)", re.IGNORECASE)
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*$", re.IGNORECASE)
OPENCLAW_BIN = os.environ.get("OPENCLAW_BIN") or "openclaw"


def _safe_run(cmd: Sequence[str], timeout_s: int = 20) -> Tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s, check=False)
        return int(proc.returncode), proc.stdout
    except Exception:
        return 1, ""


def _collect_model_ids_from_config(cfg: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    defaults = (cfg.get("agents") or {}).get("defaults") or {}
    defaults_model = defaults.get("model") or {}
    if isinstance(defaults_model, dict):
        primary = defaults_model.get("primary")
        if isinstance(primary, str):
            out.append(primary)
        fb = defaults_model.get("fallbacks") or []
        if isinstance(fb, list):
            out.extend([str(x) for x in fb if isinstance(x, str)])

    defaults_models = defaults.get("models") or {}
    if isinstance(defaults_models, dict):
        out.extend([str(k) for k in defaults_models.keys()])

    for agent in ((cfg.get("agents") or {}).get("list") or []):
        if not isinstance(agent, dict):
            continue
        model = agent.get("model") or {}
        if not isinstance(model, dict):
            continue
        primary = model.get("primary")
        if isinstance(primary, str):
            out.append(primary)
        fb = model.get("fallbacks") or []
        if isinstance(fb, list):
            out.extend([str(x) for x in fb if isinstance(x, str)])

    return sorted({m for m in out if MODEL_ID_RE.match(m)})


def _parse_models_list_text(text: str) -> Dict[str, Dict[str, Any]]:
    status: Dict[str, Dict[str, Any]] = {}
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("Model ") or line.startswith("rc=") or line.startswith("BUILD_REPO="):
            continue
        cols = line.strip().split()
        if len(cols) < 5:
            continue
        model_id = cols[0].strip()
        if not MODEL_ID_RE.match(model_id):
            continue
        # Expected table order: Model Input Ctx Local Auth Tags
        # Use token positions from the end to tolerate variable spacing.
        auth = cols[-2].strip().lower() if len(cols) >= 6 else "unknown"
        tags = cols[-1].strip().lower()
        missing = "missing" in tags
        working = (auth == "yes") and (not missing)
        status[model_id] = {
            "auth": auth == "yes",
            "missing": missing,
            "working": working,
            "tags": tags,
        }
    return status


def _discover_kimi_id(cfg_ids: Sequence[str], list_ids: Sequence[str]) -> Optional[str]:
    candidates = []
    for mid in list(cfg_ids) + list(list_ids):
        low = mid.lower()
        if "kimi" in low and ("opencode/" in low or low.startswith("zen/opencode/")):
            candidates.append(mid)
    if not candidates:
        return None
    # Prefer explicit zen/opencode namespace when present.
    zen_first = [c for c in candidates if c.lower().startswith("zen/opencode/")]
    if zen_first:
        return sorted(set(zen_first))[0]
    return sorted(set(candidates))[0]


def _probe_kimi_via_provider_lists() -> List[str]:
    discovered: List[str] = []
    for provider in ("zen", "opencode"):
        rc, out = _safe_run([OPENCLAW_BIN, "models", "list", "--all", "--provider", provider], timeout_s=20)
        if rc != 0:
            continue
        for mid in _parse_models_list_text(out).keys():
            discovered.append(mid)
    return sorted(set(discovered))


def _agent_ladder(cfg: Dict[str, Any], agent_id: str) -> List[str]:
    for agent in ((cfg.get("agents") or {}).get("list") or []):
        if not isinstance(agent, dict):
            continue
        if str(agent.get("id") or "") != agent_id:
            continue
        model = agent.get("model") or {}
        if not isinstance(model, dict):
            return []
        primary = model.get("primary")
        fallbacks = model.get("fallbacks") or []
        ladder = []
        if isinstance(primary, str):
            ladder.append(primary)
        if isinstance(fallbacks, list):
            ladder.extend([str(x) for x in fallbacks if isinstance(x, str)])
        return ladder
    return []


def _ordered_subsequence(actual: Sequence[str], expected: Sequence[str]) -> bool:
    idx = 0
    for model in actual:
        try:
            pos = expected.index(model, idx)
        except ValueError:
            return False
        idx = pos + 1
    return True


def _provider_of(model_id: str) -> str:
    return model_id.split("/", 1)[0].strip().lower() if "/" in model_id else "unknown"


def assert_policy(cfg: Dict[str, Any], models_status: Dict[str, Dict[str, Any]], kimi_id: Optional[str]) -> Dict[str, Any]:
    execution_expected = list(EXECUTION_BASE)
    thinking_expected = list(THINKING_BASE)
    unresolved_optional_rungs: List[str] = []
    if kimi_id:
        execution_expected.append(kimi_id)
        thinking_expected.append(kimi_id)
    else:
        unresolved_optional_rungs.extend(
            [
                "execution:zen/opencode/<Kimi K2.5 Free identifier>",
                "thinking:zen/opencode/<Kimi K2.5 Free identifier>",
            ]
        )

    violations: List[str] = []
    ladders: Dict[str, Any] = {}

    def validate(agent_id: str, expected: List[str]) -> None:
        actual = _agent_ladder(cfg, agent_id)
        if not actual:
            violations.append(f"{agent_id}: ladder missing")
            ladders[agent_id] = {
                "actual": [],
                "expected": expected,
                "working_models": [],
                "working_count": 0,
                "top_rung_auth_missing": True,
            }
            return

        if actual[0] != expected[0]:
            violations.append(f"{agent_id}: primary must be {expected[0]}, got {actual[0]}")
        if not _ordered_subsequence(actual, expected):
            violations.append(f"{agent_id}: ladder order mismatch with policy")

        for fb in actual[1:]:
            if DISALLOWED_FALLBACK_RE.search(fb):
                violations.append(f"{agent_id}: disallowed fallback model id: {fb}")

        for model in actual:
            if model not in expected:
                violations.append(f"{agent_id}: model not in policy ladder: {model}")

        working_models = [m for m in actual if bool((models_status.get(m) or {}).get("working", False))]
        working_count = len(working_models)
        if working_count < 1:
            violations.append(f"{agent_id}: no working model detected in configured ladder")

        top = actual[0]
        top_auth = bool((models_status.get(top) or {}).get("auth", False))
        top_working = bool((models_status.get(top) or {}).get("working", False))
        top_rung_auth_missing = not top_auth

        ladders[agent_id] = {
            "actual": actual,
            "expected": expected,
            "working_models": working_models,
            "working_count": working_count,
            "top_rung_auth_missing": top_rung_auth_missing,
            "top_rung_working": top_working,
        }

    validate("main", execution_expected)
    validate("quick", execution_expected)
    validate("think", thinking_expected)

    # Enforce extra_high when represented explicitly.
    think_agent = None
    for item in ((cfg.get("agents") or {}).get("list") or []):
        if isinstance(item, dict) and str(item.get("id") or "") == "think":
            think_agent = item
            break
    if isinstance(think_agent, dict):
        think_level = think_agent.get("thinking") if "thinking" in think_agent else think_agent.get("thinkingDefault")
        if think_level is not None and str(think_level).lower() not in {"extra_high", "extra-high", "very_high"}:
            violations.append(f"think: thinking tier should be extra_high when configured, got {think_level}")

    providers = sorted(
        {
            _provider_of(m)
            for m in execution_expected + thinking_expected
            if isinstance(m, str) and "/" in m
        }
    )
    auth_missing_providers = sorted(
        {
            _provider_of((ladders.get(aid) or {}).get("actual", [None])[0] or "")
            for aid in ("main", "quick", "think")
            if (ladders.get(aid) or {}).get("top_rung_auth_missing") is True
        }
    )

    return {
        "policy_ok": len(violations) == 0,
        "execution_ladder_expected": execution_expected,
        "thinking_ladder_expected": thinking_expected,
        "unresolved_optional_rungs": unresolved_optional_rungs,
        "providers_referenced": providers,
        "auth_missing_providers": [p for p in auth_missing_providers if p and p != "unknown"],
        "ladders": ladders,
        "violations": violations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert OpenClaw model policy for COO UX preflight.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--models-list-file", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cfg_path = Path(args.config).expanduser()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))

    list_text = ""
    if args.models_list_file:
        list_text = Path(args.models_list_file).read_text(encoding="utf-8", errors="replace")
    else:
        rc, out = _safe_run([OPENCLAW_BIN, "models", "list"], timeout_s=25)
        list_text = out if rc == 0 else ""

    models_status = _parse_models_list_text(list_text)
    cfg_ids = _collect_model_ids_from_config(cfg)
    list_ids = list(models_status.keys())
    kimi_id = _discover_kimi_id(cfg_ids, list_ids)
    if not kimi_id:
        kimi_id = _discover_kimi_id(cfg_ids, _probe_kimi_via_provider_lists())

    result = assert_policy(cfg, models_status, kimi_id)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(f"policy_ok={'true' if result['policy_ok'] else 'false'} violations={len(result['violations'])}")
    return 0 if result["policy_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
