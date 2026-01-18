# Review Packet: A1/A2 Re-closure v2.1b (Portability + Truncation Hardening)

**Mission**: Re-close A1 (Agent API) and A2 (Ops) using strictly hardened G-CBS v1.1 rules.
**Version**: v2.1b (Portability Update)
**Date**: 2026-01-12
**Author**: Antigravity
**Status**: REVIEW_REQUIRED

## 1. Summary

Produced **Closure Bundle v2.1** (rebuilt as v2.1b) with enhanced scanning and portability:

- **Unicode Ellipsis Safe**: Scanner normalizes `…` to `...` before checking patterns (fail-closed integrity).
- **Portable Paths**: Verification script uses repo-relative paths for evidence inclusion.
- **Deterministic Reporting**: Verification log removes per-execution timestamps for stability.

## 2. Deliverables

| Artifact | Location | Status |
|----------|----------|--------|
| **Closure Bundle** | `artifacts/bundles/Bundle_A1_A2_Closure_v2.1.zip` | READY |
| **Audit Report** | `artifacts/reclosure_work/final_audit_report_v2.1.md` | **PASS** |
| **Test Report** | `artifacts/reclosure_work/TEST_REPORT_A1_A2_RECLOSURE_v2.1_PASS.md` | READY |

## 3. Bundle Digest

The following is the verbatim content of `artifacts/bundles/Bundle_A1_A2_Closure_v2.1.zip.sha256`:
`65FF5C9AD80B0DC4D447218ACF63C38C406101B1CCD0DCC4C98262201C86A588  Bundle_A1_A2_Closure_v2.1.zip`

> [!IMPORTANT]
> No hashes are truncated anywhere in this packet.

## 4. Evidence Capture & Scanning Semantics

* **Verbatim Capture**: `stderr` is redirected to `stdout` and written directly to disk without line filtering.
- **Truncation Scanning**:
  - **Normalization**: Unicode ellipses (`…`) are normalized to ASCII (`...`) prior to pattern matching.
  - **Fail-Closed Patterns**:
    - `::.*\.\.\.` (NodeID truncation)
    - `[0-9a-f]{6}\.\.\.` (Hash truncation)
    - `[/\\]\.\.\.[/\\]` (Path truncation)
  - **Allow-List**: `^collecting \.\.\.$` is whitelisted (matches standard pytest output only).
- **Portability**: The bundle builder receives strict relative paths to ensure the resulting ZIP structure is environment-agnostic.

## 5. Script Hardening Logic (Diff Summary v2.1b)

### `scripts/generate_a1a2_evidence.py`

- **ADDED**: Unicode normalization (`line.replace("…", "...")`) in `is_banished()` to catch non-ASCII truncation.

### `scripts/verify_a1a2_closure.py`

- **CHANGED**: `generate_test_report()` removes timestamps from the Execution Log table.
- **CHANGED**: `evidence_list.txt` generation now converts absolute paths to repo-relative paths (`item.relative_to(REPO_ROOT)`).

## Appendix: Evidence Scripts

### A. generate_a1a2_evidence.py (v2.1b)

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
    # Normalize unicode ellipsis to ASCII for robust pattern matching
    line_norm = line.replace("…", "...")
    
    # If it's benign, we skip checks (check against normalized form)
    if is_benign(line_norm):
        return False
        
    # Check specific patterns against normalized line
    for pattern, reason in TRUNCATION_PATTERNS:
        if pattern.search(line_norm):
            print(f"  Reason: {reason}")
            return True
    
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

### B. verify_a1a2_closure.py (v2.1b)

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
        f.write(f"# Test Report: A1/A2 Re-closure v2.1b\n\n")
        f.write(f"**Date**: {datetime.now().date().isoformat()} (Execution Date)\n")
        f.write(f"**Bundle**: `{BUNDLE_FILENAME}`\n\n")
        f.write("## Execution Log\n\n")
        f.write("| Description | Exit Code | Command |\n")
        f.write("|-------------|-----------|---------|\n")
        for entry in EXECUTION_LOG:
            f.write(f"| {entry['description']} | {entry['exit_code']} | `{entry['command']}` |\n")
        
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
                # Use strict repo-relative paths for determinism and portability
                try:
                    rel_path = item.relative_to(REPO_ROOT)
                    f.write(f"{rel_path}\n")
                except ValueError:
                    print(f"WARNING: Could not make path relative: {item}")
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
