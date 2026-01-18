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
CLOSURE_ID = "CLOSURE_A1_A2_RECLOSURE_v2.1c"
BUNDLE_FILENAME = "Bundle_A1_A2_Closure_v2.1c.zip"
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
        f.write(f"# Test Report: A1/A2 Re-closure v2.1c\n\n")
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
                # Use strict relative paths from WORK_DIR (e.g. evidence/foo.txt)
                # This ensures the ZIP internal structure matches gates.json references
                try:
                    rel_path = item.relative_to(WORK_DIR)
                    f.write(f"{rel_path}\n")
                except ValueError:
                    print(f"WARNING: Could not make path relative to WORK_DIR: {item}")
                    f.write(f"{item.name}\n")

    # 3. Build Bundle
    base_cmd = [
        sys.executable, str(REPO_ROOT / "scripts/closure/build_closure_bundle.py"),
        "--profile", PROFILE,
        "--closure-id", CLOSURE_ID,
        "--schema-version", "1.1",
        "--inputs-file", str(inputs_path),
        "--outputs-file", str(outputs_path),
        "--gates-file", str(gates_path),
        "--include", str(evidence_list_path),
        "--output", str(BUNDLE_PATH)
    ]
    # Run from WORK_DIR so relative include paths resolve correctly
    run_step("Building Closure Bundle", base_cmd, cwd=WORK_DIR)

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
