
import pytest
import json
import subprocess
from unittest.mock import MagicMock, patch
from runtime.orchestration.missions.autonomous_build_cycle import AutonomousBuildCycleMission
from runtime.orchestration.missions.base import MissionContext, MissionResult, MissionType
from runtime.orchestration.loop.taxonomy import TerminalReason, FailureClass

@pytest.fixture
def dogfood_context(tmp_path):
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "artifacts" / "loop_state").mkdir(parents=True)
    return MissionContext(repo_root=repo_root, baseline_commit="demo", run_id="dogfood_1", operation_executor=None)

def test_autonomous_build_cycle_imports():
    """Regression Guard: Verify AutonomousBuildCycleMission modules import correctly."""
    # This test fails if PolicyLoader or other dependencies are missing from runtime.api.governance_api
    from runtime.orchestration.missions.autonomous_build_cycle import AutonomousBuildCycleMission
    assert AutonomousBuildCycleMission is not None

def test_plan_bypass_activation(dogfood_context):
    """
    Controlled Dogfood Run:
    Exercises AutonomousBuildCycleMission logic to trigger Plan Bypass.
    1. Policy configured to allow bypass for REVIEW_REJECTION.
    2. Attempt 1: Review Rejects (triggering retry analysis).
    3. Controller evaluates bypass -> Eligible -> Applied.
    4. Attempt 2: Succeeds.
    """
    
    # 1. Mock Infrastructure/Preconditions
    with patch("runtime.orchestration.missions.autonomous_build_cycle.verify_repo_clean") as mock_clean, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.verify_governance_baseline") as mock_baseline, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.PolicyLoader") as mock_loader, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.run_git_command") as mock_git, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.FileLock") as MockLock:
         
        mock_clean.return_value = None
        mock_baseline.return_value = MagicMock()
        
        # Policy: Allow REVIEW_REJECTION bypass
        mock_loader_instance = MagicMock()
        mock_loader_instance.load.return_value = {
            "schema_version": "1.2",
            "posture": {"mode": "PRIMARY"},
            "budgets": {"retry_limits": {"REVIEW_REJECTION": 2}},
            "failure_routing": {
                "REVIEW_REJECTION": {
                    "default_action": "RETRY",
                    "plan_bypass_eligible": True,
                    "scope_limit": {"max_lines": 50, "max_files": 3},
                    "mode": "patchful"
                }
            }
        }
        mock_loader.return_value = mock_loader_instance
        
        # Mock Git for Diffstat (Crucial for Eligibility)
        # Sequence: 
        # 1. diff HEAD (create patch)
        # 2. diff --numstat HEAD (verify scope)
        # 3. diff --summary HEAD (check dangerous modes)
        # 4. reset (revert)
        # 5. apply (if eligible)
        
        def git_side_effect(args, cwd=None):
            cmd = args if isinstance(args, list) else args.split()
            if "diff" in cmd and "--numstat" in cmd:
                return b"1\t1\tsrc/file.py\n" # 2 lines changed
            if "diff" in cmd and "--summary" in cmd:
                return b"" # No suspicious modes
            if "diff" in cmd: # Patch creation
                return b"diff content"
            return b""
            
        mock_git.side_effect = git_side_effect
        
        # Mock Lock
        MockLock.return_value.acquire_ctx.return_value.__enter__.return_value = True

        # 2. Mock Sub-Missions
        with patch("runtime.orchestration.missions.autonomous_build_cycle.DesignMission") as D, \
             patch("runtime.orchestration.missions.autonomous_build_cycle.BuildMission") as B, \
             patch("runtime.orchestration.missions.autonomous_build_cycle.ReviewMission") as R, \
             patch("runtime.orchestration.missions.autonomous_build_cycle.StewardMission") as S:
             
            # Design: OK
            D.return_value.run.return_value = MissionResult(True, MissionType.DESIGN, outputs={"build_packet": {"goal":"g"}}, evidence={"usage":{"total":1}})
            
            # Build: Attempt 1 and Attempt 2 must have different content to avoid "NO_PROGRESS" deadlock check
            B.return_value.run.side_effect = [
                MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "diff_attempt_1"}}}, evidence={"usage":{"total":1}}),
                MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "diff_attempt_2"}}}, evidence={"usage":{"total":1}})
            ]
            
            # Review: Reject first, Approve second
            def review_behavior(ctx, inputs):
                rtype = inputs.get("review_type")
                if rtype == "build_review":
                    return MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved", "council_decision": {}}, evidence={"usage":{"total":1}})
                # Output Review
                # We need state to know iteration. 
                # But mock_git is stateless in our simple mock.
                # Let's use side_effect on R.run
                return MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved"}, evidence={"usage":{"total":1}})

            # Attempt 1: Review Reject
            # Attempt 2: Review Approve
            # order: Design(1), Output(Attempt1), Output(Attempt2)
            
            results = [
                MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved"}, evidence={"usage":{"total":1}}), # Design Review
                MissionResult(True, MissionType.REVIEW, outputs={"verdict": "rejected", "council_decision": {"synthesis": "bad code"}}, evidence={"usage":{"total":1}}), # Attempt 1 Output
                MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved", "council_decision": {"synthesis": "good code"}}, evidence={"usage":{"total":1}}), # Attempt 2 Output
            ]
            R.return_value.run.side_effect = results
            
            # Steward (for final success)
            S.return_value.run.return_value = MissionResult(True, MissionType.STEWARD, outputs={"commit_hash":"final_hash"}, evidence={"usage":{"total":1}})
            
            # 3. Run Mission
            mission = AutonomousBuildCycleMission()
            result = mission.run(dogfood_context, {"task_spec": "dogfood_bypass"})
            
            assert result.success is True
            
            # 4. Verify Ledger for Bypass Evidence
            ledger_path = dogfood_context.repo_root / "artifacts/loop_state/attempt_ledger.jsonl"
            with open(ledger_path) as f:
                lines = f.readlines()
                # Header, Attempt 1 (Fail), Attempt 2 (Success)
                assert len(lines) == 3
                
                attempt1 = json.loads(lines[1])
                assert attempt1["success"] is False
                assert attempt1["failure_class"] == "REVIEW_REJECTION"
                
                attempt2 = json.loads(lines[2])
                assert attempt2["success"] is True
                # Assert Bypass Info in Attempt 2!
                bypass = attempt2["plan_bypass_info"]
                assert bypass["evaluated"] is True
                assert bypass["eligible"] is True
                assert bypass["applied"] is True
