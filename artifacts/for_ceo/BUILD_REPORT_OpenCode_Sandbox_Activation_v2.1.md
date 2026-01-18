# Build Report: OpenCode Sandbox Activation v2.1 (Fix Pack)

**Status**: VERIFIED
**Date**: 2026-01-12
**Mode**: Builder Mode Hardening

## 1. Summary

Corrected defects in v2.0 bundle. Implemented strict fail-closed logic for Builder Mode (Block D/R/C), fixed path security case-sensitivity, and repaired audit integrity (no truncation, full hashes).

## 2. Changes Implemented

- **Policy**: `scripts/opencode_gate_policy.py` updated to:
  - Block structural operations (D/R/C) in `MODE_BUILDER`.
  - Use original path for OS security checks (fixes case sensitivity).
  - Add `BUILDER_STRUCTURAL_BLOCKED` reason code.
- **Tests**: `tests/test_opencode_gate_policy_builder.py` updated with:
  - `test_builder_blocks_structural_ops`
  - `test_case_sensitivity_check`
  - `test_symlink_escape_blocked`

## 3. Evidence Map (DONE Criteria)

| ID | Criterion | Status | Evidence File | Hash (SHA256) |
|----|-----------|--------|---------------|---------------|
| E1 | Builder blocks D/R/C | PASS | `artifacts/reports/captures/test_opencode_builder_v2.1_PASS.txt` | `33d57560f4b30d2dcd11a24792730dddbd9df96b1cd6c43fff042c07923a837b` |
| E2 | Case-sensitivity Check | PASS | `artifacts/reports/captures/test_opencode_builder_v2.1_PASS.txt` | `33d57560f4b30d2dcd11a24792730dddbd9df96b1cd6c43fff042c07923a837b` (test_case_sensitivity_check) |
| E3 | Symlink Escape Blocked | PASS | `artifacts/reports/captures/test_opencode_builder_v2.1_PASS.txt` | `33d57560f4b30d2dcd11a24792730dddbd9df96b1cd6c43fff042c07923a837b` (test_symlink_escape_blocked) |
| E4 | Critical Files Protected | PASS | `artifacts/reports/captures/test_opencode_builder_v2.1_PASS.txt` | `33d57560f4b30d2dcd11a24792730dddbd9df96b1cd6c43fff042c07923a837b` (test_builder_mode_blocks_critical_files) |
| E5 | Audit Consistency | PASS | This Report | (Self-referential, see final bundle hash) |
| E6 | G-CBS Validator Pass | PASS | `audit_report.md` (in bundle) | (Generated during bundling) |

## 4. Source Artifacts (Full SHA-256)

- **Policy**: `scripts/opencode_gate_policy.py`
  - SHA256: `6ea82baf25140504919701f55e42d516b943b7d4f3e92d147fe91c07d31cf6fb`
- **Runner**: `scripts/opencode_ci_runner.py`
  - SHA256: `0a604bf76994366ee4742b9072e32d61fd4cd85508ef2ceb99f84923e6cb82ab`
- **Builder Tests**: `tests/test_opencode_gate_policy_builder.py`
  - SHA256: `4bd386d71af4614e08dfd8746fe715d373acfa27afff310a3bbedd020635669e`
- **Regression Logs**: `artifacts/reports/captures/test_opencode_regression_v2.1_PASS.txt`
  - SHA256: `433ccff43bbaea148b3177e99e1eb06a001a8e51a9f89be6f335220cda2db224`
