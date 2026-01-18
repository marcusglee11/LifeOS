# Review Packet: Known Failures Gate v1.5 — Evidence & Integrity Patch

**Date**: 2026-01-09
**Version**: v1.5
**Author**: Antigravity Agent
**Status**: ✅ COMPLETE

## Summary

Hardened the "Known Failures Gate" to ensure cross-platform portability and absolute evidence integrity. Resolved the self-referential hash recursion by separating human-readable narrative from machine-readable manifests.

## Issue Catalogue

- **CRITICAL**: Self-referential hashing (EVIDENCE_PACKAGE.md containing its own hash) caused build loops.
- **CRITICAL**: ZIP hash mismatches occurred during multi-pass builds.
- **MAJOR**: Windows shell encoding (cp1252) caused gate script crashes when printing emojis.
- **MAJOR**: Relative path resolution in gate script was non-deterministic when run from outside repo root.

## Acceptance Criteria

- [x] NO truncated hashes (all 64 hex).
- [x] NO placeholders ("...", "verify after extraction").
- [x] POSIX-compliant ZIP paths (forward slashes).
- [x] Non-self-referential manifest (excludes self and ZIP hash).
- [x] Fail-closed logic for collection errors.
- [x] OS-agnostic path resolution and Unicode output.

## Non-Goals

- Modifying actual test logic or Fixing the 24 known failures (this mission provides the *gate*, not the fixes).
- Automating the Council promotion process.

## Appendix: Flattened Code

### 1. [check_known_failures_gate.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/check_known_failures_gate.py)

```python
"""
Known Failures Gate Check v1.1

This script enforces the "no new failures" gate for LifeOS test suite.
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
    """Run full test suite and capture output."""
    try:
        result = subprocess.run(
            ["pytest", "-q", "--tb=no"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
            timeout=300,
        )
        output = result.stdout + result.stderr
        return output, result.returncode
    except subprocess.TimeoutExpired:
        print("ERROR: Test suite timed out after 300s")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Failed to run test suite: {e}")
        sys.exit(1)


def parse_failing_nodeids(pytest_output: str) -> Set[str]:
    """Extract failing nodeids from pytest output."""
    failing = set()
    for line in pytest_output.splitlines():
        line = line.strip()
        if line.startswith("FAILED ") or line.startswith("ERROR "):
            parts = line.split()
            if len(parts) >= 2:
                nodeid = parts[1]
                failing.add(nodeid)
    return failing


def load_ledger() -> Set[str]:
    """Load known failures from JSON ledger."""
    if not LEDGER_PATH.exists():
        print(f"ERROR: Ledger not found at {LEDGER_PATH}")
        sys.exit(1)
    
    try:
        with open(LEDGER_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        nodeids = {entry["nodeid"] for entry in data.get("entries", [])}
        return nodeids
    except Exception as e:
        print(f"ERROR: Failed to load ledger: {e}")
        sys.exit(1)


def compare_failures(head_failures: Set[str], ledger_failures: Set[str]) -> Tuple[Set[str], Set[str]]:
    """Compare HEAD failures against ledger."""
    added = head_failures - ledger_failures
    removed = ledger_failures - head_failures
    return added, removed


def main():
    """Main gate check logic."""
    if sys.stdout.encoding.lower() != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"gate_check_output_{timestamp}.txt"
    
    with open(log_path, "w", encoding="utf-8") as log_file:
        original_stdout = sys.stdout
        sys.stdout = TeeWriter(log_file)
        
        try:
            print("=" * 80)
            print("Known Failures Gate Check v1.1")
            print("=" * 80)
            print(f"Timestamp: {datetime.now().isoformat()}")
            print(f"Log file: {log_path}")
            print()
            
            print("Running full test suite...")
            pytest_output, returncode = run_full_suite()
            
            head_failures = parse_failing_nodeids(pytest_output)
            print(f"HEAD failures detected: {len(head_failures)}")
            print(f"Pytest return code: {returncode}")
            
            if returncode != 0 and len(head_failures) == 0:
                print()
                print("❌ FAIL-CLOSED: Pytest returned non-zero but no FAILED/ERROR lines parsed.")
                print("   This indicates a collection failure, import error, or invalid test.")
                print("   Cannot safely compare against ledger.")
                print()
                sys.stdout = original_stdout
                sys.exit(1)
            
            ledger_failures = load_ledger()
            print(f"Ledger known failures: {len(ledger_failures)}")
            print()
            
            added, removed = compare_failures(head_failures, ledger_failures)
            
            if removed:
                print(f"✅ IMPROVEMENTS: {len(removed)} test(s) now passing:")
                for nodeid in sorted(removed):
                    print(f"   - {nodeid}")
                print()
            
            if added:
                print(f"❌ GATE FAILURE: {len(added)} NEW failure(s) detected:")
                for nodeid in sorted(added):
                    print(f"   - {nodeid}")
                print()
                sys.stdout = original_stdout
                sys.exit(1)
            else:
                print("✅ GATE PASS: No new failures detected.")
                sys.stdout = original_stdout
                sys.exit(0)
        
        finally:
            sys.stdout = original_stdout


if __name__ == "__main__":
    main()
```

### 2. [MANIFEST.sha256](file:///c:/Users/cabra/Projects/LifeOS/artifacts/known_failures/MANIFEST.sha256)

```text
48f0ee5647f642f88a4f8c9905ce017003a7d8c765c6583dd99ac0c3585be89f  artifacts/known_failures/EVIDENCE_PACKAGE.md
9a28265eb296c1849a3bc12c9103b2e113c92951da358dc6ced7ae1e20f7ab5d  artifacts/known_failures/Known_Failures_Ledger_v1.0.md
34ce3bc5fdafc19c7e8b47376e2276a884425adf155e5cabb6626dc69d3ade94  artifacts/known_failures/known_failures_ledger_v1.0.json
d0fbeae51fa673eb0c2c635b0835d42a5ad2564399d3efbc651c97e4f8eedf5e  runtime/tests/test_known_failures_gate.py
08c49c19f4afd0615aed2e8c445db83d80dcbc5fde167469dd6013a55c02b6d5  scripts/check_known_failures_gate.py
```

### 3. [generate_evidence_v1_5.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/generate_evidence_v1_5.py)

```python
import hashlib
import subprocess
import sys
import platform
import zipfile
from pathlib import Path
from datetime import datetime, timezone

# --- Constants ---
REPO_ROOT = Path(".").absolute()
ARTIFACTS_DIR = REPO_ROOT / "artifacts" / "known_failures"
SCRIPTS_DIR = REPO_ROOT / "scripts"
TESTS_DIR = REPO_ROOT / "runtime" / "tests"

PAYLOAD_FILES = {
    "artifacts/known_failures/Known_Failures_Ledger_v1.0.md": ARTIFACTS_DIR / "Known_Failures_Ledger_v1.0.md",
    "artifacts/known_failures/known_failures_ledger_v1.0.json": ARTIFACTS_DIR / "known_failures_ledger_v1.0.json",
    "scripts/check_known_failures_gate.py": SCRIPTS_DIR / "check_known_failures_gate.py",
    "runtime/tests/test_known_failures_gate.py": TESTS_DIR / "test_known_failures_gate.py",
}

EVIDENCE_FILE = ARTIFACTS_DIR / "EVIDENCE_PACKAGE.md"
MANIFEST_FILE = ARTIFACTS_DIR / "MANIFEST.sha256"
BUNDLE_PATH = REPO_ROOT / "artifacts" / "bundles" / "Bundle_Known_Failures_Gate_v1.5.zip"

def compute_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def run_command(cmd_list):
    try:
        result = subprocess.run(
            cmd_list, capture_output=True, text=True, cwd=REPO_ROOT,
            timeout=300, encoding="utf-8", errors="replace"
        )
        return result.stdout + result.stderr, result.returncode
    except Exception as e:
        return str(e), -1

def main():
    print("Step 1: Preparing hash-free EVIDENCE_PACKAGE.md...")
    gate_output, gate_code = run_command([sys.executable, "scripts/check_known_failures_gate.py"])
    test_output, test_code = run_command([sys.executable, "-m", "pytest", "runtime/tests/test_known_failures_gate.py", "-v"])
    
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ev_content = [
        "# Known Failures Gate v1.5 — Evidence Package",
        f"**Date**: {timestamp}",
        "**Version**: v1.5",
        "",
        "## Archive Entry List",
        "```",
    ]
    all_zip_entries = sorted(list(PAYLOAD_FILES.keys()) + [
        "artifacts/known_failures/EVIDENCE_PACKAGE.md",
        "artifacts/known_failures/MANIFEST.sha256"
    ])
    for entry in all_zip_entries:
        ev_content.append(entry)
    ev_content.extend([
        "```",
        "## Verification Output: Gate Check",
        f"**Exit Code**: {gate_code}",
        "```",
        gate_output.strip(),
        "```",
        "## Verification Output: Unit Tests",
        f"**Exit Code**: {test_code}",
        "```",
        test_output.strip(),
        "```",
        "---",
        "“Manifest excludes itself; zero hashes in evidence doc.”"
    ])
    
    with open(EVIDENCE_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(ev_content))
    
    manifest_entries = {rel: compute_sha256(abs_p) for rel, abs_p in PAYLOAD_FILES.items()}
    manifest_entries["artifacts/known_failures/EVIDENCE_PACKAGE.md"] = compute_sha256(EVIDENCE_FILE)
    
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        for rel_path in sorted(manifest_entries.keys()):
            f.write(f"{manifest_entries[rel_path]}  {rel_path}\n")
    
    with zipfile.ZipFile(BUNDLE_PATH, 'w', zipfile.ZIP_DEFLATED) as zf:
        for rel_path, abs_path in PAYLOAD_FILES.items():
            zf.write(abs_path, rel_path)
        zf.write(EVIDENCE_FILE, "artifacts/known_failures/EVIDENCE_PACKAGE.md")
        zf.write(MANIFEST_FILE, "artifacts/known_failures/MANIFEST.sha256")
        
    print(f"ZIP Path: {BUNDLE_PATH.as_posix()}")
    print(f"ZIP SHA256: {compute_sha256(BUNDLE_PATH)}")

if __name__ == "__main__":
    main()
```
