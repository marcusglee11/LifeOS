# A1/A2 Evidence Closure Addendum v1.3.4

**Date:** 2026-01-06
**Scope:** A1 (Tier-2 Green Baseline), A2 (Reactive Determinism)
**Author:** Antigravity
**Evidence Level:** Audit-Grade (v1.3.4 Final)
**RUN_COMMIT:** b20e47b65e5ebb013930c05cbbd23d271fd15049

## 1. Execution Evidence

### 1.1 A1 Tier-2 Test Suite

**Command (exact):**
```cmd
cmd /c "python -m pytest runtime/tests tests_doc tests_recursive -v --tb=short > logs/tier2_v1_3.log 2>&1"
```

**Result:** 452 passed, 1 skipped, 1 xfailed
**Exit Code:** 0

**Artifacts (zip paths):**
| File | SHA256 |
|------|--------|
| logs/tier2_v1_3.log | 823e48a2f21be11c2c66cfc8eaa2ff3603ef01b0071b8f9d34bc565f77784f0f |
| logs/tier2_v1_3_exitcode.txt | 13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354 |

### 1.2 A2 Reactive Determinism Tests

**Command (exact):**
```cmd
cmd /c "python -m pytest runtime/tests/test_reactive -v --tb=short > logs/reactive_determinism_v1_3.log 2>&1"
```

**Result:** 35 passed
**Exit Code:** 0

**Artifacts (zip paths):**
| File | SHA256 |
|------|--------|
| logs/reactive_determinism_v1_3.log | 670cf7ee53e4a37cd93db795fd0e2f745ee659325f1222c88894e2bd38e31c3c |
| logs/reactive_determinism_v1_3_exitcode.txt | 13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354 |

## 2. Bundle Contents

| Zip Path | Description | SHA256 |
|----------|-------------|--------|
| logs/tier2_v1_3.log | A1 full stdout/stderr | 823e48a2f21be11c2c66cfc8eaa2ff3603ef01b0071b8f9d34bc565f77784f0f |
| logs/reactive_determinism_v1_3.log | A2 full stdout/stderr | 670cf7ee53e4a37cd93db795fd0e2f745ee659325f1222c88894e2bd38e31c3c |
| logs/tier2_v1_3_exitcode.txt | A1 exit code (0) | 13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354 |
| logs/reactive_determinism_v1_3_exitcode.txt | A2 exit code (0) | 13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354 |
| A1A2_EVIDENCE_ADDENDUM_v1_3_4.md | This file | N/A |
| git_evidence_v1_3_4.txt | Git context and hash commands | N/A |
| LIFEOS_STATE.md | Updated state file | N/A |
| audit_report_v1_3_4.md | PASS/FAIL checklist | N/A |

## 3. ZIP SHA256

**Command:**
```powershell
certutil -hashfile Bundle_A1_A2_Closure_v1_3_4.zip SHA256
```

**ZIP SHA256:** See git_evidence_v1_3_4.txt Section 5 for final computed value.

## 4. Invariant Evidence Note (A2)

| Invariant | Test Class | Test Function | File:Line |
|-----------|------------|---------------|-----------|
| Public API Exports | TestCycle1PublicAPI | test_public_api_imports | test_spec_conformance.py:24 |
| Schema Exactness | TestCycle2SchemaConformance | test_plan_surface_schema_exact | test_spec_conformance.py:56 |
| Constraints Default | TestCycle2SchemaConformance | test_constraints_default_matches_config | test_spec_conformance.py:72 |
| Tags None Empty | TestCycle2SchemaConformance | test_tags_none_emits_empty_list | test_spec_conformance.py:82 |
| Tags Order | TestCycle2SchemaConformance | test_tags_order_preserved | test_spec_conformance.py:91 |
| Canonical JSON Stable | TestCycle3CanonicalJSON | test_canonical_json_is_stable | test_spec_conformance.py:107 |
| Canonical JSON ASCII | TestCycle3CanonicalJSON | test_canonical_json_settings_are_pinned | test_spec_conformance.py:120 |
| Canonical JSON Roundtrip | TestCycle3CanonicalJSON | test_canonical_json_roundtrip | test_spec_conformance.py:134 |
| Hash Stable | TestCycle4HashStability | test_surface_hash_is_stable | test_spec_conformance.py:149 |
| Validate Valid | TestCycle5ValidationBoundaries | test_validate_request_accepts_valid | test_spec_conformance.py:171 |
| Reject Empty ID | TestCycle5ValidationBoundaries | test_validate_request_rejects_empty_id | test_spec_conformance.py:179 |
| Reject Invalid Tags | TestCycle5ValidationBoundaries | test_validate_request_rejects_invalid_tags_type | test_spec_conformance.py:192 |
| Reject Empty Title | TestCycle5ValidationBoundaries | test_validate_request_rejects_empty_title | test_spec_conformance.py:206 |
| Reject Long Desc | TestCycle5ValidationBoundaries | test_validate_request_rejects_overlong_description | test_spec_conformance.py:219 |
| Reject Many Tags | TestCycle5ValidationBoundaries | test_validate_request_rejects_too_many_tags | test_spec_conformance.py:230 |
| Reject Long Tag | TestCycle5ValidationBoundaries | test_validate_request_rejects_overlong_tag | test_spec_conformance.py:241 |
| Reject Oversize Payload | TestCycle5ValidationBoundaries | test_validate_surface_rejects_oversized_payload | test_spec_conformance.py:252 |
| Frozen Dataclasses | TestCycle6Immutability | test_dataclasses_are_frozen | test_spec_conformance.py:271 |
| Version Exists | TestVersionConstant | test_version_constant_exists_and_is_string | test_spec_conformance.py:292 |
| Version Pattern | TestVersionConstant | test_version_constant_matches_semantic_pattern | test_spec_conformance.py:299 |
| Surface Version | TestVersionConstant | test_surface_uses_version_constant | test_spec_conformance.py:308 |
| Dict Order Invariance | TestDeterminismHardening | test_dict_insertion_order_does_not_affect_canonical_json | test_spec_conformance.py:321 |
| Field Order Invariance | TestDeterminismHardening | test_request_field_order_does_not_affect_surface | test_spec_conformance.py:334 |
| Edge Title | TestValidationEdgeCases | test_validate_request_at_exact_title_limit | test_spec_conformance.py:351 |
| Edge Desc | TestValidationEdgeCases | test_validate_request_at_exact_description_limit | test_spec_conformance.py:362 |
| Edge Tags | TestValidationEdgeCases | test_validate_request_at_exact_tags_limit | test_spec_conformance.py:373 |
| Edge Tag Char | TestValidationEdgeCases | test_validate_request_at_exact_tag_char_limit | test_spec_conformance.py:384 |
| Unicode Title | TestUnicodeCoverage | test_unicode_in_title_is_escaped | test_spec_conformance.py:399 |
| Unicode Desc | TestUnicodeCoverage | test_unicode_in_description_is_escaped | test_spec_conformance.py:412 |
| Unicode Tags | TestUnicodeCoverage | test_unicode_in_tags_is_escaped | test_spec_conformance.py:423 |
| Build Importable | TestBuildPlanSurface | test_build_plan_surface_is_importable | test_spec_conformance.py:438 |
| Build Valid | TestBuildPlanSurface | test_build_plan_surface_produces_valid_surface | test_spec_conformance.py:443 |
| Build Invalid Reject | TestBuildPlanSurface | test_build_plan_surface_rejects_invalid_request | test_spec_conformance.py:454 |
| Build Oversize Reject | TestBuildPlanSurface | test_build_plan_surface_rejects_oversized_payload | test_spec_conformance.py:463 |
| Build Deterministic | TestBuildPlanSurface | test_build_plan_surface_is_deterministic | test_spec_conformance.py:473 |
