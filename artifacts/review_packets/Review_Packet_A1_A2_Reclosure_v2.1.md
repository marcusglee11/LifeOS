# Review Packet: A1/A2 Re-closure v2.1 (Hardening)

**Mission**: Re-close A1 (Agent API) and A2 (Ops) using strictly hardened G-CBS v1.1 rules.
**Date**: 2026-01-11
**Author**: Antigravity
**Status**: REVIEW_REQUIRED

## 1. Summary

Produced **Closure Bundle v2.1** with strict adherence to "repayment hardening" requirements:

- **Verbatim Evidence**: No stdout filtering; raw capture processed by fail-closed scanners.
- **Smart Truncation Checks**: Allowed benign `collecting ...` but disallowed dangerous nodeid/hash truncation.
- **Fail-Closed Inventories**: Build fails if inputs or environment info are missing.

## 2. Deliverables

| Artifact | Location | SHA256 (Partial) |
|----------|----------|------------------|
| **Closure Bundle** | `artifacts/bundles/Bundle_A1_A2_Closure_v2.1.zip` | `CFDD3E260E9D3227...` |
| **Sidecar SHA** | `artifacts/bundles/Bundle_A1_A2_Closure_v2.1.zip.sha256` | (Full hash in file) |
| **Audit Report** | `artifacts/reclosure_work/final_audit_report_v2.1.md` | **PASS** |
| **Test Report** | `artifacts/reclosure_work/TEST_REPORT_A1_A2_RECLOSURE_v2.1_PASS.md` | (Execution Log) |

## 3. Script Hardening Logic (Diff Summary)

### `scripts/generate_a1a2_evidence.py`

- **REMOVED**: `subprocess.output` line filtering (was dropping "collecting ..."). Reverted to verbatim capture.
- **ADDED**: `scan_evidence()` now uses regex-based truncation signatures:
  - `::.*\.\.\.` (NodeID truncation -> FAIL)
  - `[0-9a-f]{6}\.\.\.` (Hash truncation -> FAIL)
  - `[/\\]\.\.\.[/\\]` (Path truncation -> FAIL)
- **ALLOWED**: `^collecting \.\.\.$` (Explicit whitelist for benign pytest progress).

### `scripts/verify_a1a2_closure.py`

- **ADDED**: `clean_workspace()` to nuke `artifacts/reclosure_work` before run.
- **ADDED**: Fail-closed logic for `inputs.txt` generation (exit 1 if file missing).
- **ADDED**: Fail-closed logic for `env_info.txt` (exit 1 if missing).
- **ADDED**: `TEST_REPORT` markdown generation.

## 4. Acceptance Check

- [x] **Verbatim Capture**: Confirmed by script logic (subprocess.run with stdout redirection).
- [x] **Truncation Safety**: Confirmed by `scan_evidence` passing.
- [x] **Fail-Closed**: Confirmed by script logic updates.
- [x] **Audit PASS**: G-CBS v1.1 validation passed.

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

# ... (Config omitted for brevity) ...

# Truncation Detection Patterns (Fail-Closed)
TRUNCATION_PATTERNS = [
    (re.compile(r"::.*\.\.\."), "Node ID truncation detected"),
    (re.compile(r"test_.*\.\.\."), "Test name truncation detected"),
    (re.compile(r"[0-9a-fA-F]{6}\.\.\."), "Hash start truncation detected"),
    (re.compile(r"\.\.\.[0-9a-fA-F]{6}"), "Hash end truncation detected"),
    (re.compile(r"[/\\]\.\.\.[/\\]"), "Path truncation detected"),
]

# Benign Allow-List (Exact Matches Only)
BENIGN_PATTERNS = [
    re.compile(r"^collecting \.\.\.$"),
    re.compile(r"^collecting \.\.\. collected \d+ items$")
]

# ... (capture_env and run_tests ensure verbatim capture) ...

def scan_evidence():
    # ... (Implementation scans lines against patterns) ...
```
