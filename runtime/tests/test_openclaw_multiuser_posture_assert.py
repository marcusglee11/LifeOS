import json

from runtime.tools.openclaw_multiuser_posture_assert import assert_multiuser_posture


def _cfg():
    return {
        "commands": {
            "ownerAllowFrom": ["owner-1"],
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
                "allowFrom": ["owner-1"],
                "replyToMode": "first",
                "groups": {
                    "group-a": {
                        "requireMention": True,
                        "allowFrom": ["owner-1"],
                    }
                },
            },
            "whatsapp": {
                "enabled": True,
                "allowFrom": ["owner-1"],
            },
            "slack": {
                "enabled": False,
            },
        },
    }


def test_multiuser_posture_passes_for_hardened_config():
    result = assert_multiuser_posture(_cfg())
    assert result["multiuser_posture_ok"] is True
    assert sorted(result["enabled_channels"]) == ["telegram", "whatsapp"]
    assert result["allowlist_sizes"]["commands.ownerAllowFrom"] == 1
    assert result["allowlist_sizes"]["channels.telegram.allowFrom"] == 1
    assert result["allowlist_sizes"]["channels.whatsapp.allowFrom"] == 1
    assert result["violations"] == []


def test_multiuser_posture_rejects_wildcard_allowlist():
    cfg = _cfg()
    cfg["channels"]["whatsapp"]["allowFrom"] = ["*"]
    result = assert_multiuser_posture(cfg)
    assert result["multiuser_posture_ok"] is False
    assert any("whatsapp.allowFrom" in v for v in result["violations"])


def test_multiuser_posture_rejects_missing_owner_boundary():
    cfg = _cfg()
    cfg["commands"]["ownerAllowFrom"] = []
    result = assert_multiuser_posture(cfg)
    assert result["multiuser_posture_ok"] is False
    assert any("ownerAllowFrom must be non-empty" in v for v in result["violations"])


def test_multiuser_posture_rejects_telegram_drift():
    cfg = _cfg()
    cfg["channels"]["telegram"]["replyToMode"] = "all"
    cfg["channels"]["telegram"]["groups"]["group-a"]["requireMention"] = False
    cfg["agents"]["list"][0]["groupChat"]["mentionPatterns"] = []
    result = assert_multiuser_posture(cfg)
    assert result["multiuser_posture_ok"] is False
    assert any("replyToMode" in v for v in result["violations"])
    assert any("requireMention" in v for v in result["violations"])
    assert any("mentionPatterns" in v for v in result["violations"])


def test_multiuser_posture_summary_exposes_counts_only():
    result = assert_multiuser_posture(_cfg())
    dumped = json.dumps(result, sort_keys=True)
    assert "owner-1" not in dumped

