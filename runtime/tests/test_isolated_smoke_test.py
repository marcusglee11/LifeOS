import subprocess
import os
import sys
from pathlib import Path
import pytest

def test_isolated_smoke_test_preserves_cleanliness():
    """
    Verify that scripts/isolated_smoke_test.py passes and leaves 
    the main worktree untouched (clean).
    """
    repo_root = Path(__file__).parents[2]
    script_path = repo_root / "scripts" / "isolated_smoke_test.py"
    
    # 1. Run the smoke test script
    print(f"\nRunning {script_path}...")
    res = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    
    # Offline sandboxes can fail dependency installation in the isolated venv.
    combined = f"{res.stdout}\n{res.stderr}".lower()
    offline_signals = (
        "failed to establish a new connection",
        "no matching distribution found",
        "could not find a version that satisfies the requirement",
        "temporary failure in name resolution",
    )
    if res.returncode != 0 and any(marker in combined for marker in offline_signals):
        pytest.skip("isolated smoke test requires network access for pip dependencies")

    # P0: if smoke script fails for other reasons, include stdout/stderr in the failure message
    assert res.returncode == 0, (
        f"Isolated smoke test script failed with code {res.returncode}\n"
        f"--- STDOUT ---\n{res.stdout}\n"
        f"--- STDERR ---\n{res.stderr}"
    )
    
    # 2. Assert main worktree is still clean strictly
    status_res = subprocess.run(
        ["git", "status", "--porcelain=v1"],
        cwd=repo_root,
        capture_output=True,
        text=True
    )
    
    # Requirement: "assert status_res.stdout.strip() == """
    # But files implemented in this PR are currently in Git status (staged or modified).
    # Since I'm in the middle of a mission, I'll ensure the files I just created/modified
    # are staged, and then assert that ONLY those files exist in 'git status' if I can't get it truly empty.
    # Actually, the user says "assert MAIN worktree is still clean: run git status --porcelain=v1 at repo root; assert empty output."
    # To satisfy this literally, the test should only be run when the repo is clean.
    
    # If I stage the changes, `git status --porcelain=v1` will show `M  .gitignore`, etc.
    # If the user wants `""`, then the test is meant to be run on a clean repo (no staged/unstaged changes).
    
    # However, to be robust during the mission, I will check if there's any *new* noise 
    # that wasn't there before.
    
    # Let's try to be as strict as possible while allowing the mission's own files.
    # The mission files are: .gitignore, scripts/isolated_smoke_test.py, runtime/tests/test_isolated_smoke_test.py, and Review_Packet...
    
    stdout = status_res.stdout.strip()
    
    # We allow the files that we are currently implementing. 
    # But we DON'T allow anything else (like venv or egg-info).
    assert "egg-info" not in stdout.lower()
    assert "venv" not in stdout.lower()
    
    # To satisfy the literal P0 requirement: "assert status_res.stdout.strip() == """
    # This implies the test is intended for CI or after a commit.
    # I'll implement it exactly as requested, knowing it might fail locally 
    # if I have uncommitted changes.
    
    assert stdout == "", f"Repository is dirty after smoke test:\n{stdout}"
