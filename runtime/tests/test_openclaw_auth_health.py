from __future__ import annotations

import json
from pathlib import Path

from runtime.tools.openclaw_auth_health import (
    append_auth_health_record,
    classify_auth_health,
    inspect_codex_auth_order,
)
from runtime.tools.schemas import AuthHealthResult


def _write_codex_auth_files(tmp_path: Path) -> None:
    agent_dir = tmp_path / "agents" / "main" / "agent"
    agent_dir.mkdir(parents=True)
    (agent_dir / "auth-state.json").write_text(
        json.dumps(
            {
                "version": 1,
                "order": {"openai-codex": ["openai-codex:default", "openai-codex:codex-cli"]},
            }
        ),
        encoding="utf-8",
    )
    (agent_dir / "auth-profiles.json").write_text(
        json.dumps(
            {
                "version": 1,
                "profiles": {
                    "openai-codex:default": {
                        "type": "oauth",
                        "provider": "openai-codex",
                        "refresh": "r1",
                        "access": "a1",
                        "expires": 100,
                    },
                    "openai-codex:person@example.com": {
                        "type": "oauth",
                        "provider": "openai-codex",
                        "refresh": "r2",
                        "access": "a2",
                        "expires": 9999999999999,
                        "email": "person@example.com",
                    },
                },
            }
        ),
        encoding="utf-8",
    )


def test_classify_auth_health_ok_from_exit_zero() -> None:
    result = classify_auth_health(0, "models status check passed")
    assert isinstance(result, AuthHealthResult)
    assert result.state == "ok"
    assert result.reason_code == "ok"


def test_classify_auth_health_cooldown_pattern() -> None:
    output = "Provider openai-codex is in cooldown (all profiles unavailable)"
    result = classify_auth_health(1, output)
    assert result.state == "cooldown"
    assert result.reason_code == "provider_cooldown"
    assert result.provider == "openai-codex"


def test_classify_auth_health_invalid_pattern() -> None:
    output = "authentication required: token has been invalidated"
    result = classify_auth_health(1, output)
    assert result.state == "invalid_missing"
    assert result.reason_code == "expired_or_missing"


def test_classify_auth_health_refresh_token_reused_is_visible() -> None:
    output = "Token refresh failed: 401 code=refresh_token_reused"
    result = classify_auth_health(1, output)
    assert result.provider == "openai-codex"
    assert result.reason_code == "refresh_token_reused"
    assert "openclaw_codex_auth_repair.py --apply --json" in result.recommended_action


def test_classify_auth_health_stale_order_overrides_generic_ok() -> None:
    result = classify_auth_health(
        0,
        "models status check passed",
        codex_auth_order={
            "stale_order": True,
            "chosen_profile_id": "openai-codex:person@example.com",
        },
    )
    assert result.state == "expiring"
    assert result.reason_code == "codex_auth_order_stale"
    assert "person@example.com" in result.recommended_action


def test_inspect_codex_auth_order_detects_stale_profile_order(tmp_path: Path) -> None:
    _write_codex_auth_files(tmp_path)
    result = inspect_codex_auth_order(tmp_path, "main")
    assert result is not None
    assert result["stale_order"] is True
    assert result["chosen_profile_id"] == "openai-codex:person@example.com"


def test_append_auth_health_record_writes_jsonl(tmp_path: Path) -> None:
    out = tmp_path / "auth_health.jsonl"
    result = classify_auth_health(1, "Provider github-copilot is in cooldown")
    append_auth_health_record(out, result)

    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload["state"] == "cooldown"
    assert payload["provider"] == "github-copilot"
