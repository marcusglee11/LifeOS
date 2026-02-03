"""Unit tests for CEO Approval Queue."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path

from runtime.orchestration.ceo_queue import (
    CEOQueue,
    EscalationEntry,
    EscalationType,
    EscalationStatus,
)


@pytest.fixture
def queue(tmp_path: Path) -> CEOQueue:
    """Create a fresh queue for each test."""
    return CEOQueue(db_path=tmp_path / "test_queue.db")


class TestCEOQueue:
    """Unit tests for CEOQueue class."""

    def test_add_escalation_creates_entry(self, queue):
        """add_escalation should create entry with unique ID."""
        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={"path": "docs/01_governance/test.md"},
            run_id="test-run-001",
        ))

        assert entry_id is not None
        assert entry_id.startswith("ESC-")
        assert len(queue.get_pending()) == 1

    def test_get_pending_returns_only_pending_entries(self, queue):
        """get_pending should filter out resolved entries."""
        id1 = queue.add_escalation(EscalationEntry(
            type=EscalationType.BUDGET_ESCALATION,
            context={"budget": 100000},
            run_id="test-run-002",
        ))
        id2 = queue.add_escalation(EscalationEntry(
            type=EscalationType.POLICY_VIOLATION,
            context={"policy": "max_attempts"},
            run_id="test-run-003",
        ))

        queue.approve(id2, "Approved", "CEO")

        pending = queue.get_pending()
        assert len(pending) == 1
        assert pending[0].id == id1

    def test_approve_updates_status(self, queue):
        """approve should update status and record approval context."""
        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={"path": "docs/01_governance/test.md"},
            run_id="test-run-004",
        ))

        result = queue.approve(entry_id, note="Approved for P0", resolver="CEO")

        assert result is True
        entry = queue.get_by_id(entry_id)
        assert entry.status == EscalationStatus.APPROVED
        assert entry.resolution_note == "Approved for P0"
        assert entry.resolver == "CEO"
        assert entry.resolved_at is not None

    def test_reject_updates_status(self, queue):
        """reject should update status and record reason."""
        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.PROTECTED_PATH_MODIFICATION,
            context={"path": "config/governance/protected.json"},
            run_id="test-run-005",
        ))

        result = queue.reject(entry_id, reason="Out of scope", resolver="CEO")

        assert result is True
        entry = queue.get_by_id(entry_id)
        assert entry.status == EscalationStatus.REJECTED
        assert entry.resolution_note == "Out of scope"

    def test_persistence_survives_restart(self, tmp_path):
        """Queue entries should persist across restarts."""
        db_path = tmp_path / "persist_test.db"

        # Create and populate first queue instance
        queue1 = CEOQueue(db_path=db_path)
        entry_id = queue1.add_escalation(EscalationEntry(
            type=EscalationType.AMBIGUOUS_TASK,
            context={"task": "unclear spec"},
            run_id="test-run-006",
        ))
        del queue1

        # Create new queue instance pointing to same DB
        queue2 = CEOQueue(db_path=db_path)
        pending = queue2.get_pending()

        assert len(pending) == 1
        assert pending[0].id == entry_id
        assert pending[0].type == EscalationType.AMBIGUOUS_TASK

    def test_approve_fails_for_invalid_id(self, queue):
        """approve should return False for non-existent ID."""
        result = queue.approve("ESC-INVALID", "Note", "CEO")
        assert result is False

    def test_approve_fails_for_already_resolved(self, queue):
        """approve should fail for already-resolved entry."""
        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.BUDGET_ESCALATION,
            context={},
            run_id="test-run-007",
        ))
        queue.approve(entry_id, "First approval", "CEO")

        result = queue.approve(entry_id, "Second approval", "CEO")
        assert result is False

    def test_reject_fails_for_already_resolved(self, queue):
        """reject should fail for already-resolved entry."""
        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.BUDGET_ESCALATION,
            context={},
            run_id="test-run-008",
        ))
        queue.reject(entry_id, "First rejection", "CEO")

        result = queue.reject(entry_id, "Second rejection", "CEO")
        assert result is False

    def test_mark_timeout(self, queue):
        """mark_timeout should set status to TIMEOUT."""
        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={},
            run_id="test-run-009",
        ))

        result = queue.mark_timeout(entry_id)

        assert result is True
        entry = queue.get_by_id(entry_id)
        assert entry.status == EscalationStatus.TIMEOUT

    def test_unique_ids_generated(self, queue):
        """Each escalation should get a unique ID."""
        ids = set()
        for i in range(10):
            entry_id = queue.add_escalation(EscalationEntry(
                type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
                context={"index": i},
                run_id=f"test-run-{100+i}",
            ))
            ids.add(entry_id)

        assert len(ids) == 10

    def test_get_by_id_returns_none_for_invalid_id(self, queue):
        """get_by_id should return None for non-existent ID."""
        entry = queue.get_by_id("ESC-INVALID")
        assert entry is None

    def test_pending_ordered_by_age(self, queue):
        """get_pending should return entries ordered by created_at ascending."""
        # Add entries with slight delays to ensure different timestamps
        id1 = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={"order": 1},
            run_id="test-run-010",
        ))

        id2 = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={"order": 2},
            run_id="test-run-011",
        ))

        id3 = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={"order": 3},
            run_id="test-run-012",
        ))

        pending = queue.get_pending()
        assert len(pending) == 3
        # Oldest first
        assert pending[0].id == id1
        assert pending[1].id == id2
        assert pending[2].id == id3

    def test_context_serialization(self, queue):
        """Context should be properly serialized and deserialized."""
        complex_context = {
            "path": "docs/test.md",
            "action": "modify",
            "details": {
                "lines": [1, 2, 3],
                "nested": {"key": "value"}
            }
        }

        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context=complex_context,
            run_id="test-run-013",
        ))

        entry = queue.get_by_id(entry_id)
        assert entry.context == complex_context

    def test_approval_with_empty_note(self, queue):
        """approve should work with empty note."""
        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={},
            run_id="test-run-014",
        ))

        result = queue.approve(entry_id, note="", resolver="CEO")

        assert result is True
        entry = queue.get_by_id(entry_id)
        assert entry.status == EscalationStatus.APPROVED
        assert entry.resolution_note == ""

    def test_rejection_with_empty_reason(self, queue):
        """reject should work with empty reason."""
        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={},
            run_id="test-run-015",
        ))

        result = queue.reject(entry_id, reason="", resolver="CEO")

        assert result is True
        entry = queue.get_by_id(entry_id)
        assert entry.status == EscalationStatus.REJECTED
        assert entry.resolution_note == ""

    def test_all_escalation_types(self, queue):
        """Test that all escalation types can be created and retrieved."""
        types = [
            EscalationType.GOVERNANCE_SURFACE_TOUCH,
            EscalationType.BUDGET_ESCALATION,
            EscalationType.PROTECTED_PATH_MODIFICATION,
            EscalationType.AMBIGUOUS_TASK,
            EscalationType.POLICY_VIOLATION,
        ]

        for esc_type in types:
            entry_id = queue.add_escalation(EscalationEntry(
                type=esc_type,
                context={"type": esc_type.value},
                run_id=f"test-run-{esc_type.value}",
            ))

            entry = queue.get_by_id(entry_id)
            assert entry.type == esc_type

    def test_timeout_does_not_change_pending_status(self, queue):
        """mark_timeout should work even if entry was already resolved."""
        entry_id = queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={},
            run_id="test-run-016",
        ))

        queue.approve(entry_id, "Approved", "CEO")
        result = queue.mark_timeout(entry_id)

        # Should still return True even if already resolved
        assert result is True
        entry = queue.get_by_id(entry_id)
        # Status should be TIMEOUT now, not APPROVED
        assert entry.status == EscalationStatus.TIMEOUT
