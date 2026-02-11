from runtime.tools.openclaw_interfaces_policy_assert import assert_interfaces_policy


def _cfg():
    return {
        "commands": {
            "ownerAllowFrom": ["7054951144"],
            "useAccessGroups": True,
        },
        "agents": {
            "list": [
                {"id": "main", "groupChat": {"mentionPatterns": ["@openclaw", "openclaw"]}},
                {"id": "quick", "groupChat": {"mentionPatterns": ["@openclaw", "openclaw"]}},
            ]
        },
        "channels": {
            "telegram": {
                "enabled": True,
                "allowFrom": ["7054951144"],
                "replyToMode": "first",
                "groups": {
                    "-1000000000000": {
                        "requireMention": True,
                        "groupPolicy": "allowlist",
                        "allowFrom": ["7054951144"],
                    }
                },
            },
            "slack": {
                "enabled": False,
                "mode": "http",
                "webhookPath": "/slack/events",
                "groupPolicy": "disabled",
            },
        },
    }


def test_interfaces_policy_passes_with_hardened_telegram_and_disabled_slack():
    result = assert_interfaces_policy(_cfg())
    assert result["telegram"]["posture"] == "allowlist+requireMention"
    assert result["telegram"]["reply_to_mode"] == "first"
    assert result["slack"]["enabled"] is False
    assert result["slack"]["blocked"] is True


def test_interfaces_policy_rejects_telegram_wildcard_allowlist():
    cfg = _cfg()
    cfg["channels"]["telegram"]["allowFrom"] = ["*"]
    try:
        assert_interfaces_policy(cfg)
    except AssertionError as exc:
        assert "allowFrom must not include" in str(exc)
    else:
        raise AssertionError("expected wildcard allowlist assertion")


def test_interfaces_policy_rejects_missing_mention_patterns():
    cfg = _cfg()
    cfg["agents"]["list"][0]["groupChat"]["mentionPatterns"] = []
    try:
        assert_interfaces_policy(cfg)
    except AssertionError as exc:
        assert "mentionPatterns must be non-empty" in str(exc)
    else:
        raise AssertionError("expected mention patterns assertion")


def test_interfaces_policy_rejects_slack_secret_presence():
    cfg = _cfg()
    cfg["channels"]["slack"]["botToken"] = "xoxb-test"
    try:
        assert_interfaces_policy(cfg)
    except AssertionError as exc:
        assert "must not be set" in str(exc)
    else:
        raise AssertionError("expected slack secret assertion")
