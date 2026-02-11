#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

KNOWN_TELEGRAM_REPLY_MODES = {"first", "all", "off"}
SLACK_SECRET_KEYS = {"botToken", "appToken", "userToken", "signingSecret", "token", "webhookSecret"}


def _must_list(value: Any, path: str) -> List[str]:
    if not isinstance(value, list):
        raise AssertionError(f"{path} must be a list")
    return [str(x) for x in value]


def _assert_telegram(cfg: Dict[str, Any]) -> Dict[str, Any]:
    channels = cfg.get("channels") or {}
    telegram = channels.get("telegram")
    if not isinstance(telegram, dict):
        raise AssertionError("channels.telegram must exist")
    if telegram.get("enabled") is not True:
        raise AssertionError("channels.telegram.enabled must be true")

    allow_from = _must_list(telegram.get("allowFrom"), "channels.telegram.allowFrom")
    if not allow_from:
        raise AssertionError("channels.telegram.allowFrom must be non-empty")
    if "*" in allow_from:
        raise AssertionError('channels.telegram.allowFrom must not include "*"')

    groups = telegram.get("groups")
    if not isinstance(groups, dict) or not groups:
        raise AssertionError("channels.telegram.groups must be a non-empty object allowlist")
    if "*" in groups:
        raise AssertionError('channels.telegram.groups must not contain "*" at P1.2')
    for group_id, group_cfg in sorted(groups.items()):
        if not isinstance(group_cfg, dict):
            raise AssertionError(f"channels.telegram.groups.{group_id} must be an object")
        if group_cfg.get("requireMention") is not True:
            raise AssertionError(f"channels.telegram.groups.{group_id}.requireMention must be true")

    reply_mode = str(telegram.get("replyToMode") or "")
    if reply_mode not in KNOWN_TELEGRAM_REPLY_MODES:
        raise AssertionError(f"channels.telegram.replyToMode must be one of {sorted(KNOWN_TELEGRAM_REPLY_MODES)}")
    if reply_mode != "first":
        raise AssertionError(f'channels.telegram.replyToMode must be "first" at P1.2, got {reply_mode}')

    agents = ((cfg.get("agents") or {}).get("list")) or []
    if not isinstance(agents, list) or not agents:
        raise AssertionError("agents.list must be configured")
    for agent in agents:
        if not isinstance(agent, dict):
            continue
        agent_id = str(agent.get("id") or "<unknown>")
        group_chat = agent.get("groupChat") or {}
        patterns = group_chat.get("mentionPatterns")
        if not isinstance(patterns, list) or not [p for p in patterns if str(p).strip()]:
            raise AssertionError(f"agents.list[{agent_id}].groupChat.mentionPatterns must be non-empty")

    commands = cfg.get("commands") or {}
    if commands.get("useAccessGroups") is not True:
        raise AssertionError("commands.useAccessGroups must be true")

    return {
        "allow_from_count": len(allow_from),
        "group_count": len(groups),
        "reply_to_mode": reply_mode,
        "posture": "allowlist+requireMention",
    }


def _assert_slack(cfg: Dict[str, Any]) -> Dict[str, Any]:
    channels = cfg.get("channels") or {}
    slack = channels.get("slack")
    if not isinstance(slack, dict):
        return {"enabled": False, "blocked": True}

    if slack.get("enabled") is not False:
        raise AssertionError("channels.slack.enabled must be false at P1.2")

    mode = str(slack.get("mode") or "")
    if mode and mode != "http":
        raise AssertionError('channels.slack.mode must be "http" when set')
    if mode == "http":
        webhook_path = str(slack.get("webhookPath") or "")
        if webhook_path != "/slack/events":
            raise AssertionError('channels.slack.webhookPath must be "/slack/events" when mode=http')

    for key in SLACK_SECRET_KEYS:
        if key in slack and str(slack.get(key) or "").strip():
            raise AssertionError(f"channels.slack.{key} must not be set at P1.2")

    return {"enabled": False, "blocked": True, "mode": mode or "unset"}


def assert_interfaces_policy(cfg: Dict[str, Any]) -> Dict[str, Any]:
    telegram = _assert_telegram(cfg)
    slack = _assert_slack(cfg)
    return {"telegram": telegram, "slack": slack}


def main() -> int:
    parser = argparse.ArgumentParser(description="Assert OpenClaw interfaces hardening policy invariants.")
    parser.add_argument("--config", default=str(Path.home() / ".openclaw" / "openclaw.json"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    result = assert_interfaces_policy(cfg)
    if args.json:
        print(json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=True))
    else:
        print("INTERFACES_POLICY_ASSERT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
