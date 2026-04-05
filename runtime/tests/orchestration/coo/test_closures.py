"""Tests for file-based COO closure artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from runtime.orchestration.coo.closures import (
    ClosureValidationError,
    default_session_context_expiry,
    load_closures,
    load_session_context_packets,
    validate_council_request_packet,
    validate_session_context_packet,
    validate_sprint_close_packet,
    write_council_request_packet,
    write_sprint_close_packet,
)


def test_validate_sprint_close_packet_accepts_valid_payload() -> None:
    validate_sprint_close_packet(
        {
            "schema_version": "sprint_close_packet.v1",
            "order_id": "ORD-1",
            "task_ref": "T-027",
            "agent": "codex",
            "closed_at": "2026-04-05T12:00:00Z",
            "outcome": "success",
            "evidence_paths": [],
            "open_items": [],
            "suggested_next_task_ids": [],
            "state_mutations": [],
            "sync_check_result": "skipped",
        }
    )


def test_validate_sprint_close_packet_rejects_invalid_agent() -> None:
    with pytest.raises(ClosureValidationError, match="agent"):
        validate_sprint_close_packet(
            {
                "schema_version": "sprint_close_packet.v1",
                "order_id": "ORD-1",
                "task_ref": "T-027",
                "agent": "unknown",
                "closed_at": "2026-04-05T12:00:00Z",
                "outcome": "success",
                "evidence_paths": [],
                "open_items": [],
                "suggested_next_task_ids": [],
                "state_mutations": [],
                "sync_check_result": "skipped",
            }
        )


def test_validate_session_context_packet_rejects_expiry_before_written_at() -> None:
    with pytest.raises(ClosureValidationError, match="expires_at"):
        validate_session_context_packet(
            {
                "schema_version": "session_context_packet.v1",
                "author": "codex",
                "written_at": "2026-04-05T12:00:00Z",
                "subject": "Follow-up",
                "context": "Need review",
                "decisions_needed": [],
                "related_tasks": ["T-030"],
                "expires_at": "2026-04-05T11:00:00Z",
            }
        )


def test_validate_council_request_requires_resolved_at_when_resolved() -> None:
    with pytest.raises(ClosureValidationError, match="resolved_at"):
        validate_council_request_packet(
            {
                "schema_version": "council_request.v1",
                "request_id": "REQ-1",
                "requested_at": "2026-04-05T12:00:00Z",
                "trigger": "decision_support_needed",
                "question": "Proceed?",
                "context_summary": "Need approval",
                "suggested_respondents": ["Governance"],
                "options": [{"label": "Approve", "description": "Proceed"}],
                "requires_quorum": True,
                "related_tasks": ["T-030"],
                "resolved": True,
                "resolved_at": None,
            }
        )


def test_write_and_load_closures_round_trip(tmp_path: Path) -> None:
    sprint_path = write_sprint_close_packet(
        repo_root=tmp_path,
        order_id="ORD-1",
        task_ref="T-027",
        agent="codex",
        outcome="success",
        evidence_paths=["artifacts/receipts/index.json"],
        open_items=[],
        suggested_next_task_ids=["T-028"],
        state_mutations=[],
        sync_check_result="skipped",
        closed_at="2026-04-05T12:00:00Z",
    )
    council_path = write_council_request_packet(
        repo_root=tmp_path,
        request_id="REQ-1",
        trigger="decision_support_needed",
        question="Proceed?",
        context_summary="Need approval",
        suggested_respondents=["Governance"],
        options=[{"label": "Approve", "description": "Proceed"}],
        requires_quorum=True,
        related_tasks=["T-030"],
        requested_at="2026-04-05T12:00:00Z",
    )

    assert sprint_path.name == "SC-ORD-1.yaml"
    assert council_path.name == "CR-REQ-1.yaml"

    packets = load_closures(tmp_path)
    assert len(packets) == 2
    assert {packet["schema_version"] for packet in packets} == {
        "sprint_close_packet.v1",
        "council_request.v1",
    }


def test_load_closures_fails_closed_on_filename_schema_mismatch(tmp_path: Path) -> None:
    closures_dir = tmp_path / "artifacts" / "dispatch" / "closures"
    closures_dir.mkdir(parents=True)
    (closures_dir / "SC-bad.yaml").write_text(
        yaml.dump({"schema_version": "council_request.v1"}),
        encoding="utf-8",
    )
    with pytest.raises(ClosureValidationError, match="filename SC"):
        load_closures(tmp_path)


def test_load_session_context_packets_scans_only_scp_files(tmp_path: Path) -> None:
    for_ceo = tmp_path / "artifacts" / "for_ceo"
    for_ceo.mkdir(parents=True)
    (for_ceo / "IGNORED.md").write_text("not yaml", encoding="utf-8")
    (for_ceo / "SCP-20260405T120000Z-followup.yaml").write_text(
        yaml.dump(
            {
                "schema_version": "session_context_packet.v1",
                "author": "codex",
                "written_at": "2026-04-05T12:00:00Z",
                "subject": "Follow-up",
                "context": "Need review",
                "decisions_needed": [],
                "related_tasks": ["T-030"],
                "expires_at": "2026-04-08T12:00:00Z",
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    packets = load_session_context_packets(tmp_path)
    assert len(packets) == 1
    assert packets[0]["subject"] == "Follow-up"


def test_default_session_context_expiry_uses_z_suffix() -> None:
    assert default_session_context_expiry("2026-04-05T12:00:00Z") == "2026-04-08T12:00:00Z"
