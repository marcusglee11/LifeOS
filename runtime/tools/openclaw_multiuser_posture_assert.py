#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure repo root is importable when script is executed directly.
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from runtime.tools.openclaw_policy_assert import command_authorized

PRIV_COMMANDS = ["/model openai-codex/gpt-5.3-codex", "/models", "/think high"]


def _as_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()]


def _has_wildcard(values: List[str]) -> bool:
    return any(v == "*" for v in values)


def assert_multiuser_posture(cfg: Dict[str, Any]) -> Dict[str, Any]:
    violations: List[str] = []
    allowlist_sizes: Dict[str, int] = {}
    enabled_channels: List[str] = []

    session = cfg.get("session") or {}
    dm_scope = str(session.get("dmScope") or "").strip()
    if dm_scope != "per-account-channel-peer":
        violations.append('session.dmScope must be "per-account-channel-peer"')

    commands = cfg.get("commands") or {}
    owner_allow = _as_list(commands.get("ownerAllowFrom"))
    if commands.get("useAccessGroups") is not True:
        violations.append("commands.useAccessGroups must be true")
    if not owner_allow:
        violations.append("commands.ownerAllowFrom must be non-empty")
    if _has_wildcard(owner_allow):
        violations.append('commands.ownerAllowFrom must not contain "*"')
    allowlist_sizes["commands.ownerAllowFrom"] = len(owner_allow)

    channels = cfg.get("channels") or {}
    if not isinstance(channels, dict):
        violations.append("channels must be an object")
        channels = {}

    for ch_name in sorted(channels.keys()):
        ch_cfg = channels.get(ch_name)
        if not isinstance(ch_cfg, dict):
            continue
        if ch_cfg.get("enabled", True) is False:
            continue
        enabled_channels.append(ch_name)
        allow_from = _as_list(ch_cfg.get("allowFrom"))
        allowlist_sizes[f"channels.{ch_name}.allowFrom"] = len(allow_from)
        if not allow_from:
            violations.append(f"channels.{ch_name}.allowFrom must exist and be non-empty")
        if _has_wildcard(allow_from):
            violations.append(f'channels.{ch_name}.allowFrom must not contain "*"')

        if ch_name == "telegram":
            groups = ch_cfg.get("groups")
            if isinstance(groups, dict):
                if "*" in groups:
                    violations.append('channels.telegram.groups must not contain "*"')
                allowlist_sizes["channels.telegram.groups"] = len(groups)
                for group_id, group_cfg in sorted(groups.items()):
                    if not isinstance(group_cfg, dict):
                        violations.append(f"channels.telegram.groups.{group_id} must be object")
                        continue
                    if group_cfg.get("requireMention") is not True:
                        violations.append(f"channels.telegram.groups.{group_id}.requireMention must be true")
                    grp_allow = _as_list(group_cfg.get("allowFrom"))
                    if grp_allow and _has_wildcard(grp_allow):
                        violations.append(f'channels.telegram.groups.{group_id}.allowFrom must not contain "*"')

            reply_mode = str(ch_cfg.get("replyToMode") or "")
            if reply_mode != "first":
                violations.append('channels.telegram.replyToMode must be "first"')

    agents = ((cfg.get("agents") or {}).get("list")) or []
    if not isinstance(agents, list) or not agents:
        violations.append("agents.list must be configured")
    else:
        for agent in agents:
            if not isinstance(agent, dict):
                continue
            agent_id = str(agent.get("id") or "<unknown>")
            patterns = ((agent.get("groupChat") or {}).get("mentionPatterns")) or []
            if not isinstance(patterns, list) or not [p for p in patterns if str(p).strip()]:
                violations.append(f"agents.list[{agent_id}].groupChat.mentionPatterns must be non-empty")

    if owner_allow:
        owner = owner_allow[0]
        for cmd in PRIV_COMMANDS:
            if not command_authorized(cfg, owner, cmd):
                violations.append(f"owner must be authorized for {cmd.split()[0]}")
            if command_authorized(cfg, "__non_owner__", cmd):
                violations.append(f"non-owner must be rejected for {cmd.split()[0]}")

    summary = {
        "multiuser_posture_ok": len(violations) == 0,
        "enabled_channels": sorted(enabled_channels),
        "allowlist_sizes": {k: int(v) for k, v in sorted(allowlist_sizes.items())},
        "violations": violations,
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert OpenClaw multi-user posture invariants.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    result = assert_multiuser_posture(cfg)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print(
            "multiuser_posture_ok="
            + ("true" if result["multiuser_posture_ok"] else "false")
            + f" enabled_channels={','.join(result['enabled_channels'])}"
            + f" violations={len(result['violations'])}"
        )
    return 0 if result["multiuser_posture_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
