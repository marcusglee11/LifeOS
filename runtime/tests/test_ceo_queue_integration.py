"""Integration tests for CEO Approval Queue."""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path

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
def test_repo(tmp_path: Path) -> Path:
    """Create a test repository structure."""
    repo = tmp_path / "test_repo"
    repo.mkdir()

    # Create necessary directories
    (repo / "artifacts").mkdir()
    (repo / "artifacts" / "queue").mkdir()
    (repo / "artifacts" / "loop_state").mkdir()
    (repo / "config").mkdir()
    (repo / "config" / "policy").mkdir()

    # Create a minimal policy config
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
def mission_context(test_repo: Path) -> MissionContext:
    """Create a test mission context."""
    return MissionContext(
        repo_root=test_repo,
        baseline_commit="test-baseline-commit",
        run_id="test-integration-001",
    )


class TestCEOQueueIntegration:
    """Integration tests for CEO queue with autonomous build cycle."""

    def test_queue_initialization(self, test_repo: Path):
        """Queue should initialize with empty database."""
        queue = CEOQueue(db_path=test_repo / "artifacts" / "queue" / "escalations.db")
        pending = queue.get_pending()
        assert len(pending) == 0

    def test_escalation_creation_and_retrieval(self, test_repo: Path):
        """Full flow: create escalation, retrieve, approve."""
        queue = CEOQueue(db_path=test_repo / "artifacts" / "queue" / "escalations.db")

        # Create escalation
        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={
                "path": "docs/01_governance/test.md",
                "action": "modify",
                "summary": "Attempted to modify governance document",
            },
            run_id="test-run-001",
        ))

        # Verify it's pending
        pending = queue.get_pending()
        assert len(pending) == 1
        assert pending[0].id == entry_id
        assert pending[0].type == EscalationType.GOVERNANCE_SURFACE_TOUCH

        # Retrieve by ID
        entry = queue.get_by_id(entry_id)
        assert entry is not None
        assert entry.status == EscalationStatus.PENDING

        # Approve
        result = queue.approve(entry_id, "Approved for testing", "CEO")
        assert result is True

        # Verify approval
        entry = queue.get_by_id(entry_id)
        assert entry.status == EscalationStatus.APPROVED
        assert entry.resolver == "CEO"

        # No longer in pending
        pending = queue.get_pending()
        assert len(pending) == 0

    def test_escalation_rejection_flow(self, test_repo: Path):
        """Full flow: create escalation, reject."""
        queue = CEOQueue(db_path=test_repo / "artifacts" / "queue" / "escalations.db")

        # Create escalation
        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.BUDGET_ESCALATION,
            context={
                "tokens_requested": 1000000,
                "reason": "Large refactoring task",
            },
            run_id="test-run-002",
        ))

        # Reject
        result = queue.reject(entry_id, "Budget too high", "CEO")
        assert result is True

        # Verify rejection
        entry = queue.get_by_id(entry_id)
        assert entry.status == EscalationStatus.REJECTED
        assert entry.resolution_note == "Budget too high"

    def test_multiple_escalations_ordering(self, test_repo: Path):
        """Multiple escalations should be ordered by age."""
        queue = CEOQueue(db_path=test_repo / "artifacts" / "queue" / "escalations.db")

        # Create multiple escalations
        ids = []
        for i in range(3):
            entry_id = queue.add_escalation(EscalationEntry(
                type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
                context={"index": i},
                run_id=f"test-run-{i:03d}",
            ))
            ids.append(entry_id)

        # Get pending - should be in order
        pending = queue.get_pending()
        assert len(pending) == 3
        assert pending[0].id == ids[0]  # Oldest first
        assert pending[1].id == ids[1]
        assert pending[2].id == ids[2]

        # Approve middle one
        queue.approve(ids[1], "Approved", "CEO")

        # Pending should now have 2
        pending = queue.get_pending()
        assert len(pending) == 2
        assert pending[0].id == ids[0]
        assert pending[1].id == ids[2]

    def test_timeout_detection(self, test_repo: Path, monkeypatch):
        """Escalations older than 24h should be detectable as stale."""
        queue = CEOQueue(db_path=test_repo / "artifacts" / "queue" / "escalations.db")
        mission = AutonomousBuildCycleMission()

        # Create an escalation with old timestamp
        entry = EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={"test": "timeout"},
            run_id="test-run-timeout",
        )

        # Manually set created_at to 25 hours ago
        entry.created_at = datetime.utcnow() - timedelta(hours=25)
        entry_id = queue.add_escalation(entry)

        # Check if stale
        retrieved = queue.get_by_id(entry_id)
        is_stale = mission._is_escalation_stale(retrieved)
        assert is_stale is True

        # Mark timeout
        queue.mark_timeout(entry_id)

        # Verify timeout status
        retrieved = queue.get_by_id(entry_id)
        assert retrieved.status == EscalationStatus.TIMEOUT

    def test_queue_persistence_across_instances(self, test_repo: Path):
        """Queue data should persist across different queue instances."""
        db_path = test_repo / "artifacts" / "queue" / "escalations.db"

        # Create first queue instance
        queue1 = CEOQueue(db_path=db_path)
        entry_id = queue1.add_escalation(EscalationEntry(
            type=EscalationType.POLICY_VIOLATION,
            context={"violation": "test"},
            run_id="test-run-persist",
        ))
        del queue1

        # Create second queue instance
        queue2 = CEOQueue(db_path=db_path)
        pending = queue2.get_pending()
        assert len(pending) == 1
        assert pending[0].id == entry_id

        # Approve via second instance
        queue2.approve(entry_id, "Approved", "CEO")
        del queue2

        # Create third queue instance - should see approval
        queue3 = CEOQueue(db_path=db_path)
        entry = queue3.get_by_id(entry_id)
        assert entry.status == EscalationStatus.APPROVED

    def test_escalation_context_preservation(self, test_repo: Path):
        """Complex escalation context should be preserved."""
        queue = CEOQueue(db_path=test_repo / "artifacts" / "queue" / "escalations.db")

        complex_context = {
            "path": "docs/01_governance/protocol.md",
            "action": "modify",
            "changes": {
                "lines_added": 10,
                "lines_removed": 5,
                "sections": ["introduction", "requirements"],
            },
            "rationale": "Update protocol for Phase 4",
            "metadata": {
                "author": "autonomous_loop",
                "timestamp": "2026-02-02T10:00:00Z",
            },
        }

        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context=complex_context,
            run_id="test-run-context",
        ))

        # Retrieve and verify context
        entry = queue.get_by_id(entry_id)
        assert entry.context == complex_context
        assert entry.context["changes"]["lines_added"] == 10
        assert "introduction" in entry.context["changes"]["sections"]

    def test_approval_with_conditions(self, test_repo: Path):
        """CEO can approve with conditional notes."""
        queue = CEOQueue(db_path=test_repo / "artifacts" / "queue" / "escalations.db")

        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.BUDGET_ESCALATION,
            context={"tokens": 50000},
            run_id="test-run-conditional",
        ))

        # Approve with conditions
        condition = "Approved only for P0 tasks. Revert if tests fail."
        queue.approve(entry_id, condition, "CEO")

        # Verify condition is stored
        entry = queue.get_by_id(entry_id)
        assert entry.status == EscalationStatus.APPROVED
        assert entry.resolution_note == condition

    def test_all_escalation_types_supported(self, test_repo: Path):
        """All escalation types should be creatable and retrievable."""
        queue = CEOQueue(db_path=test_repo / "artifacts" / "queue" / "escalations.db")

        types_to_test = [
            EscalationType.GOVERNANCE_SURFACE_TOUCH,
            EscalationType.BUDGET_ESCALATION,
            EscalationType.PROTECTED_PATH_MODIFICATION,
            EscalationType.AMBIGUOUS_TASK,
            EscalationType.POLICY_VIOLATION,
        ]

        created_ids = []
        for esc_type in types_to_test:
            entry_id = queue.add_escalation(EscalationEntry(
                type=esc_type,
                context={"type": esc_type.value},
                run_id=f"test-run-{esc_type.value}",
            ))
            created_ids.append((entry_id, esc_type))

        # Verify all created
        for entry_id, expected_type in created_ids:
            entry = queue.get_by_id(entry_id)
            assert entry is not None
            assert entry.type == expected_type

    def test_mission_escalation_helpers(self, test_repo: Path, mission_context: MissionContext):
        """Test autonomous_build_cycle escalation helper methods."""
        queue = CEOQueue(db_path=test_repo / "artifacts" / "queue" / "escalations.db")
        mission = AutonomousBuildCycleMission()

        # Test _escalate_to_ceo
        entry_id = mission._escalate_to_ceo(
            queue=queue,
            escalation_type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context_data={"path": "docs/01_governance/test.md"},
            run_id=mission_context.run_id,
        )

        assert entry_id is not None
        assert entry_id.startswith("ESC-")

        # Test _check_queue_for_approval (pending)
        entry = mission._check_queue_for_approval(queue, entry_id)
        assert entry is not None
        assert entry.status == EscalationStatus.PENDING

        # Approve the escalation
        queue.approve(entry_id, "Approved", "CEO")

        # Test _check_queue_for_approval (approved)
        entry = mission._check_queue_for_approval(queue, entry_id)
        assert entry is not None
        assert entry.status == EscalationStatus.APPROVED
