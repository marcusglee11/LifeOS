import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(r"c:\Users\cabra\Projects\LifeOS")

# Tests that might not depend on ProjectBuilder
TARGETS = [
    "runtime/tests/test_fsm_checkpoint_regression.py",
    "runtime/tests/test_determinism.py",
    "runtime/tests/test_crypto_determinism.py"
]

def run_tests():
    print(f"Running selective pytest in {ROOT}...")
    
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    
    for test in TARGETS:
        print(f"--- Running {test} ---")
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pytest", test],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"PASS: {test}")
            else:
                print(f"FAIL: {test}")
                print(result.stderr[:1000]) # First 1000 chars of error
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    run_tests()
