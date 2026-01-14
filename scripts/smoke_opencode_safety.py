
import sys
import os
from pathlib import Path
import tempfile
import shutil
import logging

# Add repo root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runtime.safety.path_guard import PathGuard, SafetyError

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger("safety_smoke")

def smoke_test():
    print("=== OPENCODE SAFETY SMOKE TEST ===")
    
    # 1. Setup
    tmp_root = Path(tempfile.mkdtemp(prefix="smoke_safety_"))
    try:
        repo_root = tmp_root / "fake_repo"
        repo_root.mkdir()
        
        sandbox = tmp_root / "sandbox"
        PathGuard.create_sandbox(sandbox)
        
        # 2. Test Blocked Case (Unsafe Target)
        unsafe_target = repo_root
        print(f"\n[CASE 1] Attempting to destroy FAKE REPO ROOT: {unsafe_target}")
        try:
            PathGuard.verify_safe_for_destruction(unsafe_target, sandbox_root=sandbox, repo_root=repo_root)
            print("RESULT: ALLOWED (UNEXPECTED!)")
        except SafetyError as e:
            print(f"RESULT: BLOCKED (EXPECTED) - Reason: {e}")

        # 3. Test Blocked Case (Unmarked Dir)
        unmarked = tmp_root / "unmarked_dir"
        unmarked.mkdir()
        print(f"\n[CASE 2] Attempting to destroy UNMARKED DIR: {unmarked}")
        try:
            PathGuard.verify_safe_for_destruction(unmarked, sandbox_root=unmarked)
            print("RESULT: ALLOWED (UNEXPECTED!)")
        except SafetyError as e:
            print(f"RESULT: BLOCKED (EXPECTED) - Reason: {e}")
            
        # 4. Test Allowed Case (Valid Sandbox)
        print(f"\n[CASE 3] Attempting to destroy VALID SANDBOX: {sandbox}")
        try:
            PathGuard.verify_safe_for_destruction(sandbox, sandbox_root=sandbox)
            print("RESULT: ALLOWED (EXPECTED)")
            # Actually destroy it to prove it works
            shutil.rmtree(sandbox)
            print("Action: Destroyed successfully")
        except SafetyError as e:
            print(f"RESULT: BLOCKED (UNEXPECTED!) - Reason: {e}")

    finally:
        if tmp_root.exists():
            shutil.rmtree(tmp_root)
    print("\n=== SMOKE TEST COMPLETE ===")

if __name__ == "__main__":
    smoke_test()
