import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
import pytest

# Path to the repo root
REPO_ROOT = Path(__file__).parent.parent

def compute_dir_hash(directory):
    """Compute a dictionary of {relative_path: sha256} for all files in directory."""
    hashes = {}
    for root, _, files in os.walk(directory):
        for file in files:
            path = Path(root) / file
            rel_path = path.relative_to(directory).as_posix()
            with open(path, "rb") as f:
                hashes[rel_path] = hashlib.sha256(f.read()).hexdigest()
    return hashes

def run_demo(input_str="yes"):
    """Run the approval demo via subprocess."""
    cmd = [sys.executable, "-m", "coo.cli", "run-approval-demo"]
    # We pipe "yes" to stdin for approval
    # The demo also takes an initial input, but currently it's hardcoded in the code 
    # or just printed. The code says: user_request = "Generate..."
    # So we only need to provide the approval answer.
    
    # However, if we change the code to accept input, we'd need to provide it.
    # Current code: user_request = "Generate..." (Hardcoded).
    # So just "yes" is enough.
    
    result = subprocess.run(
        cmd,
        input=input_str.encode("utf-8"),
        cwd=str(REPO_ROOT),
        capture_output=True,
        check=True
    )
    return result

def test_demo_approval_determinism():
    """
    F3: Deterministic Test (Automated)
    Run DEMO_APPROVAL_V1 twice with same input/approval.
    Assert identical artifacts.
    """
    demo_dir = REPO_ROOT / "demo" / "DEMO_APPROVAL_V1"
    
    # Clean up before start
    if demo_dir.exists():
        shutil.rmtree(demo_dir)
        
    print("Run 1...")
    run_demo("yes")
    hashes_1 = compute_dir_hash(demo_dir)
    
    print("Run 2 (Replay)...")
    run_demo("yes")
    hashes_2 = compute_dir_hash(demo_dir)
    
    # Assert identical file set
    assert hashes_1.keys() == hashes_2.keys(), "File sets differ between runs"
    
    # Assert identical hashes
    for path, h1 in hashes_1.items():
        h2 = hashes_2[path]
        assert h1 == h2, f"Hash mismatch for {path}: {h1} != {h2}"
        
    print("Determinism Verified: Identical artifacts across runs.")

if __name__ == "__main__":
    test_demo_approval_determinism()
