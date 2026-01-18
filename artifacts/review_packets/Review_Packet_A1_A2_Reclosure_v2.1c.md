# Review Packet: A1/A2 Re-closure v2.1c (Internal Path Consistency)

**Mission**: Re-close A1 (Agent API) and A2 (Ops) using strictly hardened G-CBS v1.1 rules.
**Version**: v2.1c (Internal Path Consistency)
**Date**: 2026-01-12
**Author**: Antigravity
**Status**: REVIEW_REQUIRED

## 1. Summary

Produced **Closure Bundle v2.1c** with corrected internal pathing and audit hardening:

- **Internal Paths**: Evidence files stored as `evidence/*.txt` in ZIP, matching references in `gates.json` and `outputs.txt`.
- **Scanning & Normalization**: Caught non-ASCII truncation (Unicode `…`) via normalization.
- **Alignment**: Bundle version aligned to `v2.1c` for perfect audit traceability.

## 2. Deliverables

| Artifact | Location | Status |
|----------|----------|--------|
| **Closure Bundle** | `artifacts/bundles/Bundle_A1_A2_Closure_v2.1c.zip` | READY |
| **Audit Report** | `artifacts/reclosure_work/final_audit_report_v2.1.md` | **PASS** |
| **Test Report** | `artifacts/reclosure_work/TEST_REPORT_A1_A2_RECLOSURE_v2.1_PASS.md` | READY |
| **Sign-Off Record** | `artifacts/signoffs/AUR_20260112_A1_A2_Reclosure_v2.1c_Signoff.md` | READY |
| **Closure Record** | `artifacts/closures/CLOSURE_A1_A2_RECLOSURE_v2.1c.md` | READY |

## 3. Bundle Digest

The following is the verbatim content of `artifacts/bundles/Bundle_A1_A2_Closure_v2.1c.zip.sha256`:
`8F26A3E1C93D8AA57F98533324A5068688496C10C0B48048B868B190B9873C3A  Bundle_A1_A2_Closure_v2.1c.zip`

> [!IMPORTANT]
> No hashes are truncated anywhere in this packet.

## 4. ZIP Listing Evidence

Verifies that evidence is included under the `evidence/` prefix (not nested artifacts path).

Command: `zipinfo -1 artifacts/bundles/Bundle_A1_A2_Closure_v2.1c.zip | sort`

```
audit_report.md
closure_addendum.md
closure_manifest.json
evidence/env_info.txt
evidence/pytest_a1.txt
evidence/pytest_a2.txt
```

## 5. Evidence Capture & Scanning Semantics

* **Verbatim Capture**: raw `stdout` and `stderr` combined via `stderr=subprocess.STDOUT`.
- **Unicode Safe**: Unicode ellipses (`…`) normalized to `...` before signature matching.
- **Fail-Closed**: Non-zero exit if any truncation signature (`NodeID...`, `Hash...`) is detected.

## Appendix: Evidence Scripts

### A. generate_a1a2_evidence.py (v2.1c)

```python
def is_banished(line):
    # Normalize unicode ellipsis to ASCII for robust pattern matching
    line_norm = line.replace("…", "...")
    if is_benign(line_norm): return False
    # ... (Pattern checks) ...
    return False
```

### B. verify_a1a2_closure.py (v2.1c)

```python
def main():
    # ...
    # Run from WORK_DIR so relative include paths resolve correctly
    # evidence_list contains "evidence/foo.txt"
    run_step("Building Closure Bundle", base_cmd, cwd=WORK_DIR)
```
