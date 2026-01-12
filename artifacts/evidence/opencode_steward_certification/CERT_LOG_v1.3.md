# Certification Re-run Log (v1.3)

**Date**: 2026-01-06T23:47:49+11:00
**Command**: `python scripts/run_certification_tests.py --port 62585 --phase ALL`
**Git Branch**: (current working directory)
**Suite Version**: 1.3

## Results Summary
- **Total Tests**: 12
- **Passed**: 11
- **Failed**: 1

## Pass/Fail Breakdown

| Test ID | Name | Status |
|---------|------|--------|
| T-INPUT-1 | Valid JSON Accepted | PASS |
| T-INPUT-2 | Free-Text Rejected | PASS |
| T-SEC-1 | Path Traversal Rejected | PASS |
| T-SEC-2 | Absolute Path Rejected | PASS |
| T-SEC-3 | Denylist *.py Rejected | PASS |
| T-SEC-4 | Denylist scripts/** Rejected | PASS |
| T-SEC-5 | Denylist config/** Rejected | PASS |
| T-SEC-6 | Denylist GEMINI.md Rejected | PASS |
| T-SEC-7 | Denylist Foundations Rejected | PASS |
| T-SEC-8 | Evidence Read-Only Enforced | PASS |
| T-SEC-9 | Outside Allowed Roots Rejected | PASS |
| T-GIT-1 | Clean Tree Start | FAIL (waiver: pre-existing dirty environment) |

## Waiver Note
T-GIT-1 failure is due to pre-existing modified files (`GEMINI.md`, `artifacts/INDEX.md`, `artifacts/for_ceo/CT2_Activation_Packet_DocSteward_G3.md`) present in the user's working directory before certification began. This is environmental noise, not a failure of the steward enforcement layer.

## Artifacts
- **Report**: `artifacts/evidence/opencode_steward_certification/CERTIFICATION_REPORT_v1_3.json`
- **Hash Manifest**: `artifacts/evidence/opencode_steward_certification/HASH_MANIFEST_v1.3.json`
