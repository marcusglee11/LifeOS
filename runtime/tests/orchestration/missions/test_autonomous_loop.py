import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
from runtime.orchestration.missions.autonomous_build_cycle import AutonomousBuildCycleMission
from runtime.orchestration.missions.base import MissionContext, MissionResult, MissionType
from runtime.orchestration.loop.taxonomy import TerminalOutcome, TerminalReason

@pytest.fixture
def mock_context(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "artifacts" / "loop_state").mkdir(parents=True)
    (repo_root / "artifacts" / "evidence").mkdir(parents=True)
    
    # Create Policy Config
    policy_dir = repo_root / "config" / "policy"
    policy_dir.mkdir(parents=True)
    
    # Valid master config
    (policy_dir / "policy_rules.yaml").write_text(
        "schema_version: 'v1.0'\n"
        "tool_rules: []\n"
        "failure_routing:\n"
        "  review_rejection:\n"
        "    default_action: RETRY\n"
        "budgets:\n"
        "  retry_limits:\n"
        "    review_rejection: 10\n",
        encoding="utf-8"
    )
    
    # Dummy schema (allow anything)
    (policy_dir / "policy_schema.json").write_text("{}", encoding="utf-8")
    
    return MissionContext(
        repo_root=repo_root,
        baseline_commit="abc",
        run_id="test_run",
        operation_executor=None
    )

@pytest.fixture
def mock_sub_missions():
    with patch("runtime.orchestration.missions.autonomous_build_cycle.DesignMission") as MockDesign, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.BuildMission") as MockBuild, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.ReviewMission") as MockReview, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.StewardMission") as MockSteward:
        
        # Setup Success Defaults
        d_inst = MockDesign.return_value
        d_inst.run.return_value = MissionResult(True, MissionType.DESIGN, outputs={"build_packet": {}}, evidence={"usage": {"input_tokens": 10, "output_tokens": 10}})
        
        b_inst = MockBuild.return_value
        b_inst.run.return_value = MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "diff"}}}, evidence={"usage": {"input_tokens": 10, "output_tokens": 10}})
        
        r_inst = MockReview.return_value
        # Design Review -> Approved
        # Output Review -> Approved (Default)
        r_inst.run.return_value = MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved", "council_decision": {}}, evidence={"usage": {"input_tokens": 10, "output_tokens": 10}})
        
        s_inst = MockSteward.return_value
        s_inst.run.return_value = MissionResult(True, MissionType.STEWARD, outputs={"commit_hash": "hash"}, evidence={"usage": {}})
        
        yield MockDesign, MockBuild, MockReview, MockSteward

def test_loop_happy_path(mock_context, mock_sub_missions):
    mission = AutonomousBuildCycleMission()
    inputs = {"task_spec": "do validation"}
    
    result = mission.run(mock_context, inputs)
    
    # Needs to handle the fact that my logic loops? 
    # If Policy says Pass, it should exit.
    # In my logic, if Steward passes, 'check policy next iter' -> PASS.
    # So it runs one more policy check -> TERMINATE(PASS).
    
    # Assert
    assert result.success is True
    assert (mock_context.repo_root / "artifacts/CEO_Terminal_Packet.md").exists()

def test_token_accounting_fail_closed(mock_context, mock_sub_missions):
    _, MockBuild, _, _ = mock_sub_missions
    
    # Build returns NO usage
    b_inst = MockBuild.return_value
    b_inst.run.return_value = MissionResult(True, MissionType.BUILD, outputs={"review_packet": {}}, evidence={}) # Missing usage
    
    mission = AutonomousBuildCycleMission()
    inputs = {"task_spec": "do validation"}
    
    result = mission.run(mock_context, inputs)
    
    assert result.success is False
    assert result.escalation_reason == TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value

def test_budget_exhausted(mock_context, mock_sub_missions):
    _, _, MockReview, _ = mock_sub_missions
    # Make Review reject everything -> Loop -> Exhaust Budget
    r_inst = MockReview.return_value
    # First call is Design Review (Approved), subsequent are Output Review (Rejected)
    
    # We need side_effect to distinguish calls?
    # Or just make all reviews reject?
    # If Design Review rejects, we exit 'Design rejected'.
    # We want Design Approved, Loop Rejected.
      
    def review_side_effect(ctx, inp):
        if inp["review_type"] == "build_review":
            return MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved"}, evidence={"usage":{"total":1}})
        else:
            return MissionResult(True, MissionType.REVIEW, outputs={"verdict": "rejected"}, evidence={"usage":{"total":1}})
            
    r_inst.run.side_effect = review_side_effect
    
    # Mock Build to return unique content each time to avoid Deadlock
    b_inst = mock_sub_missions[1].return_value
    b_inst.run.side_effect = [
        MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": f"diff_{i}"}}}, evidence={"usage": {"total": 1}})
        for i in range(10)
    ]
    
    mission = AutonomousBuildCycleMission()
    inputs = {"task_spec": "loop forever"}
    result = mission.run(mock_context, inputs)
    
    assert result.success is False
    assert result.error == TerminalReason.BUDGET_EXHAUSTED.value

def test_resume_policy_check(mock_context, mock_sub_missions):
    # PLANT A LEDGER WITH DIFFERENT POLICY HASH
    ledger_path = mock_context.repo_root / "artifacts/loop_state/attempt_ledger.jsonl"
    with open(ledger_path, "w") as f:
        f.write('{"type": "header", "policy_hash": "BOGUS", "handoff_hash": "X", "run_id": "r"}\n')
        # Full valid record
        rec = {
            "attempt_id": 1, "timestamp": "t", "run_id": "r", "policy_hash": "p", 
            "input_hash": "i", "actions_taken": [], "diff_hash": "d", "changed_files": [], 
            "evidence_hashes": {}, "success": False, "failure_class": "unknown", 
            "terminal_reason": None, "next_action": "retry", "rationale": "r"
        }
        import json
        f.write(json.dumps(rec) + "\n")
        
    mission = AutonomousBuildCycleMission()
    inputs = {"task_spec": "resume"}
    
    result = mission.run(mock_context, inputs)
    
    assert result.success is False
    assert TerminalReason.POLICY_CHANGED_MID_RUN.value in result.escalation_reason
