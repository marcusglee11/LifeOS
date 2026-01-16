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
