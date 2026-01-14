import subprocess
import json
import sys
import os

print("--- Triggering EchoMission via CLI (Offline) ---")

# Construct command: lifeos mission run echo --params '{"message": "FRANKENSTEIN_IS_ALIVE"}' --json
# We use the 'lifeos' entrypoint as verified in the review packet.
cmd = [
    "lifeos", "mission", "run", "echo",
    "--param", "message=FRANKENSTEIN_IS_ALIVE",
    "--json"
]

print(f"Executing: {' '.join(cmd)}")
try:
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=os.getcwd() # Run from repo root
    )

    print(f"Exit Code: {result.returncode}")
    print(f"Stdout: {result.stdout}")
    print(f"Stderr: {result.stderr}")

    if result.returncode != 0:
        print("FAILED: Non-zero exit code")
        sys.exit(1)

    # 3. Verify Deterministic Output in JSON
    try:
        data = json.loads(result.stdout)
        # For Phase 3 Dispatched missions, the result is stored in final_state["mission_result"]
        # The EchoMission returns 'outputs' dict.
        mission_res = data.get("final_state", {}).get("mission_result", {})
        output_msg = mission_res.get("outputs", {}).get("message")
        
        if output_msg == "FRANKENSTEIN_IS_ALIVE":
             print("SUCCESS: Chain is ALIVE (Offline Confirmed via CLI).")
        else:
             print(f"FAILED: Output mismatch. Got: {output_msg}")
             print(f"Debug: mission_result keys: {list(mission_res.keys())}")
    except json.JSONDecodeError:
         print("FAILED: Could not decode JSON output")
         sys.exit(1)

except Exception as e:
    print(f"CRASH: {e}")
    sys.exit(1)
