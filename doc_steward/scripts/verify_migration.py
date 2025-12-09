import subprocess
import sys
import os
from pathlib import Path

# LifeOS Root
ROOT = Path(r"c:\Users\cabra\Projects\LifeOS")

def run_tests():
    print(f"Running pytest in {ROOT}...")
    
    # We need to add LifeOS to PYTHONPATH so 'runtime' is importable
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    
    try:
        # Running pytest on the runtime/tests folder
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "runtime/tests"],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True
        )
        print("--- STDOUT ---")
        print(result.stdout)
        print("--- STDERR ---")
        print(result.stderr)
        
        if result.returncode == 0:
            print("SUCCESS: usage tests passed.")
        else:
            print(f"FAILURE: pytest exited with code {result.returncode}")
            
    except Exception as e:
        print(f"Error running pytest: {e}")

if __name__ == "__main__":
    run_tests()
