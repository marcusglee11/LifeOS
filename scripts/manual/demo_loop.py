
import sys
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from runtime.orchestration.missions.autonomous_build_cycle import AutonomousBuildCycleMission
from runtime.orchestration.missions.base import MissionContext, MissionResult, MissionType

def setup_demo_env():
    root = Path("./demo_env")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()
    (root / "artifacts" / "loop_state").mkdir(parents=True)
    return MissionContext(repo_root=root, baseline_commit="demo", run_id="demo_run", operation_executor=None)

def mock_review_behavior(ctx, inputs):
    print(f"[DEMO] Review running... Type: {inputs.get('review_type')}")
    if inputs.get("review_type") == "build_review":
        return MissionResult(True, MissionType.REVIEW, outputs={"verdict": "approved", "council_decision": {}}, evidence={"usage":{"total":1}})
    return MissionResult(True, MissionType.REVIEW, outputs={"verdict": "rejected", "council_decision": {"synthesis": "rejected"}}, evidence={"usage":{"total":1}})

def run_demo():
    print("=== STARTING PHASE A LOOP CONTROLLER DEMO ===")
    ctx = setup_demo_env()
    
    with patch("runtime.orchestration.missions.autonomous_build_cycle.DesignMission") as D, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.BuildMission") as B, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.ReviewMission") as R, \
         patch("runtime.orchestration.missions.autonomous_build_cycle.StewardMission") as S:
         
        D.return_value.run.return_value = MissionResult(True, MissionType.DESIGN, outputs={"build_packet": {"goal":"demo"}}, evidence={"usage":{"total":1}})
        
        # Configure mocks to run 3 attempts then Oscillation
        # Attempt 1: Diff A
        # Attempt 2: Diff B
        # Attempt 3: Diff A (Oscillation)
        
        B.return_value.run.side_effect = [
            MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "diffA"}}}, executed_steps=["build"], evidence={"usage":{"total":1}}),
            MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "diffB"}}}, executed_steps=["build"], evidence={"usage":{"total":1}}),
            MissionResult(True, MissionType.BUILD, outputs={"review_packet": {"payload": {"content": "diffA"}}}, executed_steps=["build"], evidence={"usage":{"total":1}}),
        ]
        
        R.return_value.run.side_effect = mock_review_behavior
        
        mission = AutonomousBuildCycleMission()
        print("[DEMO] Invoking Mission: AutonomousBuildCycle")
        result = mission.run(ctx, {"task_spec": "demo execution"})
        
        print(f"[DEMO] Mission Result: Success={result.success}")
        print(f"[DEMO] Failure Reason: {result.error}")
        
    # Verify Artifacts
    print("\n=== VERIFYING ARTIFACTS ===")
    root = ctx.repo_root
    ledger = root / "artifacts/loop_state/attempt_ledger.jsonl"
    if ledger.exists():
        print(f"[CHECK] Ledger exists at {ledger}")
        with open(ledger) as f:
            lines = f.readlines()
            print(f"[CHECK] Ledger contains {len(lines)} lines (Header + 3 Attempts)")
            for line in lines:
                print(f"  > {line.strip()}")
    else:
        print("[FAIL] Ledger missing!")

    term = root / "artifacts/CEO_Terminal_Packet.md"
    if term.exists():
        print(f"[CHECK] Terminal Packet exists at {term}")
        with open(term) as f:
            print(f.read())
    else:
        print("[FAIL] Terminal Packet missing!")
        
    print("=== DEMO COMPLETE ===")

if __name__ == "__main__":
    run_demo()
