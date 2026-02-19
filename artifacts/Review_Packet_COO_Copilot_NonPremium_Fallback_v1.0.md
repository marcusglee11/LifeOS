---
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
mission_ref: "Change first subscription fallback to Copilot non-premium model and re-validate fail-closed startup gates"
version: "1.0"
status: "PENDING_REVIEW"
---

# Review_Packet_COO_Copilot_NonPremium_Fallback_v1.0

## Scope Envelope

- Allowed: `runtime/tools/openclaw_model_policy_assert.py`, `runtime/tools/openclaw_policy_assert.py`, runtime OpenClaw config at `/home/cabra/.openclaw/openclaw.json`
- Forbidden observed: none

## Summary

Updated the required fallback ladder in both policy assertions so the first fallback is `github-copilot/gpt-5-mini` (Copilot non-premium request path), followed by `google-gemini-cli/gemini-3-flash-preview`.

Applied live runtime config alignment in `/home/cabra/.openclaw/openclaw.json` for defaults and `main`/`quick`/`think` agents, verified `channels.slack.mode` remained unset, and re-ran gate validations plus `coo app`/`coo tui` startup checks.

## Acceptance Mapping

- First fallback rung switched to Copilot non-premium: PASS
- Policy assert scripts match runtime ladder: PASS
- Fail-closed gate status after startup checks: PASS (`gate_status.json pass=true`)
- `coo app` startup with deep security audit: PASS
- `coo tui` startup in host context: PASS

## Evidence

- `python3 runtime/tools/openclaw_model_policy_assert.py --json` => `policy_ok: true`
- `python3 runtime/tools/openclaw_policy_assert.py --json` => required fallbacks include `github-copilot/gpt-5-mini`
- `python3 runtime/tools/openclaw_interfaces_policy_assert.py --json` => Slack mode unset/blocked posture preserved
- `python3 runtime/tools/openclaw_cron_delivery_guard.py --json` => pass true
- `coo app` => `PASS security_audit_mode=deep ...` and dashboard open
- `coo tui` (host context) => `PASS models_preflight=true` and `PASS security_audit_mode=deep ...`
- `/home/cabra/.openclaw/runtime/gates/gate_status.json` => `pass: true`, `blocking_reasons: []`

## Changed Files

- `runtime/tools/openclaw_model_policy_assert.py`
- `runtime/tools/openclaw_policy_assert.py`

## Appendix A — Flattened Code

### File: `runtime/tools/openclaw_model_policy_assert.py`

````python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

REQUIRED_PREFIX = [
    "openai-codex/gpt-5.3-codex",
    "github-copilot/gpt-5-mini",
    "google-gemini-cli/gemini-3-flash-preview",
]
DISALLOWED_FALLBACK_RE = re.compile(r"(haiku|small)", re.IGNORECASE)
QUARANTINED_PROVIDER_RE = re.compile(r"^claude-max/", re.IGNORECASE)
MODEL_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*(?:/[a-z0-9][a-z0-9._-]*)+$", re.IGNORECASE)
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
    candidates: List[str] = []
    for mid in list(cfg_ids) + list(list_ids):
        low = str(mid).lower()
        if "kimi" in low and "/" in low:
            candidates.append(str(mid))
    if not candidates:
        return None
    return sorted(set(candidates))[0]


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
        ladder: List[str] = []
        if isinstance(primary, str) and primary.strip():
            ladder.append(primary)
        if isinstance(fallbacks, list):
            ladder.extend([str(x) for x in fallbacks if isinstance(x, str) and str(x).strip()])
        return ladder
    return []


def _provider_of(model_id: str) -> str:
    return model_id.split("/", 1)[0].strip().lower() if "/" in model_id else "unknown"


def assert_policy(cfg: Dict[str, Any], models_status: Dict[str, Dict[str, Any]], kimi_id: Optional[str]) -> Dict[str, Any]:
    del kimi_id  # Optional Kimi rung is no longer part of the burn-in baseline policy.

    violations: List[str] = []
    ladders: Dict[str, Any] = {}

    def validate(agent_id: str) -> None:
        actual = _agent_ladder(cfg, agent_id)
        if not actual:
            violations.append(f"{agent_id}: ladder missing or empty")
            ladders[agent_id] = {
                "actual": [],
                "required_prefix": REQUIRED_PREFIX,
                "working_models": [],
                "working_count": 0,
                "top_rung_auth_missing": True,
            }
            return

        if actual[0] != REQUIRED_PREFIX[0]:
            violations.append(f"{agent_id}: primary must be {REQUIRED_PREFIX[0]}, got {actual[0]}")

        if len(actual) < len(REQUIRED_PREFIX):
            violations.append(f"{agent_id}: ladder must include subscription-first prefix {REQUIRED_PREFIX}")
        else:
            prefix = actual[: len(REQUIRED_PREFIX)]
            if prefix != REQUIRED_PREFIX:
                violations.append(f"{agent_id}: ladder prefix mismatch with policy {REQUIRED_PREFIX}")

        for model_id in actual:
            if not MODEL_ID_RE.match(model_id):
                violations.append(f"{agent_id}: invalid model id format: {model_id}")

        for fb in actual[1:]:
            if DISALLOWED_FALLBACK_RE.search(fb):
                violations.append(f"{agent_id}: disallowed fallback model id: {fb}")
            if QUARANTINED_PROVIDER_RE.search(fb):
                violations.append(f"{agent_id}: quarantined provider fallback disallowed: {fb}")

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
            "required_prefix": REQUIRED_PREFIX,
            "working_models": working_models,
            "working_count": working_count,
            "top_rung_auth_missing": top_rung_auth_missing,
            "top_rung_working": top_working,
        }

    validate("main")
    validate("quick")
    validate("think")

    think_agent = None
    for item in ((cfg.get("agents") or {}).get("list") or []):
        if isinstance(item, dict) and str(item.get("id") or "") == "think":
            think_agent = item
            break
    if isinstance(think_agent, dict):
        think_level = think_agent.get("thinking") if "thinking" in think_agent else think_agent.get("thinkingDefault")
        if think_level is not None and str(think_level).lower() not in {"extra_high", "extra-high", "very_high"}:
            violations.append(f"think: thinking tier should be extra_high when configured, got {think_level}")

    all_model_ids: List[str] = []
    for aid in ("main", "quick", "think"):
        all_model_ids.extend([m for m in (ladders.get(aid) or {}).get("actual", []) if isinstance(m, str)])

    providers = sorted({_provider_of(m) for m in all_model_ids if "/" in m})
    auth_missing_providers = sorted(
        {
            _provider_of((ladders.get(aid) or {}).get("actual", [""])[0] or "")
            for aid in ("main", "quick", "think")
            if (ladders.get(aid) or {}).get("top_rung_auth_missing") is True
        }
    )

    return {
        "policy_ok": len(violations) == 0,
        "required_prefix": REQUIRED_PREFIX,
        "unresolved_optional_rungs": [],
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

    try:
        cfg_path = Path(args.config).expanduser()
        if not cfg_path.exists():
            error_result = {
                "policy_ok": False,
                "error": "config_not_found",
                "error_detail": f"Config file not found: {cfg_path}",
                "violations": ["config file missing"],
                "ladders": {},
                "required_prefix": REQUIRED_PREFIX,
                "unresolved_optional_rungs": [],
                "providers_referenced": [],
                "auth_missing_providers": [],
            }
            if args.json:
                print(json.dumps(error_result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
            else:
                print("policy_ok=false violations=1 error=config_not_found")
            return 1

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

        result = assert_policy(cfg, models_status, kimi_id)
        if args.json:
            print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        else:
            print(f"policy_ok={'true' if result['policy_ok'] else 'false'} violations={len(result['violations'])}")
        return 0 if result["policy_ok"] else 1
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError, IndexError, TypeError) as e:
        error_result = {
            "policy_ok": False,
            "error": type(e).__name__.lower(),
            "error_detail": str(e),
            "violations": [f"preflight error: {type(e).__name__}: {str(e)}"],
            "ladders": {},
            "required_prefix": REQUIRED_PREFIX,
            "unresolved_optional_rungs": [],
            "providers_referenced": [],
            "auth_missing_providers": [],
        }
        if args.json:
            print(json.dumps(error_result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        else:
            print(f"policy_ok=false violations=1 error={type(e).__name__.lower()}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
````

### File: `runtime/tools/openclaw_policy_assert.py`

````python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

PRIMARY_MODEL = "openai-codex/gpt-5.3-codex"
SUBSCRIPTION_FALLBACKS = [
    "github-copilot/gpt-5-mini",
    "google-gemini-cli/gemini-3-flash-preview",
]
OWNER_ONLY_COMMANDS = {"/model", "/models", "/think"}
MEMORY_PROVIDER = "local"
MEMORY_FALLBACK = "none"
DISALLOWED_FALLBACK_RE = re.compile(r"(haiku|small)", re.IGNORECASE)
QUARANTINED_PROVIDER_RE = re.compile(r"^claude-max/", re.IGNORECASE)


def _agent_by_id(cfg: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
    for item in ((cfg.get("agents") or {}).get("list") or []):
        if isinstance(item, dict) and item.get("id") == agent_id:
            return item
    return {}


def _owner_allow_from(cfg: Dict[str, Any]) -> List[str]:
    raw = (((cfg.get("commands") or {}).get("ownerAllowFrom")) or [])
    if not isinstance(raw, list):
        return []
    return sorted({str(x).strip() for x in raw if str(x).strip()})


def _model_cfg(entry: Dict[str, Any]) -> Dict[str, Any]:
    model = entry.get("model")
    return model if isinstance(model, dict) else {}


def _assert_ladder_prefix(entry: Dict[str, Any], label: str) -> None:
    model = _model_cfg(entry)
    got_primary = str(model.get("primary", ""))
    got_fallbacks = model.get("fallbacks")
    if not isinstance(got_fallbacks, list):
        got_fallbacks = []

    if got_primary != PRIMARY_MODEL:
        raise AssertionError(f"{label} primary mismatch: {got_primary} != {PRIMARY_MODEL}")
    if len(got_fallbacks) < len(SUBSCRIPTION_FALLBACKS):
        raise AssertionError(
            f"{label} fallbacks must begin with {SUBSCRIPTION_FALLBACKS}; got too few entries: {got_fallbacks}"
        )
    prefix = [str(x) for x in got_fallbacks[: len(SUBSCRIPTION_FALLBACKS)]]
    if prefix != SUBSCRIPTION_FALLBACKS:
        raise AssertionError(f"{label} fallback prefix mismatch: {prefix} != {SUBSCRIPTION_FALLBACKS}")

    for fb in got_fallbacks:
        model_id = str(fb)
        if DISALLOWED_FALLBACK_RE.search(model_id):
            raise AssertionError(f"{label} disallowed fallback model id: {model_id}")
        if QUARANTINED_PROVIDER_RE.search(model_id):
            raise AssertionError(f"{label} quarantined provider fallback disallowed: {model_id}")


def command_authorized(cfg: Dict[str, Any], sender: str, command: str) -> bool:
    cmd = command.strip().split(" ", 1)[0].lower()
    if cmd not in OWNER_ONLY_COMMANDS:
        return True
    owners = _owner_allow_from(cfg)
    if not owners:
        return False
    return sender in owners


def _assert_memory_policy(cfg: Dict[str, Any]) -> Dict[str, Any]:
    defaults = ((cfg.get("agents") or {}).get("defaults") or {})
    workspace_raw = str(defaults.get("workspace") or "")
    if not workspace_raw:
        raise AssertionError("agents.defaults.workspace must be set")

    workspace = os.path.abspath(os.path.expanduser(workspace_raw))
    openclaw_home = os.path.abspath(os.path.expanduser("~/.openclaw"))
    if not (workspace == openclaw_home or workspace.startswith(openclaw_home + os.sep)):
        raise AssertionError(f"agents.defaults.workspace must be under ~/.openclaw, got {workspace_raw}")

    memory = defaults.get("memorySearch")
    if not isinstance(memory, dict):
        raise AssertionError("agents.defaults.memorySearch must be configured")
    if memory.get("enabled") is not False:
        raise AssertionError("agents.defaults.memorySearch.enabled must be false during burn-in")

    provider = str(memory.get("provider") or "")
    fallback = str(memory.get("fallback") or "")
    if provider != MEMORY_PROVIDER:
        raise AssertionError(f"agents.defaults.memorySearch.provider must be {MEMORY_PROVIDER}, got {provider}")
    if fallback != MEMORY_FALLBACK:
        raise AssertionError(f"agents.defaults.memorySearch.fallback must be {MEMORY_FALLBACK}, got {fallback}")

    sources = memory.get("sources")
    if not isinstance(sources, list):
        raise AssertionError("agents.defaults.memorySearch.sources must be a list")
    normalized_sources = [str(x) for x in sources]
    if "memory" not in normalized_sources:
        raise AssertionError('agents.defaults.memorySearch.sources must include "memory"')
    if "sessions" in normalized_sources:
        raise AssertionError('agents.defaults.memorySearch.sources must not include "sessions" during burn-in')

    return {
        "enabled": False,
        "workspace": workspace_raw,
        "provider": provider,
        "fallback": fallback,
        "sources": normalized_sources,
    }


def assert_policy(cfg: Dict[str, Any]) -> Dict[str, Any]:
    defaults = ((cfg.get("agents") or {}).get("defaults") or {})
    defaults_think = str(defaults.get("thinkingDefault") or "unknown")
    if defaults_think not in {"low", "off"}:
        raise AssertionError(f"agents.defaults.thinkingDefault must be low/off, got {defaults_think}")

    _assert_ladder_prefix({"model": (defaults.get("model") or {})}, "agents.defaults")
    _assert_ladder_prefix(_agent_by_id(cfg, "main"), "main")
    _assert_ladder_prefix(_agent_by_id(cfg, "quick"), "quick")
    _assert_ladder_prefix(_agent_by_id(cfg, "think"), "think")

    owners = _owner_allow_from(cfg)
    if not owners:
        raise AssertionError("commands.ownerAllowFrom must be non-empty")
    owner = owners[0]
    if not command_authorized(cfg, owner, "/model openai-codex/gpt-5.3-codex"):
        raise AssertionError("owner must be authorized for /model")
    if command_authorized(cfg, "__non_owner__", "/model openai-codex/gpt-5.3-codex"):
        raise AssertionError("non-owner must be rejected for /model")
    if command_authorized(cfg, "__non_owner__", "/think high"):
        raise AssertionError("non-owner must be rejected for /think")

    memory = _assert_memory_policy(cfg)
    return {
        "primary_model": PRIMARY_MODEL,
        "required_subscription_fallbacks": SUBSCRIPTION_FALLBACKS,
        "owners": owners,
        "defaults_thinking": defaults_think,
        "memory": memory,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert OpenClaw subscription-first policy invariants.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    try:
        cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
        result = assert_policy(cfg)
    except (FileNotFoundError, json.JSONDecodeError, AssertionError, KeyError, ValueError, TypeError) as e:
        error_result = {
            "policy_ok": False,
            "error": type(e).__name__.lower(),
            "error_detail": str(e),
        }
        if args.json:
            print(json.dumps(error_result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
        else:
            print(f"POLICY_ASSERT_FAIL config={args.config} error={type(e).__name__}: {e}")
        return 1

    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(f"POLICY_ASSERT_PASS config={args.config}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
````
