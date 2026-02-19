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
