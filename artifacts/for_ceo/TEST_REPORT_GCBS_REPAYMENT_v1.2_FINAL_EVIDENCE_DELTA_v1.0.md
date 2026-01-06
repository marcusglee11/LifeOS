# Test Report: GCBS Repayment v1.2 Final Evidence Delta v1.0

**Date**: 2026-01-06
**Subject**: v1.2 -> v1.2.1 Validation (Evidence & Digest Fixes)

## Summary
All required gates for v1.2.1 passed. The validator now correctly handles detached digests in the report, and the builder captures full-fidelity validator transcripts ("Draft+Sidecar" strategy).

## Gates Verified

### G1: TDD Compliance
- **Command**: `python -m pytest tests_doc/test_tdd_compliance.py`
- **Result**: PASS

### G2: Bundle Tests (Regressions & Negative)
- **Command**: `python -m pytest scripts/closure/tests/`
- **Tests Run**: 9
    - `test_detached_digest_happy_path`: PASS
    - `test_detached_digest_missing`: PASS (Negative)
    - `test_detached_digest_mismatch`: PASS (Negative)
    - `test_bundle_zip_is_deterministic`: PASS (Strict)
    - `test_no_transient_paths`: PASS
    - `test_posix_path_accepted`: PASS
    - `test_sha_mismatch_rejected`: PASS
    - `test_truncation_token_rejected_strict`: PASS (Negative)
    - `test_validator_transcript_completeness`: PASS (Negative)
- **Result**: PASS

### G3: Final Bundle Verification (v1.2.1)
- **Command**: `python scripts/closure/build_closure_bundle.py ... --output ...v1.2.1.zip`
- **Audit Report**: PASS (Clean)
- **Detached Sidecar**: Verified
- **Transcript**: Full fidelity (Exit Code present, no `...`)

## Evidence
- `evidence/validator_run_final.txt` (Embedded in Bundle)
- `evidence/pytest_bundle_tests.txt` (Embedded in Bundle)
