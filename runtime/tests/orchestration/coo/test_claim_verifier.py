"""Tests for COO claim verifier module."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.orchestration.coo.backlog import TaskEntry
from runtime.orchestration.coo.claim_verifier import (
    ClaimViolation,
    EvidenceSnapshot,
    collect_evidence,
    verify_claims,
    verify_progress_obligation,
)


def _make_empty_snapshot() -> EvidenceSnapshot:
    return EvidenceSnapshot(
        tasks=[],
        inbox_orders=[],
        active_orders=[],
        completed_orders={},
        manifest_entries=[],
        escalation_ids=[],
    )


def _make_task(task_id: str, status: str = "pending") -> TaskEntry:
    return TaskEntry(
        id=task_id,
        title=f"Task {task_id}",
        description="",
        dod="",
        priority="P1",
        risk="low",
        scope_paths=[],
        status=status,
        requires_approval=False,
        owner="",
        evidence="",
        task_type="build",
        tags=[],
        objective_ref="bootstrap",
        created_at="2026-03-05T00:00:00Z",
        completed_at=None,
    )


class TestVerifyClaimsStartedPatterns:
    def test_reject_started_no_active_order(self) -> None:
        """'started T-009' with no active order -> violation."""
        snapshot = _make_empty_snapshot()
        output = "I have started T-009 as requested."
        violations = verify_claims(output, snapshot)
        assert len(violations) >= 1
        types = {v.claim_type for v in violations}
        assert "execution_state" in types

    def test_allow_started_with_active_order(self) -> None:
        """'started T-009' with matching active order -> no violation."""
        snapshot = EvidenceSnapshot(
            tasks=[_make_task("T-009", "in_progress")],
            inbox_orders=[],
            active_orders=["ORD-T-009-20260310000000"],
            completed_orders={},
            manifest_entries=[],
            escalation_ids=[],
        )
        output = "I have started T-009 as requested."
        violations = verify_claims(output, snapshot)
        # Should be empty (no violation for T-009 started)
        execution_violations = [v for v in violations if "T-009" in v.required_evidence]
        assert execution_violations == []


class TestVerifyClaimsCompletedPatterns:
    def test_reject_completed_no_success_order(self) -> None:
        """'completed T-009' with no SUCCESS order -> violation."""
        snapshot = _make_empty_snapshot()
        output = "T-009 has been completed successfully."
        violations = verify_claims(output, snapshot)
        assert len(violations) >= 1

    def test_allow_completed_with_success_order(self) -> None:
        """'completed T-009' with SUCCESS completed order -> no violation."""
        snapshot = EvidenceSnapshot(
            tasks=[_make_task("T-009", "completed")],
            inbox_orders=[],
            active_orders=[],
            completed_orders={"ORD-T-009-20260310000000": "SUCCESS"},
            manifest_entries=[],
            escalation_ids=[],
        )
        output = "T-009 completed successfully."
        violations = verify_claims(output, snapshot)
        execution_violations = [
            v for v in violations
            if "T-009" in (v.required_evidence or "") and v.claim_type == "execution_state"
        ]
        assert execution_violations == []

    def test_reject_completed_with_clean_fail_order(self) -> None:
        """'T-009 completed' with only CLEAN_FAIL order -> violation."""
        snapshot = EvidenceSnapshot(
            tasks=[_make_task("T-009", "blocked")],
            inbox_orders=[],
            active_orders=[],
            completed_orders={"ORD-T-009-20260310000000": "CLEAN_FAIL"},
            manifest_entries=[],
            escalation_ids=[],
        )
        output = "T-009 has been completed."
        violations = verify_claims(output, snapshot)
        # CLEAN_FAIL != SUCCESS so should still flag
        assert len(violations) >= 1


class TestVerifyClaimsCommitSHA:
    def test_reject_commit_sha_not_in_git(self, tmp_path: Path) -> None:
        """Random 40-char hex in output with repo_root set -> violation."""
        snapshot = _make_empty_snapshot()
        sha = "a" * 40
        output = f"The commit {sha} was created."
        with patch(
            "runtime.orchestration.coo.claim_verifier._sha_exists_in_git",
            return_value=False,
        ):
            violations = verify_claims(output, snapshot, repo_root=tmp_path)
        commit_violations = [v for v in violations if v.claim_type == "commit"]
        assert len(commit_violations) >= 1

    def test_sha_without_repo_root_is_unverifiable(self) -> None:
        """40-char hex with no repo_root -> marked unverifiable, not rejected."""
        snapshot = _make_empty_snapshot()
        sha = "b" * 40
        output = f"The commit {sha} was created."
        violations = verify_claims(output, snapshot, repo_root=None)
        commit_violations = [v for v in violations if v.claim_type == "commit"]
        assert len(commit_violations) >= 1
        assert all(v.found_evidence == "unverifiable" for v in commit_violations)


class TestVerifyClaimsNoViolations:
    def test_no_claims_no_violations(self) -> None:
        """Proposal with only rationale text -> empty list."""
        snapshot = _make_empty_snapshot()
        output = (
            "schema_version: task_proposal.v1\n"
            "proposals:\n"
            "  - task_id: T-001\n"
            "    rationale: Highest priority, all deps met.\n"
            "    proposed_action: dispatch\n"
            "    urgency_override: null\n"
            "    suggested_owner: codex\n"
        )
        violations = verify_claims(output, snapshot)
        assert violations == []

    def test_ntp_with_no_execution_claims(self) -> None:
        """NTP output with no execution claims -> empty list."""
        snapshot = _make_empty_snapshot()
        output = (
            "schema_version: nothing_to_propose.v1\n"
            "reason: No pending actionable tasks after policy checks.\n"
            "recommended_follow_up: Wait for blocked tasks to unblock.\n"
        )
        violations = verify_claims(output, snapshot)
        assert violations == []

    def test_no_false_positive_done_in_proposal_rationale(self) -> None:
        """'T-001 needs to be done by Friday' must not trigger a violation."""
        snapshot = _make_empty_snapshot()
        output = (
            "schema_version: task_proposal.v1\n"
            "proposals:\n"
            "  - task_id: T-001\n"
            "    rationale: T-001 needs to be done by end of sprint.\n"
            "    proposed_action: dispatch\n"
        )
        violations = verify_claims(output, snapshot)
        execution_violations = [v for v in violations if v.claim_type == "execution_state"]
        assert execution_violations == []

    def test_no_false_positive_ci_present_tense_conditional(self) -> None:
        """'make sure tests pass' in rationale must not trigger a CI violation."""
        snapshot = _make_empty_snapshot()
        output = (
            "schema_version: task_proposal.v1\n"
            "proposals:\n"
            "  - task_id: T-001\n"
            "    rationale: The build step will make sure all tests pass.\n"
            "    proposed_action: dispatch\n"
        )
        violations = verify_claims(output, snapshot)
        ci_violations = [v for v in violations if v.claim_type == "ci"]
        assert ci_violations == []


class TestEvidenceSnapshotFrozen:
    def test_evidence_snapshot_is_frozen(self) -> None:
        """Modifying the source list after snapshot creation doesn't affect results."""
        tasks = [_make_task("T-001")]
        active = ["ORD-T-001-001"]
        snapshot = EvidenceSnapshot(
            tasks=list(tasks),
            inbox_orders=[],
            active_orders=list(active),
            completed_orders={},
            manifest_entries=[],
            escalation_ids=[],
        )
        # Verify snapshot captured the state
        assert len(snapshot.active_orders) == 1
        assert snapshot.active_orders[0] == "ORD-T-001-001"

        # Modify the original list
        active.clear()
        tasks.clear()

        # Snapshot should be unaffected (it has its own copy)
        assert len(snapshot.active_orders) == 1


class TestCollectEvidence:
    def test_collect_evidence_empty_dirs(self, tmp_path: Path) -> None:
        """collect_evidence on empty repo -> no errors, returns empty snapshot."""
        (tmp_path / "config" / "tasks").mkdir(parents=True)
        snapshot = collect_evidence(tmp_path)
        assert snapshot.inbox_orders == []
        assert snapshot.active_orders == []
        assert snapshot.completed_orders == {}
        assert snapshot.tasks == []

    def test_collect_evidence_reads_inbox(self, tmp_path: Path) -> None:
        """Orders in inbox/ are captured in inbox_orders."""
        inbox = tmp_path / "artifacts" / "dispatch" / "inbox"
        inbox.mkdir(parents=True)
        (inbox / "ORD-T-001-20260310.yaml").write_text("order_id: ORD-T-001-20260310\n")
        snapshot = collect_evidence(tmp_path)
        assert "ORD-T-001-20260310" in snapshot.inbox_orders

    def test_collect_evidence_reads_active(self, tmp_path: Path) -> None:
        """Orders in active/ are captured in active_orders."""
        active = tmp_path / "artifacts" / "dispatch" / "active"
        active.mkdir(parents=True)
        (active / "ORD-T-002-20260310.yaml").write_text("order_id: ORD-T-002-20260310\n")
        snapshot = collect_evidence(tmp_path)
        assert "ORD-T-002-20260310" in snapshot.active_orders


class TestVerifyProgressObligation:
    def test_no_decline_returns_none(self) -> None:
        output = "I recommend dispatching T-009 as it has all prerequisites met."
        snapshot = _make_empty_snapshot()
        result = verify_progress_obligation(output, snapshot)
        assert result is None

    def test_ntp_with_policy_reference_passes(self) -> None:
        output = (
            "schema_version: nothing_to_propose.v1\n"
            "reason: All pending tasks require L3 approval per policy. No eligible tasks."
        )
        snapshot = _make_empty_snapshot()
        result = verify_progress_obligation(output, snapshot)
        assert result is None

    def test_ntp_with_blocked_task_reference_passes(self) -> None:
        output = (
            "schema_version: nothing_to_propose.v1\n"
            "reason: T-009 is blocked. Cannot proceed until blocker resolves."
        )
        snapshot = _make_empty_snapshot()
        result = verify_progress_obligation(output, snapshot)
        assert result is None

    def test_ntp_with_vague_reason_fails(self) -> None:
        output = (
            "schema_version: nothing_to_propose.v1\n"
            "reason: No pending actionable tasks.\n"
            "recommended_follow_up: Suggest waiting for alignment before proceeding."
        )
        snapshot = _make_empty_snapshot()
        result = verify_progress_obligation(output, snapshot)
        assert result is not None
        assert "PROGRESS_OBLIGATION_VIOLATION" in result

    def test_cannot_proceed_without_blocker_fails(self) -> None:
        output = "I cannot proceed at this time. I recommend careful review."
        snapshot = _make_empty_snapshot()
        result = verify_progress_obligation(output, snapshot)
        assert result is not None
        assert "PROGRESS_OBLIGATION_VIOLATION" in result
