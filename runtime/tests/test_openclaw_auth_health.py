from __future__ import annotations

import json
from pathlib import Path

from runtime.tools.openclaw_auth_health import (
    append_auth_health_record,
    classify_auth_health,
)
from runtime.tools.schemas import AuthHealthResult


def test_classify_auth_health_ok_from_exit_zero():
    result = classify_auth_health(0, "models status check passed")
    assert isinstance(result, AuthHealthResult)
    assert result.state == "ok"
    assert result.reason_code == "ok"


def test_classify_auth_health_cooldown_pattern():
    output = "Provider openai-codex is in cooldown (all profiles unavailable)"
    result = classify_auth_health(1, output)
    assert result.state == "cooldown"
    assert result.reason_code == "provider_cooldown"
    assert result.provider == "openai-codex"


def test_classify_auth_health_invalid_pattern():
    output = "authentication required: token has been invalidated"
    result = classify_auth_health(1, output)
    assert result.state == "invalid_missing"
    assert result.reason_code == "expired_or_missing"


def test_append_auth_health_record_writes_jsonl(tmp_path: Path):
    out = tmp_path / "auth_health.jsonl"
    result = classify_auth_health(1, "Provider github-copilot is in cooldown")
    append_auth_health_record(out, result)

    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["state"] == "cooldown"
    assert payload["provider"] == "github-copilot"
