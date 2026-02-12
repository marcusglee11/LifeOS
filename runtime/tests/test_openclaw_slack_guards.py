from runtime.tools.openclaw_slack_overlay import slack_base_posture


def test_base_posture_slack_disabled_without_secrets():
    cfg = {"channels": {"slack": {"enabled": False, "mode": "socket"}}}
    result = slack_base_posture(cfg)
    assert result["slack_base_disabled"] is True
    assert result["slack_base_enabled"] is False
    assert result["slack_secrets_in_base"] is False
    assert result["slack_secret_key_count"] == 0


def test_base_posture_detects_secret_keys_in_base():
    cfg = {"channels": {"slack": {"enabled": False, "botToken": "xoxb-unsafe"}}}
    result = slack_base_posture(cfg)
    assert result["slack_base_disabled"] is True
    assert result["slack_secrets_in_base"] is True
    assert result["slack_secret_key_count"] == 1


def test_base_posture_detects_enabled_slack():
    cfg = {"channels": {"slack": {"enabled": True}}}
    result = slack_base_posture(cfg)
    assert result["slack_base_enabled"] is True
    assert result["slack_base_disabled"] is False

