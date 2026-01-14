# G-CBS v1.0 Repayment — Implementation Plan

## Goal

Re-close waived items A1/A2 under deterministic G-CBS validator gate, eliminating the prior waiver debt:
- Zip path separator non-canonicalization → Fixed by POSIX normalization
- Zip SHA mismatch → Fixed by deterministic manifest/hash generation
- Evidence ellipses → Enforced by truncation token scanner

---

## User Review Required

> [!IMPORTANT]
> The G-CBS infrastructure (`validate_closure_bundle.py`, `build_closure_bundle.py`) already exists and passed verification. This build focuses on:
> 1. Adding TDD-compliant regression tests that lock in the A1/A2 failure modes
> 2. Building a fresh A1/A2 bundle that passes the validator
> 3. Marking A1/A2 as DONE (no longer WAIVER) in LIFEOS_STATE.md

No protocol changes are required. All work stays within existing G-CBS v1.0 boundaries.

---

## Proposed Changes

### Component 1: Regression Tests (TDD-first)

Add regression tests that explicitly reproduce the waived failures before confirming they are caught.

#### [NEW] [test_gcbs_a1a2_regressions.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/closure/tests/test_gcbs_a1a2_regressions.py)

New pytest module with:
1. `test_backslash_path_rejected()` — Bundle with `\\` paths fails `ZIP_PATH_NON_CANONICAL`
2. `test_ellipsis_in_log_rejected()` — Evidence with `...` fails `TRUNCATION_TOKEN_FOUND`
3. `test_sha_mismatch_rejected()` — Mismatched hash fails `SHA256_MISMATCH`
4. `test_deterministic_ordering()` — Same inputs produce byte-identical manifest

---

### Component 2: A1/A2 Closure Bundle

Build new bundle using G-CBS builder with clean evidence.

#### [NEW] Bundle file
Path: `artifacts/bundles/Bundle_A1_A2_Closure_GCBS_v1.0.zip`

Contents:
- `closure_manifest.json` — G-CBS-1.0 schema, profile: a1a2
- `closure_addendum.md` — Inventory with SHA256 hashes
- `logs/tier2_baseline.log` — Clean log (no ellipses)
- `logs/reactive_determinism.log` — Clean log (no ellipses)
- `audit_report.md` — Validator-generated PASS report

---

### Component 3: Documentation Update

#### [MODIFY] [LIFEOS_STATE.md](file:///c:/Users/cabra/Projects/LifeOS/docs/11_admin/LIFEOS_STATE.md)

Update lines 47-48:
```diff
-6. **[CLOSED (WAIVER)]** A2 Reactive v0.1 Determinism | Waiver: `artifacts/waivers/WAIVER_A1A2_Closure_v1_3_4.md` | Waived: zip paths, zip sha mismatch, ellipses | Repayment: G-CBS v1.0 + re-close under validator
-7. **[CLOSED (WAIVER)]** A1 Tier-2 Green Baseline | Waiver: `artifacts/waivers/WAIVER_A1A2_Closure_v1_3_4.md` | Waived: zip paths, zip sha mismatch, ellipses | Repayment: G-CBS v1.0 + re-close under validator
+6. **[DONE]** A2 Reactive v0.1 Determinism | Evidence: `artifacts/bundles/Bundle_A1_A2_Closure_GCBS_v1.0.zip`, Validator PASS
+7. **[DONE]** A1 Tier-2 Green Baseline | Evidence: `artifacts/bundles/Bundle_A1_A2_Closure_GCBS_v1.0.zip`, Validator PASS
```

---

## Verification Plan

### Automated Tests

| # | Command | Expected | Purpose |
|---|---------|----------|---------|
| 1 | `pytest tests_doc/test_tdd_compliance.py -v` | 12/12 PASS | TDD compliance gate |
| 2 | `pytest scripts/closure/tests/test_gcbs_a1a2_regressions.py -v` | 4/4 PASS | Regression tests for A1/A2 |
| 3 | `python scripts/closure/tests/verify_gcbs.py` | "ALL VERIFICATION PASSED" | G-CBS pipeline E2E |
| 4 | `python scripts/closure/validate_closure_bundle.py artifacts/bundles/Bundle_A1_A2_Closure_GCBS_v1.0.zip` | Exit 0, "PASS" | Final bundle validation |

### Evidence Capture

All test commands will be run with full output captured (no elisions) for:
- `TEST_REPORT_GCBS_REPAYMENT_v1.0.md`
- `EVIDENCE_MANIFEST_GCBS_REPAYMENT_v1.0.txt`

### Manual Verification

None required — all checks are automated via validator gate.

---

## DONE Definition

Per instruction block Section E:

| # | Criterion | Verification |
|---|-----------|--------------|
| E1 | A1/A2 re-closed under validator | Bundle_A1_A2_Closure_GCBS_v1.0.zip PASS |
| E2 | Deterministic packaging proven | Regression test `test_deterministic_ordering` |
| E3 | No evidence elisions | Truncation token scan PASS |
| E4 | All tests pass | TDD (12) + Regressions (4) + Verify GCBS |
| E5 | Documentation updated | LIFEOS_STATE.md shows [DONE] |
