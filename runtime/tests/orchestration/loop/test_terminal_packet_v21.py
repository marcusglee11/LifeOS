"""Tests for TerminalPacket v2.1 extensions."""

from __future__ import annotations

from dataclasses import asdict, fields

from runtime.orchestration.loop.spine import TerminalPacket


def test_terminal_packet_has_v21_fields():
    """TerminalPacket includes all v2.1 extension fields."""
    v21_fields = {
        "status",
        "start_ts",
        "end_ts",
        "task_ref",
        "policy_hash",
        "phase_outcomes",
        "gate_results",
        "receipt_index",
        "clean_fail_reason",
        "repo_clean_verified",
        "orphan_check_passed",
        "packet_hash",
    }
    actual_fields = {f.name for f in fields(TerminalPacket)}
    assert v21_fields.issubset(actual_fields), f"Missing: {v21_fields - actual_fields}"


def test_packet_hash_computed():
    """packet_hash field can hold a SHA-256 value."""
    from runtime.util.canonical import compute_sha256

    test_hash = compute_sha256({"test": "data"})

    packet = TerminalPacket(
        run_id="run_test",
        timestamp="2026-02-26T12:00:00+00:00",
        outcome="PASS",
        reason="pass",
        steps_executed=["hydrate", "policy", "design"],
        packet_hash=test_hash,
    )
    assert packet.packet_hash.startswith("sha256:")
    assert len(packet.packet_hash) > 70  # sha256: + 64 hex chars


def test_status_success_on_pass():
    """status="SUCCESS" when outcome is PASS."""
    packet = TerminalPacket(
        run_id="run_pass",
        timestamp="2026-02-26T12:00:00+00:00",
        outcome="PASS",
        reason="pass",
        steps_executed=["hydrate", "policy", "design", "build", "review", "steward"],
        status="SUCCESS",
    )
    assert packet.status == "SUCCESS"
    assert packet.outcome == "PASS"
    assert packet.clean_fail_reason is None


def test_status_clean_fail_on_blocked():
    """status="CLEAN_FAIL" when outcome is BLOCKED."""
    packet = TerminalPacket(
        run_id="run_blocked",
        timestamp="2026-02-26T12:00:00+00:00",
        outcome="BLOCKED",
        reason="mission_failed",
        steps_executed=["hydrate", "policy", "design"],
        status="CLEAN_FAIL",
        clean_fail_reason="mission_failed",
    )
    assert packet.status == "CLEAN_FAIL"
    assert packet.outcome == "BLOCKED"
    assert packet.clean_fail_reason == "mission_failed"


def test_phase_outcomes_populated():
    """phase_outcomes dict records per-phase status."""
    outcomes = {
        "hydrate": {"status": "pass"},
        "policy": {"status": "pass"},
        "design": {"status": "pass"},
        "build": {"status": "fail"},
    }
    packet = TerminalPacket(
        run_id="run_phases",
        timestamp="2026-02-26T12:00:00+00:00",
        outcome="BLOCKED",
        reason="mission_failed",
        steps_executed=["hydrate", "policy", "design", "build"],
        phase_outcomes=outcomes,
    )
    assert packet.phase_outcomes is not None
    assert packet.phase_outcomes["hydrate"]["status"] == "pass"
    assert packet.phase_outcomes["build"]["status"] == "fail"
    assert len(packet.phase_outcomes) == 4


def test_backward_compatible_defaults():
    """v2.1 fields have sensible defaults, existing code unaffected."""
    packet = TerminalPacket(
        run_id="run_compat",
        timestamp="2026-02-26T12:00:00+00:00",
        outcome="PASS",
        reason="pass",
        steps_executed=[],
    )
    assert packet.status == ""
    assert packet.start_ts is None
    assert packet.end_ts is None
    assert packet.task_ref is None
    assert packet.policy_hash is None
    assert packet.phase_outcomes is None
    assert packet.gate_results is None
    assert packet.receipt_index is None
    assert packet.clean_fail_reason is None
    assert packet.repo_clean_verified is False
    assert packet.orphan_check_passed is False
    assert packet.packet_hash is None
    assert packet.tokens_consumed is None
    assert packet.token_source is None
    assert packet.token_accounting_complete is True


def test_terminal_packet_has_token_accounting_fields():
    fields_present = {f.name for f in fields(TerminalPacket)}
    assert {"tokens_consumed", "token_source", "token_accounting_complete"}.issubset(
        fields_present
    )


def test_token_accounting_complete_defaults_true():
    packet = TerminalPacket(
        run_id="run_accounting_defaults",
        timestamp="2026-02-26T12:00:00+00:00",
        outcome="PASS",
        reason="pass",
        steps_executed=[],
    )
    assert packet.token_accounting_complete is True


def test_terminal_packet_serializes():
    """TerminalPacket with v2.1 fields serializes to dict cleanly."""
    packet = TerminalPacket(
        run_id="run_serial",
        timestamp="2026-02-26T12:00:00+00:00",
        outcome="PASS",
        reason="pass",
        steps_executed=["hydrate"],
        status="SUCCESS",
        start_ts="2026-02-26T11:59:00+00:00",
        end_ts="2026-02-26T12:00:00+00:00",
        phase_outcomes={"hydrate": {"status": "pass"}},
        repo_clean_verified=True,
        orphan_check_passed=True,
    )
    d = asdict(packet)
    assert d["status"] == "SUCCESS"
    assert d["phase_outcomes"]["hydrate"]["status"] == "pass"
    assert d["repo_clean_verified"] is True
