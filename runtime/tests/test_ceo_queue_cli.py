"""
Automated tests for CEO Approval Queue CLI commands.

Tests the CLI interface:
- coo queue list
- coo queue show <id>
- coo queue approve <id> [--note]
- coo queue reject <id> --reason
"""

import pytest
import json
import subprocess
from pathlib import Path

from runtime.orchestration.ceo_queue import (
    CEOQueue,
    EscalationEntry,
    EscalationType,
    EscalationStatus,
)
from runtime.cli import (
    cmd_queue_list,
    cmd_queue_show,
    cmd_queue_approve,
    cmd_queue_reject,
)


@pytest.fixture
def cli_repo(tmp_path: Path) -> Path:
    """Create a test repository for CLI testing."""
    repo = tmp_path / "cli_repo"
    repo.mkdir()
    (repo / "artifacts").mkdir()
    (repo / "artifacts" / "queue").mkdir()
    return repo


@pytest.fixture
def cli_queue(cli_repo: Path) -> CEOQueue:
    """Create a queue for CLI testing."""
    return CEOQueue(db_path=cli_repo / "artifacts" / "queue" / "escalations.db")


@pytest.fixture
def sample_escalation(cli_queue: CEOQueue) -> str:
    """Create a sample escalation for testing."""
    return cli_queue.add_escalation(EscalationEntry(
        type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
        context={
            "path": "docs/01_governance/test.md",
            "action": "modify",
            "summary": "Test escalation for CLI",
        },
        run_id="cli-test-run-001",
    ))


class TestCEOQueueCLI:
    """Automated tests for CLI commands."""

    def test_cmd_queue_list_empty(self, cli_repo: Path, capsys):
        """Test queue list command with empty queue."""
        import argparse
        args = argparse.Namespace()

        result = cmd_queue_list(args, cli_repo)

        assert result == 0, "Command should succeed"
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == [], "Empty queue should return empty array"

    def test_cmd_queue_list_with_entries(self, cli_repo: Path, cli_queue: CEOQueue, sample_escalation: str, capsys):
        """Test queue list command with entries."""
        import argparse
        args = argparse.Namespace()

        result = cmd_queue_list(args, cli_repo)

        assert result == 0, "Command should succeed"
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert len(output) == 1, "Should have one entry"
        assert output[0]["id"] == sample_escalation
        assert output[0]["type"] == "governance_surface_touch"
        assert "age_hours" in output[0]
        assert output[0]["summary"] == "Test escalation for CLI"
        assert output[0]["run_id"] == "cli-test-run-001"

    def test_cmd_queue_show_existing(self, cli_repo: Path, sample_escalation: str, capsys):
        """Test queue show command for existing escalation."""
        import argparse
        args = argparse.Namespace(escalation_id=sample_escalation)

        result = cmd_queue_show(args, cli_repo)

        assert result == 0, "Command should succeed"
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert output["id"] == sample_escalation
        assert output["type"] == "governance_surface_touch"
        assert output["status"] == "pending"
        assert output["run_id"] == "cli-test-run-001"
        assert output["context"]["path"] == "docs/01_governance/test.md"
        assert output["resolved_at"] is None
        assert output["resolution_note"] is None
        assert output["resolver"] is None

    def test_cmd_queue_show_nonexistent(self, cli_repo: Path, capsys):
        """Test queue show command for nonexistent escalation."""
        import argparse
        args = argparse.Namespace(escalation_id="ESC-9999")

        result = cmd_queue_show(args, cli_repo)

        assert result == 1, "Command should fail for nonexistent ID"
        captured = capsys.readouterr()
        assert "Error: Escalation ESC-9999 not found" in captured.out

    def test_cmd_queue_approve_without_note(self, cli_repo: Path, sample_escalation: str, cli_queue: CEOQueue, capsys):
        """Test queue approve command without note."""
        import argparse
        args = argparse.Namespace(escalation_id=sample_escalation, note=None)

        result = cmd_queue_approve(args, cli_repo)

        assert result == 0, "Command should succeed"
        captured = capsys.readouterr()
        assert f"Approved: {sample_escalation}" in captured.out

        # Verify approval recorded
        entry = cli_queue.get_by_id(sample_escalation)
        assert entry.status == EscalationStatus.APPROVED
        assert entry.resolution_note == "Approved via CLI"
        assert entry.resolver == "CEO"

    def test_cmd_queue_approve_with_note(self, cli_repo: Path, cli_queue: CEOQueue, capsys):
        """Test queue approve command with custom note."""
        # Create new escalation
        escalation_id = cli_queue.add_escalation(EscalationEntry(
            type=EscalationType.BUDGET_ESCALATION,
            context={"tokens": 50000},
            run_id="cli-test-run-002",
        ))

        import argparse
        args = argparse.Namespace(escalation_id=escalation_id, note="Approved for P0 only")

        result = cmd_queue_approve(args, cli_repo)

        assert result == 0, "Command should succeed"
        captured = capsys.readouterr()
        assert f"Approved: {escalation_id}" in captured.out

        # Verify custom note recorded
        entry = cli_queue.get_by_id(escalation_id)
        assert entry.status == EscalationStatus.APPROVED
        assert entry.resolution_note == "Approved for P0 only"

    def test_cmd_queue_approve_nonexistent(self, cli_repo: Path, capsys):
        """Test queue approve command for nonexistent escalation."""
        import argparse
        args = argparse.Namespace(escalation_id="ESC-9999", note=None)

        result = cmd_queue_approve(args, cli_repo)

        assert result == 1, "Command should fail for nonexistent ID"
        captured = capsys.readouterr()
        assert "Error: Could not approve ESC-9999" in captured.out

    def test_cmd_queue_reject_with_reason(self, cli_repo: Path, sample_escalation: str, cli_queue: CEOQueue, capsys):
        """Test queue reject command with reason."""
        import argparse
        args = argparse.Namespace(escalation_id=sample_escalation, reason="Out of scope for this sprint")

        result = cmd_queue_reject(args, cli_repo)

        assert result == 0, "Command should succeed"
        captured = capsys.readouterr()
        assert f"Rejected: {sample_escalation}" in captured.out

        # Verify rejection recorded
        entry = cli_queue.get_by_id(sample_escalation)
        assert entry.status == EscalationStatus.REJECTED
        assert entry.resolution_note == "Out of scope for this sprint"
        assert entry.resolver == "CEO"

    def test_cmd_queue_reject_without_reason(self, cli_repo: Path, sample_escalation: str, capsys):
        """Test queue reject command without reason (should fail)."""
        import argparse
        args = argparse.Namespace(escalation_id=sample_escalation, reason=None)

        result = cmd_queue_reject(args, cli_repo)

        assert result == 1, "Command should fail without reason"
        captured = capsys.readouterr()
        assert "Error: --reason is required for rejection" in captured.out

    def test_cmd_queue_reject_nonexistent(self, cli_repo: Path, capsys):
        """Test queue reject command for nonexistent escalation."""
        import argparse
        args = argparse.Namespace(escalation_id="ESC-9999", reason="Test reason")

        result = cmd_queue_reject(args, cli_repo)

        assert result == 1, "Command should fail for nonexistent ID"
        captured = capsys.readouterr()
        assert "Error: Could not reject ESC-9999" in captured.out

    def test_cmd_queue_approve_already_resolved(self, cli_repo: Path, cli_queue: CEOQueue, capsys):
        """Test that approving an already-resolved escalation fails."""
        # Create and approve escalation
        escalation_id = cli_queue.add_escalation(EscalationEntry(
            type=EscalationType.POLICY_VIOLATION,
            context={"violation": "test"},
            run_id="cli-test-run-003",
        ))
        cli_queue.approve(escalation_id, "First approval", "CEO")

        # Try to approve again
        import argparse
        args = argparse.Namespace(escalation_id=escalation_id, note="Second approval")

        result = cmd_queue_approve(args, cli_repo)

        assert result == 1, "Command should fail for already-resolved escalation"
        captured = capsys.readouterr()
        assert f"Error: Could not approve {escalation_id}" in captured.out

    def test_queue_list_ordering(self, cli_repo: Path, cli_queue: CEOQueue, capsys):
        """Test that queue list returns entries in correct order (oldest first)."""
        # Create multiple escalations
        id1 = cli_queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={"order": 1},
            run_id="run-001",
        ))
        id2 = cli_queue.add_escalation(EscalationEntry(
            type=EscalationType.BUDGET_ESCALATION,
            context={"order": 2},
            run_id="run-002",
        ))
        id3 = cli_queue.add_escalation(EscalationEntry(
            type=EscalationType.PROTECTED_PATH_MODIFICATION,
            context={"order": 3},
            run_id="run-003",
        ))

        import argparse
        args = argparse.Namespace()
        result = cmd_queue_list(args, cli_repo)

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        assert len(output) == 3
        # Oldest first
        assert output[0]["id"] == id1
        assert output[1]["id"] == id2
        assert output[2]["id"] == id3

    def test_queue_list_filters_resolved(self, cli_repo: Path, cli_queue: CEOQueue, capsys):
        """Test that queue list only shows pending escalations."""
        # Create 3 escalations
        id1 = cli_queue.add_escalation(EscalationEntry(
            type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
            context={"status": "pending"},
            run_id="run-001",
        ))
        id2 = cli_queue.add_escalation(EscalationEntry(
            type=EscalationType.BUDGET_ESCALATION,
            context={"status": "will-approve"},
            run_id="run-002",
        ))
        id3 = cli_queue.add_escalation(EscalationEntry(
            type=EscalationType.PROTECTED_PATH_MODIFICATION,
            context={"status": "pending"},
            run_id="run-003",
        ))

        # Approve middle one
        cli_queue.approve(id2, "Approved", "CEO")

        import argparse
        args = argparse.Namespace()
        result = cmd_queue_list(args, cli_repo)

        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)

        # Should only have 2 pending
        assert len(output) == 2
        assert output[0]["id"] == id1
        assert output[1]["id"] == id3
        # id2 should not be in list
        assert id2 not in [e["id"] for e in output]
