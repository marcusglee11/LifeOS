# Review Packet: A1/A2 Re-closure v2.1a (Strict Compliance)

**Mission**: Re-close A1 (Agent API) and A2 (Ops) using strictly hardened G-CBS v1.1 rules.
**Version**: v2.1a (Packet Update)
**Date**: 2026-01-11
**Author**: Antigravity
**Status**: REVIEW_REQUIRED

## 1. Summary

Produced **Closure Bundle v2.1** with strict adherence to "repayment hardening" requirements:

- **Verbatim Evidence**: No stdout filtering; raw capture processed by fail-closed scanners.
- **Smart Truncation Checks**: Allowed benign `collecting ...` but disallowed dangerous nodeid/hash truncation.
- **Fail-Closed Inventories**: Build fails if inputs or environment info are missing.

## 2. Deliverables

| Artifact | Location | Status |
|----------|----------|--------|
| **Closure Bundle** | `artifacts/bundles/Bundle_A1_A2_Closure_v2.1.zip` | READY |
| **Audit Report** | `artifacts/reclosure_work/final_audit_report_v2.1.md` | **PASS** |
| **Test Report** | `artifacts/reclosure_work/TEST_REPORT_A1_A2_RECLOSURE_v2.1_PASS.md` | READY |

## 3. Bundle Digest

The following is the verbatim content of `artifacts/bundles/Bundle_A1_A2_Closure_v2.1.zip.sha256`:
`E81931C47D039AF16BAC7310BD90BC64B088646F920B64F19943BA94CE388DED  Bundle_A1_A2_Closure_v2.1.zip`

> [!IMPORTANT]
> No hashes are truncated anywhere in this packet.

## 4. Evidence Capture Semantics

To ensure auditability and verbatim integrity:
- **Combined Streams**: stdout and stderr are captured together into a single text file (e.g., `pytest_a1.txt`) via `subprocess.run(..., stderr=subprocess.STDOUT)`.
- **Exact Paths**: Evidence is captured to:
  - `artifacts/reclosure_work/evidence/pytest_a1.txt`
  - `artifacts/reclosure_work/evidence/pytest_a2.txt`
  - `artifacts/reclosure_work/evidence/env_info.txt`
- **Post-Process Scanning**: Scanning for forbidden tokens/truncation is performed **AFTER** capture. The scanning process reads the file but does **NOT** modify, delete, or mutate any content.
- **Allow-List**: The allow-list (e.g., for `collecting ...`) is **allow-only**. It permits the build to proceed if the pattern matches but does **not** remove the line from the evidence.

## 5. Script Hardening Logic (Diff Summary)

### `scripts/generate_a1a2_evidence.py`

- **REMOVED**: `subprocess.output` line filtering (reverted to verbatim capture).
- **ADDED**: `scan_evidence()` now uses regex-based truncation signatures:
  - `::.*\.\.\.` (NodeID truncation -> FAIL)
  - `[0-9a-f]{6}\.\.\.` (Hash truncation -> FAIL)
  - `[/\\]\.\.\.[/\\]` (Path truncation -> FAIL)
- **ALLOWED**: `^collecting \.\.\.$` (Explicit whitelist for benign pytest progress).

### `scripts/verify_a1a2_closure.py`

- **ADDED**: `clean_workspace()` to clear `artifacts/reclosure_work` before run.
- **ADDED**: Fail-closed logic for `inputs.txt` (exit 1 if file missing).
- **ADDED**: Fail-closed logic for `env_info.txt` (exit 1 if missing).
- **ADDED**: `TEST_REPORT` markdown generation.

## Appendix: Evidence Scripts

### A. generate_a1a2_evidence.py (v2.1)

```python
import os
import sys
import subprocess
import platform
import shutil
import re
from pathlib import Path

# Config
REPO_ROOT = Path(__file__).parent.parent
WORK_DIR = REPO_ROOT / "artifacts" / "reclosure_work"
EVIDENCE_DIR = WORK_DIR / "evidence"

# Truncation Detection Patterns (Fail-Closed)
TRUNCATION_PATTERNS = [
    (re.compile(r"::.*\.\.\."), "Node ID truncation detected"),   # e.g. ::test_something...
    (re.compile(r"test_.*\.\.\."), "Test name truncation detected"),
    (re.compile(r"[0-9a-fA-F]{6}\.\.\."), "Hash start truncation detected"), # e.g. abc123...
    (re.compile(r"\.\.\.[0-9a-fA-F]{6}"), "Hash end truncation detected"),   # e.g. ...abc123
    (re.compile(r"[/\\]\.\.\.[/\\]"), "Path truncation detected"), # e.g. /.../
]

# Benign Allow-List (Exact Matches Only)
BENIGN_PATTERNS = [
    re.compile(r"^collecting \.\.\.$"),
    re.compile(r"^collecting \.\.\. collected \d+ items$")
]

TEST_SUITES = [
    {
        "name": "pytest_a1",
        "targets": ["runtime/tests/test_agent_api.py", "runtime/tests/test_opencode_client.py"],
        "output": "pytest_a1.txt"
    },
    {
        "name": "pytest_a2",
        "targets": ["runtime/tests/test_tier2_suite.py"],
        "output": "pytest_a2.txt"
    }
]

def ensure_dirs():
    if not WORK_DIR.exists():
        WORK_DIR.mkdir(parents=True)
    if not EVIDENCE_DIR.exists():
        EVIDENCE_DIR.mkdir(parents=True)

def capture_env():
    env_file = EVIDENCE_DIR / "env_info.txt"
    print(f"Capturing environment info to {env_file}...")
    try:
        with open(env_file, "w", encoding="utf-8") as f:
            f.write(f"Python Version: {sys.version}\n")
            f.write(f"Platform: {platform.platform()}\n")
            f.write("Pip Freeze:\n")
            # Fail-closed: Must succeed
            subprocess.run([sys.executable, "-m", "pip", "freeze"], stdout=f, stderr=subprocess.STDOUT, check=True)
    except Exception as e:
        print(f"CRITICAL: Failed to capture environment info: {e}")
        sys.exit(1)

def run_tests():
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["COLUMNS"] = "200" # Prevent wrapping
    
    overall_success = True

    for suite in TEST_SUITES:
        output_path = EVIDENCE_DIR / suite["output"]
        # -v: Verbose, -ra: Show extra test info, --no-header: Reduce noise (optional, but keeping standard)
        # Avoiding -q (quiet) to ensure context, but relying on COLUMNS preventing wrap
        cmd = [sys.executable, "-m", "pytest", "-v"] + suite["targets"]
        
        print(f"Running suite {suite['name']} -> {output_path}...")
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                # Verbatim capture: stdout and stderr to file
                proc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, cwd=REPO_ROOT)
            
            if proc.returncode != 0:
                print(f"WARNING: Suite {suite['name']} returned exit code {proc.returncode}")
                overall_success = False
        except Exception as e:
            print(f"ERROR: Failed to run suite {suite['name']}: {e}")
            overall_success = False

    return overall_success

def is_benign(line_stripped):
    for pattern in BENIGN_PATTERNS:
        if pattern.match(line_stripped):
            return True
    return False

def scan_evidence():
    print("Scanning evidence for forbidden truncation...")
    failed = False
    
    for item in EVIDENCE_DIR.glob("*.txt"):
        try:
            with open(item, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                
                # Check for "..." trigger first (optimization)
                if "..." in line or "…" in line:
                    if is_banished(line_stripped):
                        print(f"FAIL: {item.name}:{i+1} - Truncation detected: '{line_stripped}'")
                        failed = True
        except Exception as e:
            print(f"ERROR: Could not read {item.name}: {e}")
            failed = True
            
    if failed:
        print("Evidence verification FAILED (Truncation detected).")
        sys.exit(1)
    else:
        print("Evidence verification PASSED.")

def is_banished(line):
    # If it's benign, we skip checks
    if is_benign(line):
        return False
        
    # Check specific patterns
    for pattern, reason in TRUNCATION_PATTERNS:
        if pattern.search(line):
            print(f"  Reason: {reason}")
            return True
    
    # Optional logic: could strictly ban ALL "..." if not benign.
    # But adhering to 'truncation-signature checks' as per instructions.
    return False

def main():
    ensure_dirs()
    capture_env()
    tests_passed = run_tests()
    scan_evidence() # Scan triggers regardless of test result
    
    if not tests_passed:
        print("Tests FAILED (Non-zero exit code).")
        sys.exit(1)
        
    print("All steps PASSED.")

if __name__ == "__main__":
    main()
```

### B. verify_a1a2_closure.py (v2.1)

```python
import os
import sys
import subprocess
import hashlib
import json
import shutil
from pathlib import Path
from datetime import datetime

# Config
REPO_ROOT = Path(__file__).parent.parent
WORK_DIR = REPO_ROOT / "artifacts" / "reclosure_work"
EVIDENCE_DIR = WORK_DIR / "evidence"
BUNDLE_DIR = REPO_ROOT / "artifacts" / "bundles"
CLOSURE_ID = "CLOSURE_A1_A2_RECLOSURE_v2.1"
BUNDLE_FILENAME = "Bundle_A1_A2_Closure_v2.1.zip"
BUNDLE_PATH = BUNDLE_DIR / BUNDLE_FILENAME
PROFILE = "step_gate_closure"

INPUT_FILES = [
    "runtime/agents/api.py",
    "runtime/orchestration/run_controller.py",
    "runtime/orchestration/registry.py",
    "runtime/engine.py"
]

TEST_REPORT_PATH = WORK_DIR / "TEST_REPORT_A1_A2_RECLOSURE_v2.1_PASS.md"
EXECUTION_LOG = []

def log_execution(command, exit_code, description):
    EXECUTION_LOG.append({
        "timestamp": datetime.now().isoformat(),
        "description": description,
        "command": " ".join(command) if isinstance(command, list) else command,
        "exit_code": exit_code
    })

def calculate_sha256(filepath):
    sha = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data: break
            sha.update(data)
    return sha.hexdigest().upper()

def run_step(description, cmd, cwd=REPO_ROOT, check=True):
    print(f"\n--- {description} ---")
    print(f"Command: {' '.join(cmd)}")
    try:
        proc = subprocess.run(cmd, cwd=cwd, check=False)
        log_execution(cmd, proc.returncode, description)
        if check and proc.returncode != 0:
            print(f"FAILED: {description}")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

def clean_workspace():
    print("Cleaning workspace...")
    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True)
    if not BUNDLE_DIR.exists():
        BUNDLE_DIR.mkdir(parents=True)

def generate_test_report():
    print(f"Generating Test Report: {TEST_REPORT_PATH}")
    with open(TEST_REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(f"# Test Report: A1/A2 Re-closure v2.1\n\n")
        f.write(f"**Date**: {datetime.now().isoformat()}\n")
        f.write(f"**Bundle**: `{BUNDLE_FILENAME}`\n\n")
        f.write("## Execution Log\n\n")
        f.write("| Timestamp | Description | Exit Code | Command |\n")
        f.write("|-----------|-------------|-----------|---------|\n")
        for entry in EXECUTION_LOG:
            f.write(f"| {entry['timestamp']} | {entry['description']} | {entry['exit_code']} | `{entry['command']}` |\n")
        
        f.write("\n## Evidence Inventory\n")
        if EVIDENCE_DIR.exists():
            for item in sorted(EVIDENCE_DIR.glob("*")):
                if item.is_file():
                    sha = calculate_sha256(item)
                    f.write(f"- `{item.name}` ({sha})\n")

def main():
    clean_workspace()
        
    # 1. Generate Evidence
    run_step("Generating Evidence (Strict)", [sys.executable, "scripts/generate_a1a2_evidence.py"])
    
    # 2. Creates Inventory Files
    print(f"\n--- Creating Inventory Files in {WORK_DIR} ---")
    
    # inputs.txt (Fail-Closed)
    inputs_path = WORK_DIR / "inputs.txt"
    with open(inputs_path, "w", encoding="utf-8") as f:
        for rel_path in INPUT_FILES:
            full_path = REPO_ROOT / rel_path
            if not full_path.exists():
                print(f"CRITICAL: Required input file missing: {rel_path}")
                sys.exit(1)
            sha = calculate_sha256(full_path)
            f.write(f"{rel_path}|{sha}|source_code\n")
    
    # outputs.txt (Fail-Closed Env Info)
    outputs_path = WORK_DIR / "outputs.txt"
    env_info_path = EVIDENCE_DIR / "env_info.txt"
    if not env_info_path.exists():
        print("CRITICAL: env_info.txt missing (Output generation failed)")
        sys.exit(1)
        
    env_sha = calculate_sha256(env_info_path)
    with open(outputs_path, "w", encoding="utf-8") as f:
        f.write(f"evidence/env_info.txt|{env_sha}|environment_snapshot\n")

    # gates.json
    gates_path = WORK_DIR / "gates.json"
    gates_data = [
        {"id": "test_a1_agent_api", "status": "PASS", "evidence_paths": ["evidence/pytest_a1.txt"]},
        {"id": "test_a2_ops_tier2", "status": "PASS", "evidence_paths": ["evidence/pytest_a2.txt"]}
    ]
    with open(gates_path, "w", encoding="utf-8") as f:
        json.dump(gates_data, f, indent=2)

    # evidence_list.txt for --include
    evidence_list_path = WORK_DIR / "evidence_list.txt"
    with open(evidence_list_path, "w", encoding="utf-8") as f:
        # Sort for determinism
        for item in sorted(EVIDENCE_DIR.glob("*")):
            if item.is_file():
                # Use strict repo-relative paths for determinism
                # item is abs path via WORK_DIR, we need relative to REPO_ROOT?
                # build_closure_bundle expects paths it can open.
                # If we pass abs paths to --include, the builder relativizes them.
                # We'll pass absolute paths here as before, builder handles it.
                f.write(f"{item}\n")

    # 3. Build Bundle
    base_cmd = [
        sys.executable, "scripts/closure/build_closure_bundle.py",
        "--profile", PROFILE,
        "--closure-id", CLOSURE_ID,
        "--schema-version", "1.1",
        "--inputs-file", str(inputs_path),
        "--outputs-file", str(outputs_path),
        "--gates-file", str(gates_path),
        "--include", str(evidence_list_path),
        "--output", str(BUNDLE_PATH)
    ]
    run_step("Building Closure Bundle", base_cmd)

    # 4. Verify Bundle
    audit_report_path = WORK_DIR / "final_audit_report_v2.1.md"
    verify_cmd = [
        sys.executable, "scripts/closure/validate_closure_bundle.py",
        str(BUNDLE_PATH),
        "--output", str(audit_report_path),
        "--deterministic"
    ]
    run_step("Verifying Closure Bundle", verify_cmd)
    
    generate_test_report()
    
    print(f"\nSUCCESS! Bundle created: {BUNDLE_PATH}")
    print(f"Audit Report: {audit_report_path}")

if __name__ == "__main__":
    main()
```
