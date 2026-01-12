# Test Report: GCBS Repayment v1.2.2 Shipped Evidence Delta v1.0

**Date**: 2026-01-06
**Subject**: v1.2.2 Validation (Evidence Consistency & Audit Semantics)

## Summary
All required gates for v1.2.2 passed. The build pipeline now produces a full-fidelity validator transcript that references the shipped bundle filename. The audit report avoids circular hash references when in detached mode.

## Gates Verified

### G1: TDD Compliance
- **Command**: `python -m pytest tests_doc/test_tdd_compliance.py`
- **Result**: PASS

### G2: Bundle Tests (Regressions & Integrity)
- **Command**: `python -m pytest scripts/closure/tests/`
- **Tests Run**: 9
    - `test_validator_transcript_completeness`: PASS (Updated for v1.2.2 requirements)
        - Asserted: Transcript contains `Bundle_GCBS_Repayment_v1.2.2.zip`
        - Asserted: Transcript contains `Exit Code: 0`
        - Asserted: Transcript contains `STDERR` section
        - Asserted: Audit Report matches `Digest Strategy: Detached`
    - `test_detached_digest_happy_path`: PASS
    - `test_detached_digest_missing`: PASS
    - `test_detached_digest_mismatch`: PASS
    - `test_bundle_zip_is_deterministic`: PASS
    - `test_truncation_token_rejected_strict`: PASS
- **Result**: PASS

### G3: Final Bundle Verification (v1.2.2)
- **Command**: `python scripts/closure/build_closure_bundle.py ... --output ...v1.2.2.zip`
- **Audit Report**: PASS (Clean)
- **Detached Sidecar**: Verified
- **Transcript**: Full fidelity (Captured from Candidate build named `Bundle_GCBS_Repayment_v1.2.2.zip`)

## Evidence
- `evidence/validator_run_shipped.txt` (Embedded in Bundle, role: `validator_final_shipped`)
