
import pytest
import json
import hashlib
import sys
import os
import shutil
from pathlib import Path
from scripts.e2e import run_mission_cli_e2e

def test_mission_cli_e2e_harness(tmp_path):
    """
    CI wrapper for the E2E Mission CLI Harness.
    Verifies that the harness:
    1. Runs without blocking (fail-closed entrypoint resolution works).
    2. Produces audit-grade evidence (hashes, summary).
    3. Validates correctness of E2E-1/2/3 using proven conventions.
    """
    
    # 1. Setup Arguments
    original_argv = sys.argv
    out_dir = tmp_path / "artifacts" / "evidence" / "mission_cli_e2e"
    
    # We call the script logic directly via main()
    # It must detect its own repo root (via walking up from __file__)
    # It must resolve entrypoint (lifeos or python -m)
    
    sys.argv = ["scripts/e2e/run_mission_cli_e2e.py", "--out-dir", str(out_dir)]
    
    # 2. Execution
    try:
        run_mission_cli_e2e.main()
    except SystemExit as e:
        # P0.6: If the harness exits non-zero, it must be because it's FAIL or BLOCKED.
        # We catch it so we can provide a better error message after inspecting the out_dir.
        pass
    finally:
        sys.argv = original_argv

    # 3. Validation
    
    # Check if BLOCKED.md exists (Critical Failure)
    # We don't know the ID yet, but we can look for any directory or BLOCKED.md
    blocked_files = list(out_dir.glob("**/BLOCKED.md"))
    if blocked_files:
        with open(blocked_files[0], 'r') as f:
            reason = f.read()
        pytest.fail(f"Harness BLOCKED in CI Environment: {reason}")
    
    latest_ptr = out_dir / "latest.json"
    assert latest_ptr.exists(), "latest.json pointer must exist"
    
    with open(latest_ptr) as f:
        latest = json.load(f)
        
    run_id = latest["run_id"]
    summary_path = out_dir / run_id / "summary.json"
    assert summary_path.exists(), "summary.json must exist"
    
    with open(summary_path) as f:
        summary = json.load(f)
        
    # Check Schema & P0 Requirements
    assert summary["schema_version"] == "e2e_mission_cli_summary_v1"
    
    # Check Entrypoint Resolution (CI-Safe)
    mode = summary.get("selected_entrypoint_mode")
    
    # P0.2: Strict Entrypoint Blessing Gate
    if shutil.which("lifeos"):
        # If lifeos is in PATH, it MUST be selected
        assert mode == "lifeos"
    else:
        # If lifeos is NOT in PATH, we check if we expected python-m or BLOCKED
        # How do we know if python-m usage was proven?
        # We can check the search log or the summary which reflects the choice.
        # But per P0.2 requirements: "Update assertions: ... expect overall_outcome == BLOCKED" if not proven.
        
        # We need to know if the repo actually HAD the proof.
        # In this specific test environment (temp_repo not used here, actual repo used), 
        # we expect the repo to have the proof (since we are testing LifeOS repo itself).
        # So we expect python-m if we are on a system without lifeos in PATH but WITH the repo artifact.
        
        # HOWEVER, if the harness failed to find proof, it would have exited non-zero (BLOCKED).
        # And we caught that exit.
        # So if we are here (summary exists), either it passed entrypoint gate or passed as BLOCKED?
        # Wait, if harness exits non-zero, we catch it. But we proceed to validation.
        # If BLOCKED, summary might differ or not exist?
        # The harness writes BLOCKED.md and exits. It does NOT write summary.json in write_blocked.
        # So if we are here and summary.json exists, it means it DID NOT BLOCK.
        
        # So if lifeos is missing, and we are here, mode MUST be python-m.
        assert mode == "python-m", "Harness fell back to python-m without blocking"
        
        # Verify it was justified (proven)
        # We can check evidence or search log, but simply asserting mode is python-m implies it found proof.
    
    # Check Outcome
    if summary["overall_outcome"] != "PASS":
        # P0.6: Accept SKIPPED in some cases if allowed by contract
        # But for CI sanity, we usually want E2E-1 to at least pass.
        pytest.fail(f"E2E Harness Failed: {json.dumps(summary, indent=2)}")

    # Check Cases
    cases = {c["name"]: c for c in summary["cases"]}
    
    # E2E-1 Smoke
    assert "E2E-1" in cases
    assert cases["E2E-1"]["status"] == "PASS", "E2E-1 Smoke Test Failed"
    assert cases["E2E-1"]["wrapper_validation"]["ok"] is True, "E2E-1 Wrapper Validation Failed"

    # E2E-2 Determinism
    if "E2E-2" in cases:
        # If SKIPPED, must have reason. If PASS, implies exact match.
        if cases["E2E-2"]["status"] == "SKIPPED":
            assert cases["E2E-2"]["reason"], "Skipped determinism requires reason"
        elif cases["E2E-2"]["status"] == "FAIL":
            pytest.fail("E2E-2 Determinism Breach (Detailed logs in output)")
    
    # E2E-3 Negative
    if "E2E-3" in cases:
        # Allow either PASS (if negative proof exists) or SKIPPED (if not)
        if cases["E2E-3"]["status"] == "PASS":
            assert cases["E2E-3"]["observed"]["exit_code"] == 1
        elif cases["E2E-3"]["status"] != "SKIPPED":
            pytest.fail(f"E2E-3 unexpected status: {cases['E2E-3']}")
         
    # Check Evidence Hashing
    evidence_map = {e["path"]: e for e in summary.get("evidence_files", [])}
    run_dir = out_dir / run_id
    
    # Verify at least one set of stdout/stderr exists and is hashed
    assert any(k.endswith(".stdout.txt") for k in evidence_map.keys())
    assert "search_log.txt" in evidence_map
    
    for fname, meta in evidence_map.items():
        disk_path = run_dir / fname
        assert disk_path.exists()
        with open(disk_path, 'rb') as f:
            disk_bytes = f.read()
            sha = hashlib.sha256(disk_bytes).hexdigest()
            assert sha == meta["sha256"], f"Hash mismatch for {fname}"
