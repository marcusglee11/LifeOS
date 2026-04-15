from __future__ import annotations

import json
from pathlib import Path

from runtime.tools.openclaw_codex_auth_repair import (
    analyze_codex_auth_setup,
    apply_repair,
    build_proposed_order,
    planned_apply_commands,
    rank_profiles,
    write_rollback_receipt,
)


def _auth_profiles_payload() -> dict[str, object]:
    return {
        "version": 1,
        "profiles": {
            "openai-codex:default": {
                "type": "oauth",
                "provider": "openai-codex",
                "refresh": "r1",
                "access": "a1",
                "expires": 100,
                "managedBy": "codex-cli",
                "accountId": "acct-default",
            },
            "openai-codex:codex-cli": {
                "type": "oauth",
                "provider": "openai-codex",
                "refresh": "r2",
                "access": "a2",
                "expires": 200,
                "accountId": "acct-codex-cli",
            },
            "openai-codex:person@example.com": {
                "type": "oauth",
                "provider": "openai-codex",
                "refresh": "r3",
                "access": "a3",
                "expires": 300,
                "email": "person@example.com",
            },
            "anthropic:default": {
                "type": "oauth",
                "provider": "anthropic",
                "refresh": "ignore",
                "expires": 9999,
            },
        },
    }


def _auth_state_payload() -> dict[str, object]:
    return {
        "version": 1,
        "order": {"openai-codex": ["openai-codex:default", "openai-codex:codex-cli"]},
        "lastGood": {"openai-codex": "openai-codex:default"},
    }


def test_rank_profiles_prefers_latest_expiry_then_email_scoped() -> None:
    analysis = analyze_codex_auth_setup(
        _auth_state_payload(),
        _auth_profiles_payload(),
        now_ms=50,
        codex_auth_path=Path("/missing/auth.json"),
    )

    ranked = rank_profiles(analysis.profiles)
    assert [profile.profile_id for profile in ranked] == [
        "openai-codex:person@example.com",
        "openai-codex:codex-cli",
        "openai-codex:default",
    ]


def test_build_proposed_order_promotes_valid_profile_and_keeps_existing_entries() -> None:
    analysis = analyze_codex_auth_setup(
        _auth_state_payload(),
        _auth_profiles_payload(),
        now_ms=250,
        codex_auth_path=Path("/missing/auth.json"),
    )

    assert analysis.chosen_profile_id == "openai-codex:person@example.com"
    assert analysis.stale_order is True
    assert analysis.proposed_order == [
        "openai-codex:person@example.com",
        "openai-codex:default",
        "openai-codex:codex-cli",
    ]


def test_build_proposed_order_handles_no_valid_profile() -> None:
    analysis = analyze_codex_auth_setup(
        _auth_state_payload(),
        _auth_profiles_payload(),
        now_ms=500,
        codex_auth_path=Path("/missing/auth.json"),
    )

    assert analysis.chosen_profile_id is None
    assert analysis.stale_order is False
    assert analysis.proposed_order == [
        "openai-codex:default",
        "openai-codex:codex-cli",
        "openai-codex:person@example.com",
    ]


def test_planned_apply_commands_match_openclaw_cli_contract() -> None:
    commands = planned_apply_commands(
        openclaw_bin="openclaw",
        provider="openai-codex",
        proposed_order=["openai-codex:person@example.com", "openai-codex:default"],
    )

    assert commands == [
        [
            "openclaw",
            "models",
            "auth",
            "order",
            "set",
            "--provider",
            "openai-codex",
            "openai-codex:person@example.com",
            "openai-codex:default",
        ],
        ["openclaw", "secrets", "reload", "--json"],
    ]


def test_write_rollback_receipt_captures_previous_and_proposed_order(tmp_path: Path) -> None:
    analysis = analyze_codex_auth_setup(
        _auth_state_payload(),
        _auth_profiles_payload(),
        now_ms=250,
        codex_auth_path=Path("/missing/auth.json"),
    )

    receipt_path = write_rollback_receipt(
        tmp_path,
        analysis,
        command_results=[{"cmd": ["openclaw", "secrets", "reload", "--json"], "exit_code": 0}],
        applied=False,
    )

    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert payload["applied"] is False
    assert payload["current_order"] == ["openai-codex:default", "openai-codex:codex-cli"]
    assert payload["proposed_order"][0] == "openai-codex:person@example.com"


def test_apply_repair_uses_runner_and_returns_receipt_path(tmp_path: Path) -> None:
    analysis = analyze_codex_auth_setup(
        _auth_state_payload(),
        _auth_profiles_payload(),
        now_ms=250,
        codex_auth_path=Path("/missing/auth.json"),
    )
    calls: list[list[str]] = []

    def runner(cmd: list[str]) -> dict[str, object]:
        calls.append(cmd)
        return {"cmd": cmd, "exit_code": 0, "stdout": "", "stderr": ""}

    result = apply_repair(
        analysis,
        provider="openai-codex",
        openclaw_bin="openclaw",
        receipt_root=tmp_path,
        runner=runner,
    )

    assert result["ok"] is True
    assert len(calls) == 2
    assert Path(str(result["receipt_path"])).exists()


def test_build_proposed_order_deduplicates_existing_rows() -> None:
    order = build_proposed_order(
        ["openai-codex:default", "openai-codex:default"],
        [],
        ["openai-codex:default", "openai-codex:person@example.com"],
    )
    assert order == ["openai-codex:default", "openai-codex:person@example.com"]
