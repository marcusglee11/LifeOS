# Repair Closure Bundle Defects: FIX RETURN

**Date**: 2026-01-14
**Status**: FIXED

## Summary of P0 Changes

| ID | Defect | Resolution |
|----|--------|------------|
| P0.1 | RPV: Fake Parsing | Implemented strict Acceptance Criteria table parsing with enforced columns (ID, Criterion, Status, Evidence Pointer, SHA-256) and grammar validation for pointers/hashes. |
| P0.2 | Schema Alignment | Updated `lifeos_packet_schemas_CURRENT.yaml` to require `closure_evidence` in `REVIEW_PACKET` and harmonized constraints. |
| P0.3 | PPV Completion | Implemented PPV001-PPV008 logic, including proven-claim evidence checking (PPV003/005) and distinct FAIL code counting (PPV006). |
| P0.4 | Audit Report | Patched `build_closure_bundle.py` to inject real `run_timestamp` and `bundle_name`, ensuring `audit_report.md` does not claim unimplemented checks. |
| P0.5 | Output Contract | Standardized both validators to output `PASS` or `FAIL <CODE>: <MESSAGE>` (fail-closed). |
| P0.6 | Evidence | Included verifiable verbatim run logs below. |

## Canonical Output Contract

The validators strictly adhere to the following output contract:

- **Success**: `PASS`
- **Failure**: `FAIL <CODE>: <MESSAGE>`

## Changed Files (Lexicographic List)

- `docs/02_protocols/lifeos_packet_schemas_CURRENT.yaml`
- `scripts/closure/build_closure_bundle.py`
- `scripts/generate_plan_fixtures.py`
- `scripts/generate_review_fixtures.py`
- `scripts/validate_plan_packet.py`
- `scripts/validate_review_packet.py`

## Verifiable Evidence Logs

### validate_review_packet.py (1 PASS + 5 FAIL)

```text
> python validate_review_packet.py pass_01.md
PASS
> python validate_review_packet.py fail_RPV001.md
FAIL RPV001: Missing section 'Scope Envelope'.
> python validate_review_packet.py fail_RPV002.md
FAIL RPV002: Section 'Summary' found before previous section.
> python validate_review_packet.py fail_RPV003.md
FAIL RPV003: Acceptance Criteria table missing column 'evidence pointer'. Found: ['id', 'criterion', 'status', 'sha-256']
> python validate_review_packet.py fail_RPV004.md
FAIL RPV004: Invalid Evidence Pointer 'bad pointer' (must be path | path:Lx-Ly | path#sha256:<HEX64> | N/A(<reason>)).
> python validate_review_packet.py fail_RPV005.md
FAIL RPV005: Missing mandatory checklist row 'Provenance'.
```

### validate_plan_packet.py (1 PASS + 5 FAIL)

```text
> python validate_plan_packet.py pass_01.md
PASS
> python validate_plan_packet.py fail_PPV001.md
FAIL PPV001: Missing required section 'Scope Envelope' in PLAN_PACKET.
> python validate_plan_packet.py fail_PPV002.md
FAIL PPV002: PLAN_PACKET section order invalid. Expected: Scope Envelope -> Proposed Changes -> Claims -> Targets -> Validator Contract -> Verification Matrix -> Migration Plan -> Governance Impact.
> python validate_plan_packet.py fail_PPV003.md
FAIL PPV003: Claim 'C' marked proven but evidence pointer missing.
> python validate_plan_packet.py fail_PPV005.md
FAIL PPV005: Claim 'C' marked proven but evidence file not found at 'nonexistent_file.md'.
> python validate_plan_packet.py fail_PPV006.md
FAIL PPV006: Verification Matrix insufficient (need >=1 PASS and >=5 FAIL with distinct codes; found PASS=1, FAIL_DISTINCT=4).
```
