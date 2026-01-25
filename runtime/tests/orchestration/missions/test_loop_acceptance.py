import pytest
import json
import subprocess
from unittest.mock import MagicMock, patch
from runtime.orchestration.missions.autonomous_build_cycle import AutonomousBuildCycleMission
from runtime.orchestration.missions.base import MissionContext, MissionResult, MissionType
from runtime.orchestration.loop.taxonomy import TerminalReason, TerminalOutcome
from runtime.governance.baseline_checker import BaselineManifest

@pytest.fixture
def acceptance_context(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    # Initialize git repo (required for verify_repo_clean)
    subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_root, check=True, capture_output=True)

    # Create initial commit (required for baseline)
    (repo_root / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "README.md"], cwd=repo_root, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_root, check=True, capture_output=True)

    # Create artifacts directory structure
    (repo_root / "artifacts" / "loop_state").mkdir(parents=True)

    return MissionContext(
        repo_root=repo_root,
        baseline_commit="abc",
        run_id="acc_run",
        operation_executor=None
    )

@pytest.fixture
def mock_preconditions():
    """Mock the P0 precondition checks and policy loader to allow tests to focus on loop logic."""
    with patch("runtime.orchestration.missions.autonomous_build_cycle.verify_repo_clean") as mock_clean, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.verify_governance_baseline") as mock_baseline, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.PolicyLoader") as mock_policy_loader:
        # verify_repo_clean returns None on success (raises on failure)
        mock_clean.return_value = None
        # verify_governance_baseline returns a manifest on success
        mock_baseline.return_value = BaselineManifest(
            baseline_version="1.0",
            approved_by="CEO",
            council_ruling_ref=None,
            hash_algorithm="SHA-256",
            path_normalization="relpath_from_repo_root",
            artifacts=[],
        )
        # PolicyLoader returns minimal effective config
        loader_instance = MagicMock()
        loader_instance.load.return_value = {
            "schema_version": "1.2",
            "posture": {"mode": "PRIMARY"},
            "loop_rules": [],
        }
        mock_policy_loader.return_value = loader_instance
        yield mock_clean, mock_baseline

@pytest.fixture
def mock_subs():
    with patch("runtime.orchestration.missions.autonomous_build_cycle.DesignMission") as D, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.BuildMission") as B, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.ReviewMission") as R, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.StewardMission") as S:
        yield D, B, R, S

def mock_review_behavior(ctx, inputs):
    # Approve Design Review to enter loop
    if inputs.get("review_type") == "build_review":
        return MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved", "council_decision": {}}, evidence={"usage":{"total":1}})
    # Reject Output Review to force loop retry/failure
    return MissionResult(True, MissionType.REVIEW, outputs={"verdict": "rejected", "council_decision": {"synthesis": "rejected"}}, evidence={"usage":{"total":1}})

def test_crash_and_resume(acceptance_context, mock_subs, mock_preconditions):
    D, B, R, S = mock_subs
    
    D.return_value.run.return_value = MissionResult(True, MissionType.DESIGN, outputs={"build_packet": {"goal":"g"}}, evidence={"usage":{"total":1}})
    
    # Use smart side effect for Review
    R.return_value.run.side_effect = mock_review_behavior

    # Run 1: Fails at Attempt 1 (Crash/Interruption simulated by exception or just fail)
    # Attempt 1: Review Rejection (Retry)
    
    B.return_value.run.side_effect = [
        MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "diff1"}}}, evidence={"usage":{"total":1}}),
        KeyboardInterrupt("Simulate Crash")
    ]
    
    mission = AutonomousBuildCycleMission()
    inputs = {"task_spec": "resume_test"}
    
    try:
        mission.run(acceptance_context, inputs)
    except KeyboardInterrupt:
        pass
        
    # Verify Ledger has Attempt 1
    ledger_path = acceptance_context.repo_root / "artifacts/loop_state/attempt_ledger.jsonl"
    with open(ledger_path) as f:
        lines = f.readlines()
        assert len(lines) == 2 # Header + 1 record
        rec = json.loads(lines[1])
        assert rec["attempt_id"] == 1
        
    # Run 2: Resume
    # Reset mocks for Run 2
    # Design approved again
    # Attempt 2 (Now resuming): Succeeds
    B.return_value.run.side_effect = None
    B.return_value.run.return_value = MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "diff2"}}}, evidence={"usage":{"total":1}})
    
    # Needs sequence: Design (Approve), Output (Approve)
    def mock_resume_review(ctx, inputs):
         if inputs.get("review_type") == "build_review":
             return MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved", "council_decision": {}}, evidence={"usage":{"total":1}})
         return MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved", "council_decision": {}}, evidence={"usage":{"total":1}})

    R.return_value.run.side_effect = mock_resume_review
    S.return_value.run.return_value = MissionResult(True, MissionType.STEWARD, outputs={"commit_hash":"xyz"}, evidence={"usage":{"total":1}})
    
    result = mission.run(acceptance_context, inputs)
    
    assert result.success is True
    
    # Verify Ledger has Attempt 2
    with open(ledger_path) as f:
        lines = f.readlines()
        assert len(lines) == 3 # Header + 1 + 2
        rec2 = json.loads(lines[2])
        assert rec2["attempt_id"] == 2
        assert rec2["success"] is True

def test_acceptance_oscillation(acceptance_context, mock_subs, mock_preconditions):
    D, B, R, S = mock_subs
    
    D.return_value.run.return_value = MissionResult(True, MissionType.DESIGN, outputs={"build_packet": {"goal":"g"}}, evidence={"usage":{"total":1}})
    
    # Smart Review: Approve Design, Reject Output
    R.return_value.run.side_effect = mock_review_behavior
    
    # A -> B -> A
    # Mock Build outputs
    B.return_value.run.side_effect = [
        MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "diffA"}}}, evidence={"usage":{"total":1}}),
        MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "diffB"}}}, evidence={"usage":{"total":1}}),
        MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "diffA"}}}, evidence={"usage":{"total":1}}),
    ]
    
    mission = AutonomousBuildCycleMission()
    result = mission.run(acceptance_context, {"task_spec": "osc_test"})
    
    assert result.success is False
    assert result.error == TerminalReason.OSCILLATION_DETECTED.value
    
    # Verify Terminal Packet
    term_path = acceptance_context.repo_root / "artifacts/CEO_Terminal_Packet.md"
    assert term_path.exists()
    with open(term_path) as f:
        content = f.read()
        assert "oscillation_detected" in content
        assert "ESCALATION_REQUESTED" in content

def test_verify_terminal_packet_structure(acceptance_context, mock_subs, mock_preconditions):
    # Just force a budget exhaustion to check packet fields
    D, B, R, S = mock_subs
    D.return_value.run.return_value = MissionResult(True, MissionType.DESIGN, outputs={"build_packet": {"goal":"g"}}, evidence={"usage":{"total":1}})
    B.return_value.run.return_value = MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "u"}}}, evidence={"usage":{"total":1}})
    
    # Need to approve design!
    R.return_value.run.side_effect = mock_review_behavior

    # Small budget to fail fast
    with patch("runtime.orchestration.missions.autonomous_build_cycle.BudgetController") as MockBudget:
        MockBudget.return_value.check_budget.return_value = (True, TerminalReason.BUDGET_EXHAUSTED.value)
        
        mission = AutonomousBuildCycleMission()
        mission.run(acceptance_context, {"task_spec": "pkt"})
        
    term_path = acceptance_context.repo_root / "artifacts/CEO_Terminal_Packet.md"
    with open(term_path) as f:
        text = f.read()
        # Verify wrapper
        assert "# Packet: CEO_Terminal_Packet.md" in text
        assert "```json" in text
        # Verify fields
        assert '"outcome": "BLOCKED"' in text
        assert '"reason": "budget_exhausted"' in text
        assert '"tokens_consumed"' in text
        assert '"run_id": "acc_run"' in text

def test_diff_budget_exceeded(acceptance_context, mock_subs, mock_preconditions):
    D, B, R, S = mock_subs
    # Mock approval to get to build
    D.return_value.run.return_value = MissionResult(True, MissionType.DESIGN, outputs={"build_packet": {"goal":"g"}}, evidence={"usage":{"total":1}})
    R.return_value.run.side_effect = mock_review_behavior # Approve Design
    
    # Create massive diff (400 lines) to definitely exceed 300
    massive_diff = "\n".join([f"line {i}" for i in range(400)])
    
    B.return_value.run.return_value = MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": massive_diff}}}, evidence={"usage":{"total":1}})
    
    mission = AutonomousBuildCycleMission()
    result = mission.run(acceptance_context, {"task_spec": "diff_limit"})
    
    assert result.success is False
    assert result.escalation_reason == TerminalReason.DIFF_BUDGET_EXCEEDED.value
    
    # Verify Terminal Packet
    term_path = acceptance_context.repo_root / "artifacts/CEO_Terminal_Packet.md"
    with open(term_path) as f:
        text = f.read()
        assert '"outcome": "ESCALATION_REQUESTED"' in text
        assert '"reason": "diff_budget_exceeded"' in text
        assert '"diff_evidence_path"' in text

    # Verify Evidence Captured
    # We don't know exact attempt id used in filename but check directory
    ev_files = list(acceptance_context.repo_root.glob("artifacts/rejected_diff_attempt_*.txt"))
    assert len(ev_files) > 0

def test_policy_changed_mid_run(acceptance_context, mock_subs, mock_preconditions):
    # PLANT LEGER with different policy hash
    ledger_path = acceptance_context.repo_root / "artifacts" / "loop_state" / "attempt_ledger.jsonl"
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger_path, 'w') as f:
        f.write('{"type": "header", "schema_version": "v1.0", "policy_hash": "OLD_POLICY", "handoff_hash": "x", "run_id": "r"}\n')
        
    mission = AutonomousBuildCycleMission()
    result = mission.run(acceptance_context, {"task_spec": "policy_check"})
    
    assert result.success is False
    assert "policy_changed_mid_run" in result.escalation_reason
    
    # Verify Terminal Packet emitted
    term_path = acceptance_context.repo_root / "artifacts/CEO_Terminal_Packet.md"
    with open(term_path) as f:
        text = f.read()
        assert "ESCALATION_REQUESTED" in text
        assert "policy_changed_mid_run" in text

def test_workspace_reset_unavailable(acceptance_context, mock_subs, mock_preconditions):
    # Mock _can_reset_workspace to return False
    mission = AutonomousBuildCycleMission()
    with patch.object(AutonomousBuildCycleMission, '_can_reset_workspace', return_value=(False, "mocked_unavailable")):
        result = mission.run(acceptance_context, {"task_spec": "reset_check"})

        assert result.success is False
        assert TerminalReason.WORKSPACE_RESET_UNAVAILABLE.value in result.error

        # Verify Terminal Packet
        term_path = acceptance_context.repo_root / "artifacts/CEO_Terminal_Packet.md"
        with open(term_path) as f:
            text = f.read()
            assert "BLOCKED" in text
            assert "workspace_reset_unavailable" in text
