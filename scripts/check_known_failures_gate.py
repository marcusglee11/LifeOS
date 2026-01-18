"""
Known Failures Gate Check v1.1

This script enforces the "no new failures" gate for LifeOS test suite.

Gate Semantics:
- PASS: If HEAD_failures ⊆ ledger_entries (all failures are known)
- FAIL: If HEAD_failures ⊄ ledger_entries (new unknown failures detected)
- FAIL: If pytest returns non-zero but no failures/errors parsed (fail-closed)

Usage:
    python scripts/check_known_failures_gate.py

Exit Codes:
    0: PASS (no new failures)
    1: FAIL (new failures detected, parsing error, or pytest failure)
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Set, Tuple, TextIO


REPO_ROOT = Path(__file__).parent.parent
LEDGER_PATH = REPO_ROOT / "artifacts" / "known_failures" / "known_failures_ledger_v1.0.json"
LOG_DIR = REPO_ROOT / "artifacts" / "known_failures"


class TeeWriter:
    """Write to both stdout and a log file."""
    
    def __init__(self, log_file: TextIO):
        self.log_file = log_file
        self.stdout = sys.stdout
    
    def write(self, text: str):
        self.stdout.write(text)
        self.log_file.write(text)
        self.log_file.flush()
    
    def flush(self):
        self.stdout.flush()
        self.log_file.flush()


def run_full_suite() -> Tuple[str, int]:
    """
    Run full test suite and capture output.
    
    Returns:
        Tuple of (raw pytest output as string, return code).
    """
    try:
        result = subprocess.run(
            ["pytest", "-q", "--tb=no"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=300,
        )
        # Combine stdout and stderr for robustness
        output = result.stdout + result.stderr
        return output, result.returncode
    except subprocess.TimeoutExpired:
        print("ERROR: Test suite timed out after 300s")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to run test suite: {e}")
        sys.exit(1)


def parse_failing_nodeids(pytest_output: str) -> Set[str]:
    """
    Extract failing nodeids from pytest output.
    
    Deterministic parsing: looks for lines starting with "FAILED " or "ERROR ",
    extracts the second whitespace-delimited token (the nodeid).
    
    Args:
        pytest_output: Raw pytest output text.
        
    Returns:
        Set of failing nodeids (deterministic, no temp paths).
    """
    failing = set()
    for line in pytest_output.splitlines():
        line = line.strip()
        # Parse both FAILED and ERROR lines
        if line.startswith("FAILED ") or line.startswith("ERROR "):
            parts = line.split()
            if len(parts) >= 2:
                nodeid = parts[1]
                failing.add(nodeid)
    return failing


def load_ledger() -> Set[str]:
    """
    Load known failures from JSON ledger.
    
    Returns:
        Set of known failing nodeids.
    """
    if not LEDGER_PATH.exists():
        print(f"ERROR: Ledger not found at {LEDGER_PATH}")
        sys.exit(1)
    
    try:
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Extract nodeids from entries
        nodeids = {entry["nodeid"] for entry in data.get("entries", [])}
        return nodeids
    except Exception as e:
        print(f"ERROR: Failed to load ledger: {e}")
        sys.exit(1)


def compare_failures(head_failures: Set[str], ledger_failures: Set[str]) -> Tuple[Set[str], Set[str]]:
    """
    Compare HEAD failures against ledger.
    
    Args:
        head_failures: Failing nodeids from current HEAD.
        ledger_failures: Known failing nodeids from ledger.
        
    Returns:
        Tuple of (added failures, removed failures).
        - added: NEW failures not in ledger (gate violation)
        - removed: Ledger failures that now pass (improvement, allowed)
    """
    added = head_failures - ledger_failures
    removed = ledger_failures - head_failures
    return added, removed


def main():
    """Main gate check logic."""
    # Force UTF-8 stdout to prevent Windows cp1252 errors with emojis
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass # Keep going if reconfiguration fails

    # Setup self-logging (bypass shell piping issues on Windows)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"gate_check_output_{timestamp}.txt"
    
    with open(log_path, "w", encoding="utf-8") as log_file:
        # Redirect stdout to both console and log
        original_stdout = sys.stdout
        sys.stdout = TeeWriter(log_file)
        
        try:
            print("=" * 80)
            print("Known Failures Gate Check v1.1")
            print("=" * 80)
            print(f"Timestamp: {datetime.now().isoformat()}")
            print(f"Log file: {log_path}")
            print()
            
            # Step 1: Run full suite
            print("Running full test suite...")
            pytest_output, returncode = run_full_suite()
            
            # Step 2: Parse failing nodeids (both FAILED and ERROR)
            head_failures = parse_failing_nodeids(pytest_output)
            print(f"HEAD failures detected: {len(head_failures)}")
            print(f"Pytest return code: {returncode}")
            
            # Step 2.5: Fail-closed check for collection failures
            if returncode != 0 and len(head_failures) == 0:
                print()
                print("❌ FAIL-CLOSED: Pytest returned non-zero but no FAILED/ERROR lines parsed.")
                print("   This indicates a collection failure, import error, or invalid test.")
                print("   Cannot safely compare against ledger.")
                print()
                print("Pytest output excerpt (last 50 lines):")
                print("-" * 80)
                for line in pytest_output.splitlines()[-50:]:
                    print(line)
                sys.stdout = original_stdout
                sys.exit(1)
            
            # Step 3: Load ledger
            ledger_failures = load_ledger()
            print(f"Ledger known failures: {len(ledger_failures)}")
            print()
            
            # Step 4: Compare
            added, removed = compare_failures(head_failures, ledger_failures)
            
            # Step 5: Report
            if removed:
                print(f"✅ IMPROVEMENTS: {len(removed)} test(s) now passing (removed from failures):")
                for nodeid in sorted(removed):
                    print(f"   - {nodeid}")
                print()
            
            if added:
                print(f"❌ GATE FAILURE: {len(added)} NEW failure(s) detected (not in ledger):")
                for nodeid in sorted(added):
                    print(f"   - {nodeid}")
                print()
                print("Action required: Fix new failures or update ledger (governance-controlled).")
                sys.stdout = original_stdout
                sys.exit(1)
            else:
                print("✅ GATE PASS: No new failures detected.")
                print(f"   HEAD failures: {len(head_failures)}")
                print(f"   All failures are documented in ledger.")
                sys.stdout = original_stdout
                sys.exit(0)
        
        finally:
            sys.stdout = original_stdout


if __name__ == "__main__":
    main()
