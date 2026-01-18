from runtime.orchestration.registry import run_mission
from runtime.orchestration.engine import ExecutionContext
import os

# Set dummy key if not present (BuildMission will try to use it)
if "OPENROUTER_API_KEY" not in os.environ:
    os.environ["OPENROUTER_API_KEY"] = "sk-dummy-key-for-verification"

print("--- Triggering BuildMission via Registry ---")
try:
    # 1. Trigger mission
    # We use 'build' mission which should invoke 'builder' agent
    result = run_mission(
        'build', 
        ExecutionContext({}, {}),
        params={
            "build_packet": {"goal": "PROVE_THE_CHAIN"},
            "approval": {"verdict": "approved"}
        }
    )
    
    # 2. Verify Result
    print(f"\nStatus: {getattr(result, 'status', 'unknown')}")
    print(f"Success: {getattr(result, 'success', False)}")
    
    evidence = getattr(result, 'evidence', {}) or {}
    print(f"Evidence Keys: {list(evidence.keys())}")
    
    # 3. Verify Agent Call logic
    # BuildMission puts 'call_id' in evidence per source code
    if getattr(result, 'success', False):
        if 'call_id' in evidence:
             print("SUCCESS: Chain is ALIVE. 'call_id' found in evidence.")
        else:
             print("PARTIAL SUCCESS: Mission ran but 'call_id' missing from evidence.")
    else:
        print(f"FAILED: {getattr(result, 'error_message', 'No error message')}")
        # Print full output if available
        if hasattr(result, 'to_dict'):
            print(result.to_dict())

except Exception as e:
    print(f"CRASH: {e}")
    import traceback
    traceback.print_exc()
