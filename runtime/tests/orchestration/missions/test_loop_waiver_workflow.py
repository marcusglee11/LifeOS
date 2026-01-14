"""
Integration tests for Loop Waiver Workflow (Phase B.3)

Tests waiver request emission, approval CLI, and resume logic with POFV validation.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from runtime.orchestration.missions.autonomous_build_cycle import AutonomousBuildCycleMission
from runtime.orchestration.missions.base import MissionResult, MissionContext, MissionType
from runtime.orchestration.loop.taxonomy import TerminalReason, TerminalOutcome, FailureClass


# Import approve_waiver functions for testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent / "scripts/loop"))
from approve_waiver import approve_waiver, reject_waiver, get_debt_score


@pytest.fixture
def waiver_context(tmp_path):
    """Create a mission context for waiver workflow tests."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "artifacts").mkdir()
    (repo / "artifacts/loop_state").mkdir(parents=True)
    (repo / "config/loop").mkdir(parents=True)
    (repo / "config/governance").mkdir(parents=True)
    (repo / "docs/11_admin").mkdir(parents=True)
    (repo / "docs/00_foundations").mkdir(parents=True)
    (repo / "docs/01_governance").mkdir(parents=True)

    # Plant protected artefacts config (required for governance protection)
    protected_config = {
        "protected_paths": [
            "docs/00_foundations",
            "docs/01_governance",
            "config/governance/protected_artefacts.json"
        ]
    }
    protected_path = repo / "config/governance/protected_artefacts.json"
    protected_path.write_text(json.dumps(protected_config, indent=2), encoding='utf-8')

    # Initialize BACKLOG.md for debt registration (required for waiver workflow)
    backlog_path = repo / "docs/11_admin/BACKLOG.md"
    backlog_path.write_text("# BACKLOG\n\n## Technical Debt\n\n", encoding='utf-8')

    return MissionContext(
        repo_root=repo,
        baseline_commit="abc123",
        run_id="waiver_test_run",
        operation_executor=None,
        journal=None,
        metadata={}
    )


def mock_review_behavior(context, inputs):
    """Mock review behavior: approve design, reject output."""
    review_type = inputs.get("review_type")
    if review_type == "design_review":
        return MissionResult(
            True, MissionType.REVIEW,
            outputs={"verdict": "approved", "council_decision": {"synthesis": "Design OK"}},
            evidence={"usage": {"total": 1}}
        )
    else:
        return MissionResult(
            True, MissionType.REVIEW,
            outputs={"verdict": "rejected", "council_decision": {"synthesis": "Output needs work"}},
            evidence={"usage": {"total": 1}}
        )





class TestWaiverApprovalCLI:
    """Test approve_waiver.py CLI functionality."""

    def test_approve_waiver_creates_valid_decision_file(self, waiver_context):
        """approve_waiver.py APPROVE creates valid decision file with stable debt ID."""
        # Create mock waiver request
        waiver_request_path = waiver_context.repo_root / "artifacts/loop_state" / f"WAIVER_REQUEST_{waiver_context.run_id}.md"
        waiver_request_path.write_text(f"""# WAIVER REQUEST: {waiver_context.run_id}

**Date**: 2026-01-14T10:00:00Z
**Failure Class**: review_rejection
**Attempts Made**: 3
""", encoding='utf-8')

        # Approve waiver
        approve_waiver(waiver_context.run_id, "Test approval", waiver_context.repo_root)

        # Verify decision file
        decision_path = waiver_context.repo_root / "artifacts/loop_state" / f"WAIVER_DECISION_{waiver_context.run_id}.json"
        assert decision_path.exists()

        with open(decision_path, 'r') as f:
            decision = json.load(f)
            assert decision["decision"] == "APPROVE"
            assert decision["run_id"] == waiver_context.run_id
            assert decision["debt_registered"] is True
            assert decision["debt_id"] == f"DEBT-{waiver_context.run_id}"  # Stable ID!
            assert "waiver_request_hash" in decision
            assert "debt_score" in decision

    def test_approve_waiver_registers_debt_in_backlog(self, waiver_context):
        """approve_waiver.py APPROVE registers debt in BACKLOG.md with stable debt ID."""
        # Create mock waiver request
        waiver_request_path = waiver_context.repo_root / "artifacts/loop_state" / f"WAIVER_REQUEST_{waiver_context.run_id}.md"
        waiver_request_path.write_text(f"""# WAIVER REQUEST: {waiver_context.run_id}

**Date**: 2026-01-14T10:00:00Z
**Failure Class**: test_failure
**Attempts Made**: 3
""", encoding='utf-8')

        # Approve waiver
        approve_waiver(waiver_context.run_id, "Test approval", waiver_context.repo_root)

        # Verify BACKLOG.md entry
        backlog_path = waiver_context.repo_root / "docs/11_admin/BACKLOG.md"
        assert backlog_path.exists()

        with open(backlog_path, 'r') as f:
            backlog_content = f.read()
            debt_id = f"DEBT-{waiver_context.run_id}"
            assert debt_id in backlog_content, "Stable debt ID should be in BACKLOG"
            assert "Score: 30" in backlog_content  # TEST_FAILURE score
            assert "test_failure" in backlog_content
            # Verify NO line numbers in debt ID format
            assert f"[{debt_id}]" in backlog_content

    def test_reject_waiver_creates_decision_file_without_debt(self, waiver_context):
        """approve_waiver.py REJECT creates decision file without debt registration."""
        # Create mock waiver request
        waiver_request_path = waiver_context.repo_root / "artifacts/loop_state" / f"WAIVER_REQUEST_{waiver_context.run_id}.md"
        waiver_request_path.write_text(f"""# WAIVER REQUEST: {waiver_context.run_id}

**Date**: 2026-01-14T10:00:00Z
**Failure Class**: review_rejection
**Attempts Made**: 3
""", encoding='utf-8')

        # Reject waiver
        reject_waiver(waiver_context.run_id, "Requires manual fix", waiver_context.repo_root)

        # Verify decision file
        decision_path = waiver_context.repo_root / "artifacts/loop_state" / f"WAIVER_DECISION_{waiver_context.run_id}.json"
        assert decision_path.exists()

        with open(decision_path, 'r') as f:
            decision = json.load(f)
            assert decision["decision"] == "REJECT"
            assert decision["debt_registered"] is False
            assert decision["debt_id"] is None
            assert "Requires manual fix" in decision["rationale"]

        # Verify NO BACKLOG entry
        backlog_path = waiver_context.repo_root / "docs/11_admin/BACKLOG.md"
        if backlog_path.exists():
            with open(backlog_path, 'r') as f:
                backlog_content = f.read()
                assert waiver_context.run_id not in backlog_content

    def test_debt_score_calculation(self):
        """Debt scores are calculated correctly for different failure classes."""
        assert get_debt_score("test_failure") == 30
        assert get_debt_score("review_rejection") == 40
        assert get_debt_score("timeout") == 50
        assert get_debt_score("unknown") == 50


class TestWaiverResumeLogic:
    """Test waiver resume logic with POFV validation."""

    @patch('runtime.orchestration.missions.autonomous_build_cycle.DesignMission')
    def test_waiver_approve_resume_pass(self, DesignMock, waiver_context):
        """Resuming after APPROVE waiver terminates with PASS (WAIVER_APPROVED)."""
        # Create approved waiver decision
        decision = {
            "run_id": waiver_context.run_id,
            "decision": "APPROVE",
            "debt_registered": True,
            "debt_id": f"DEBT-{waiver_context.run_id}",
            "waiver_request_hash": "abc123"
        }
        decision_path = waiver_context.repo_root / "artifacts/loop_state" / f"WAIVER_DECISION_{waiver_context.run_id}.json"
        decision_path.write_text(json.dumps(decision), encoding='utf-8')

        # Create ledger (resume scenario)
        ledger_path = waiver_context.repo_root / "artifacts/loop_state/attempt_ledger.jsonl"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        header = {
            "type": "header",  # Required by ledger hydration
            "schema_version": "v1.0",
            "policy_hash": "phase_a_hardcoded_v1",  # Must match runtime's Phase A policy hash
            "handoff_hash": "abc",
            "run_id": waiver_context.run_id
        }
        ledger_path.write_text(json.dumps(header) + "\n", encoding='utf-8')

        mission = AutonomousBuildCycleMission()
        result = mission.run(waiver_context, {"task_spec": "test"})

        # Verify PASS via waiver
        assert result.success is True
        assert result.outputs["status"] == "waived"
        assert result.outputs["debt_id"] == f"DEBT-{waiver_context.run_id}"

        # Verify terminal packet says WAIVER_APPROVED
        terminal_path = waiver_context.repo_root / "artifacts/CEO_Terminal_Packet.md"
        assert terminal_path.exists()
        with open(terminal_path, 'r') as f:
            terminal_content = f.read()
            assert "waiver_approved" in terminal_content.lower()

    @patch('runtime.orchestration.missions.autonomous_build_cycle.DesignMission')
    def test_waiver_reject_resume_blocked(self, DesignMock, waiver_context):
        """Resuming after REJECT waiver terminates with BLOCKED (WAIVER_REJECTED)."""
        # Create rejected waiver decision
        decision = {
            "run_id": waiver_context.run_id,
            "decision": "REJECT",
            "debt_registered": False,
            "debt_id": None,
            "rationale": "Requires manual intervention",
            "waiver_request_hash": "abc123"
        }
        decision_path = waiver_context.repo_root / "artifacts/loop_state" / f"WAIVER_DECISION_{waiver_context.run_id}.json"
        decision_path.write_text(json.dumps(decision), encoding='utf-8')

        # Create ledger (resume scenario)
        ledger_path = waiver_context.repo_root / "artifacts/loop_state/attempt_ledger.jsonl"
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        header = {
            "type": "header",  # Required by ledger hydration
            "schema_version": "v1.0",
            "policy_hash": "phase_a_hardcoded_v1",  # Must match runtime's Phase A policy hash
            "handoff_hash": "abc",
            "run_id": waiver_context.run_id
        }
        ledger_path.write_text(json.dumps(header) + "\n", encoding='utf-8')

        mission = AutonomousBuildCycleMission()
        result = mission.run(waiver_context, {"task_spec": "test"})

        # Verify BLOCKED
        assert result.success is False
        assert "waiver rejected" in result.error.lower()

        # Verify terminal packet says WAIVER_REJECTED
        terminal_path = waiver_context.repo_root / "artifacts/CEO_Terminal_Packet.md"
        assert terminal_path.exists()
        with open(terminal_path, 'r') as f:
            terminal_content = f.read()
            assert "waiver_rejected" in terminal_content.lower()
