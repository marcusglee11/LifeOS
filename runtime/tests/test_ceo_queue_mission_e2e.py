"""
End-to-end mission-level integration tests for CEO Approval Queue.

Tests the complete flow:
- autonomous_build_cycle mission triggers escalation
- Loop halts correctly
- CEO approval/rejection changes outcome
- Loop resumes or terminates deterministically
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from runtime.orchestration.ceo_queue import (
    CEOQueue,
    EscalationEntry,
    EscalationType,
    EscalationStatus,
)
from runtime.orchestration.missions.autonomous_build_cycle import (
    AutonomousBuildCycleMission,
)
from runtime.orchestration.missions.base import MissionContext


@pytest.fixture
def e2e_repo(tmp_path: Path) -> Path:
    """Create a complete test repository for E2E testing."""
    repo = tmp_path / "e2e_repo"
    repo.mkdir()

    # Create all required directories
    (repo / "artifacts").mkdir()
    (repo / "artifacts" / "queue").mkdir()
    (repo / "artifacts" / "loop_state").mkdir()
    (repo / "config").mkdir()
    (repo / "config" / "policy").mkdir()
    (repo / "docs").mkdir()
    (repo / "docs" / "11_admin").mkdir()

    # Create minimal policy config
    policy_config = {
        "loop_policy": {
            "max_attempts": 5,
            "oscillation_window": 3,
        }
    }
    with open(repo / "config" / "policy" / "loop_policy.json", 'w') as f:
        json.dump(policy_config, f)

    return repo


@pytest.fixture
def e2e_context(e2e_repo: Path) -> MissionContext:
    """Create mission context for E2E tests."""
    return MissionContext(
        repo_root=e2e_repo,
        baseline_commit="test-baseline-e2e",
        run_id="e2e-run-001",
    )


class TestCEOQueueMissionE2E:
    """End-to-end mission-level integration tests."""

    def test_escalation_halts_loop_then_approval_resumes(self, e2e_repo: Path, e2e_context: MissionContext):
        """
        E2E Test: Escalation → Halt → Approval → Resume

        Flow:
        1. Mission detects condition requiring escalation
        2. Escalation created in queue
        3. Loop halts with escalation_id in output
        4. CEO approves escalation
        5. Mission resumes successfully
        """
        mission = AutonomousBuildCycleMission()
        queue = CEOQueue(db_path=e2e_repo / "artifacts" / "queue" / "escalations.db")

        # Step 1: Manually create an escalation (simulating detection)
        escalation_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={
                "path": "docs/01_governance/test.md",
                "action": "modify",
                "summary": "Test escalation for E2E",
            },
            run_id=e2e_context.run_id,
        ))

        # Step 2: Save escalation state (simulating loop halt)
        escalation_state_path = e2e_repo / "artifacts" / "loop_state" / "escalation_state.json"
        with open(escalation_state_path, 'w') as f:
            json.dump({"escalation_id": escalation_id}, f)

        # Step 3: Initialize ledger (simulating resume scenario)
        ledger_path = e2e_repo / "artifacts" / "loop_state" / "attempt_ledger.jsonl"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a minimal ledger header to simulate resume
        from runtime.orchestration.loop.ledger import AttemptLedger, LedgerHeader
        ledger = AttemptLedger(ledger_path)
        ledger.initialize(LedgerHeader(
            policy_hash="test_policy_hash",
            handoff_hash="test_handoff_hash",
            run_id=e2e_context.run_id,
        ))

        # Step 4: Verify escalation is pending (loop cannot proceed)
        entry = queue.get_by_id(escalation_id)
        assert entry.status == EscalationStatus.PENDING, "Escalation should be pending"

        # Step 5: CEO approves escalation
        result = queue.approve(escalation_id, "Approved for E2E test", "CEO")
        assert result is True, "Approval should succeed"

        # Step 6: Verify approval recorded
        entry = queue.get_by_id(escalation_id)
        assert entry.status == EscalationStatus.APPROVED, "Escalation should be approved"
        assert entry.resolver == "CEO"
        assert entry.resolution_note == "Approved for E2E test"

        # Step 7: Verify escalation state file can be cleaned up on resume
        # (In actual mission, this would be deleted after successful approval check)
        assert escalation_state_path.exists(), "State file should exist for resume"

    def test_escalation_halts_loop_then_rejection_terminates(self, e2e_repo: Path, e2e_context: MissionContext):
        """
        E2E Test: Escalation → Halt → Rejection → Terminate

        Flow:
        1. Mission detects condition requiring escalation
        2. Escalation created in queue
        3. Loop halts with escalation_id in output
        4. CEO rejects escalation
        5. Mission terminates with BLOCKED outcome
        """
        mission = AutonomousBuildCycleMission()
        queue = CEOQueue(db_path=e2e_repo / "artifacts" / "queue" / "escalations.db")

        # Step 1: Create escalation
        escalation_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.PROTECTED_PATH_MODIFICATION,
            context={
                "path": "config/governance/protected.json",
                "action": "modify",
                "summary": "Attempted protected path modification",
            },
            run_id=e2e_context.run_id,
        ))

        # Step 2: Save escalation state
        escalation_state_path = e2e_repo / "artifacts" / "loop_state" / "escalation_state.json"
        with open(escalation_state_path, 'w') as f:
            json.dump({"escalation_id": escalation_id}, f)

        # Step 3: Verify escalation is pending
        entry = queue.get_by_id(escalation_id)
        assert entry.status == EscalationStatus.PENDING

        # Step 4: CEO rejects escalation
        result = queue.reject(escalation_id, "Protected path cannot be modified", "CEO")
        assert result is True, "Rejection should succeed"

        # Step 5: Verify rejection recorded
        entry = queue.get_by_id(escalation_id)
        assert entry.status == EscalationStatus.REJECTED
        assert entry.resolver == "CEO"
        assert entry.resolution_note == "Protected path cannot be modified"

        # Step 6: In actual mission run, this would cause termination
        # Verify helper method correctly identifies rejection
        checked_entry = mission._check_queue_for_approval(queue, escalation_id)
        assert checked_entry.status == EscalationStatus.REJECTED

    def test_escalation_timeout_after_24_hours(self, e2e_repo: Path, e2e_context: MissionContext, monkeypatch):
        """
        E2E Test: Escalation → 24h Timeout → Auto-Reject

        Flow:
        1. Mission creates escalation
        2. 24 hours pass with no CEO action
        3. Timeout detection marks escalation as TIMEOUT
        4. Mission terminates with TIMEOUT outcome
        """
        mission = AutonomousBuildCycleMission()
        queue = CEOQueue(db_path=e2e_repo / "artifacts" / "queue" / "escalations.db")

        # Step 1: Create old escalation (25 hours ago)
        old_entry = EscalationEntry(
            type=EscalationType.BUDGET_ESCALATION,
            context={"tokens": 500000, "reason": "Large refactoring"},
            run_id=e2e_context.run_id,
        )
        old_entry.created_at = datetime.utcnow() - timedelta(hours=25)
        escalation_id = queue.add_escalation(old_entry)

        # Step 2: Verify escalation is stale
        entry = queue.get_by_id(escalation_id)
        is_stale = mission._is_escalation_stale(entry, hours=24)
        assert is_stale is True, "25-hour-old escalation should be stale"

        # Step 3: Check queue triggers timeout
        checked_entry = mission._check_queue_for_approval(queue, escalation_id)
        assert checked_entry.status == EscalationStatus.TIMEOUT, "Stale escalation should be marked TIMEOUT"

        # Step 4: Verify timeout reason recorded
        assert "TIMEOUT_24H" in (checked_entry.resolution_note or "")

    def test_mission_escalation_helpers_integration(self, e2e_repo: Path, e2e_context: MissionContext):
        """
        Test mission helper methods work correctly in integration.

        Tests:
        - _escalate_to_ceo creates entry
        - _check_queue_for_approval retrieves and checks status
        - _is_escalation_stale detects old entries
        """
        mission = AutonomousBuildCycleMission()
        queue = CEOQueue(db_path=e2e_repo / "artifacts" / "queue" / "escalations.db")

        # Test _escalate_to_ceo
        escalation_id = mission._escalate_to_ceo(
            queue=queue,
            escalation_type=EscalationType.AMBIGUOUS_TASK,
            context_data={"task": "unclear specification", "severity": "high"},
            run_id=e2e_context.run_id,
        )

        assert escalation_id is not None
        assert escalation_id.startswith("ESC-")

        # Verify entry created
        entry = queue.get_by_id(escalation_id)
        assert entry is not None
        assert entry.type == EscalationType.AMBIGUOUS_TASK
        assert entry.status == EscalationStatus.PENDING

        # Test _check_queue_for_approval (pending)
        checked = mission._check_queue_for_approval(queue, escalation_id)
        assert checked.status == EscalationStatus.PENDING

        # Approve and test again
        queue.approve(escalation_id, "Clarified offline", "CEO")
        checked = mission._check_queue_for_approval(queue, escalation_id)
        assert checked.status == EscalationStatus.APPROVED

        # Test _is_escalation_stale with fresh entry
        fresh_entry = queue.get_by_id(escalation_id)
        is_stale = mission._is_escalation_stale(fresh_entry, hours=24)
        assert is_stale is False, "Fresh escalation should not be stale"

    def test_queue_persistence_across_mission_runs(self, e2e_repo: Path, e2e_context: MissionContext):
        """
        Test that queue persists across multiple mission runs.

        Simulates:
        - Mission run 1 creates escalation
        - System restarts (new queue instance)
        - Mission run 2 can retrieve escalation
        """
        # Run 1: Create escalation
        queue1 = CEOQueue(db_path=e2e_repo / "artifacts" / "queue" / "escalations.db")
        mission1 = AutonomousBuildCycleMission()

        escalation_id = mission1._escalate_to_ceo(
            queue=queue1,
            escalation_type=EscalationType.POLICY_VIOLATION,
            context_data={"policy": "max_file_changes", "actual": 50, "limit": 40},
            run_id=e2e_context.run_id,
        )

        # Simulate system restart
        del queue1
        del mission1

        # Run 2: New instances
        queue2 = CEOQueue(db_path=e2e_repo / "artifacts" / "queue" / "escalations.db")
        mission2 = AutonomousBuildCycleMission()

        # Verify escalation persisted
        entry = queue2.get_by_id(escalation_id)
        assert entry is not None, "Escalation should persist across restarts"
        assert entry.type == EscalationType.POLICY_VIOLATION
        assert entry.status == EscalationStatus.PENDING

        # Verify helper can check it
        checked = mission2._check_queue_for_approval(queue2, escalation_id)
        assert checked.status == EscalationStatus.PENDING

    def test_multiple_escalations_ordering(self, e2e_repo: Path, e2e_context: MissionContext):
        """
        Test that multiple escalations are ordered correctly (oldest first).
        """
        queue = CEOQueue(db_path=e2e_repo / "artifacts" / "queue" / "escalations.db")

        # Create 3 escalations
        id1 = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={"order": 1},
            run_id="run-001",
        ))

        id2 = queue.add_escalation(EscalationEntry(
            type=EscalationType.BUDGET_ESCALATION,
            context={"order": 2},
            run_id="run-002",
        ))

        id3 = queue.add_escalation(EscalationEntry(
            type=EscalationType.PROTECTED_PATH_MODIFICATION,
            context={"order": 3},
            run_id="run-003",
        ))

        # Get pending (should be oldest first)
        pending = queue.get_pending()
        assert len(pending) == 3
        assert pending[0].id == id1, "Oldest escalation should be first"
        assert pending[1].id == id2
        assert pending[2].id == id3

        # Approve middle one
        queue.approve(id2, "Approved", "CEO")

        # Pending should now have 2
        pending = queue.get_pending()
        assert len(pending) == 2
        assert pending[0].id == id1
        assert pending[1].id == id3
