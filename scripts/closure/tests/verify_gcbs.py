
import os
import sys
import json
import zipfile
import shutil
import subprocess
import hashlib

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..")) 
# Assuming scripts/closure/tests/verify_gcbs.py -> ../../../
# Adjusted: scripts/closure/tests -> ../../../ is root
# Actually, let's use current working dir if in root

BUILDER_SCRIPT = os.path.join(REPO_ROOT, "scripts", "closure", "build_closure_bundle.py")
VALIDATOR_SCRIPT = os.path.join(REPO_ROOT, "scripts", "closure", "validate_closure_bundle.py")

WORK_DIR = os.path.join(REPO_ROOT, "temp_verification")
os.makedirs(WORK_DIR, exist_ok=True)

def create_dummy_evidence():
    # Create simple evidence
    p = os.path.join(WORK_DIR, "evidence.txt")
    with open(p, "w") as f:
        f.write("Sample evidence content. No truncation.")
    return p

def create_bad_evidence():
    p = os.path.join(WORK_DIR, "bad_log.txt")
    with open(p, "w") as f:
        f.write("Log content with [PENDING] token.")
    return p

def run_builder(output_path, evidence_list):
    include_file = os.path.join(WORK_DIR, "include.txt")
    with open(include_file, "w") as f:
        for p in evidence_list:
            f.write(p + "\n")
            
    cmd = [sys.executable, BUILDER_SCRIPT, 
           "--profile", "step_gate_closure", 
           "--closure-id", "TEST_BUNDLE",
           "--include", include_file,
           "--output", output_path]
           
    return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)

def run_validator(bundle_path):
    cmd = [sys.executable, VALIDATOR_SCRIPT, bundle_path, "--output", os.path.join(WORK_DIR, "audit.md")]
    return subprocess.run(cmd, capture_output=True, text=True)

def test_good_bundle():
    print("\n--- Testing Good Bundle ---")
    ev = create_dummy_evidence()
    bundle_path = os.path.join(WORK_DIR, "good.zip")
    
    # 1. Build
    build_res = run_builder(bundle_path, [ev])
    if build_res.returncode != 0:
        print("FAIL: Builder failed")
        print("STDOUT:", build_res.stdout)
        print("STDERR:", build_res.stderr)
        return False
        
    # 2. Validate
    val_res = run_validator(bundle_path)
    if val_res.returncode != 0:
        print("FAIL: Good bundle failed validation")
        print(val_res.stdout)
        return False
        
    print("PASS: Good bundle built and validated.")
    return True

def test_bad_bundle():
    print("\n--- Testing Bad Bundle ---")
    # Manually create a bad zip to test specific failures
    bundle_path = os.path.join(WORK_DIR, "bad.zip")
    
    manifest = {
        "schema_version": "WRONG_VERSION", # FAIL
        "closure_id": "BAD",
        "evidence": [
            {"path": "missing.txt", "sha256": "0"*64, "role": "other"} # FAIL: Missing
        ]
        # Missing required fields too
    }
    
    with zipfile.ZipFile(bundle_path, "w") as zf:
        zf.writestr("closure_manifest.json", json.dumps(manifest))
        zf.writestr("closure_addendum.md", "Dummy")
        zf.writestr("truncation.txt", "Has ... token") # We need to list in manifest to scan?
        # If not in manifest, it's ignored for tokens usually (by validator logic)
        
    val_res = run_validator(bundle_path)
    if val_res.returncode == 0:
        print("FAIL: Bad bundle passed validation!")
        return False
        
    report = val_res.stdout
    # Check for expected codes
    expected_codes = ["MANIFEST_VERSION_MISMATCH", "MANIFEST_FIELD_MISSING", "EVIDENCE_MISSING"]
    # Actually checking stdout for json or checking output file?
    # Validator prints findings to stdout too in table? No, writes to file.
    # Validator prints "Audit Status: FAIL" to stdout.
    
    # Let's read the report file
    with open(os.path.join(WORK_DIR, "audit.md"), "r") as f:
        report_content = f.read()
        
    missing = []
    for code in expected_codes:
        if code not in report_content:
            missing.append(code)
            
    if missing:
        print(f"FAIL: Validator didn't catch {missing}")
        print("Report Content:\n", report_content)
        return False
        
    print("PASS: Bad bundle failed with expected codes.")
    return True

def main():
    try:
        if not test_good_bundle():
            sys.exit(1)
        if not test_bad_bundle():
            sys.exit(1)
        print("\nALL VERIFICATION PASSED")
        # Cleanup
        # shutil.rmtree(WORK_DIR) 
    except Exception as e:
        print(f"Verification crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
