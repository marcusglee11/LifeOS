# A1/A2 Evidence Closure Addendum v1.3

**Date:** 2026-01-05
**Scope:** A1 (Tier-2 Green Baseline), A2 (Reactive Determinism)
**Author:** Antigravity
**Evidence Level:** Audit-Grade (Clean Worktree, No Ellipses)
**RUN_COMMIT:** b20e47b65e5ebb013930c05cbbd23d271fd15049

## 1. Execution Evidence

### 1.1 Clean Worktree Setup
- **Worktree Path:** `.worktrees/a1a2_clean_b20e47b`
- **HEAD:** `b20e47b65e5ebb013930c05cbbd23d271fd15049`
- **Pre-run Status:** Empty (clean)
- **Pre-run Diff:** Empty (clean)

### 1.2 A1 Tier-2 Test Suite

**Command (exact):**
```cmd
cmd /c "python -m pytest runtime/tests tests_doc tests_recursive -v --tb=short > logs\tier2_v1_3.log 2>&1 && echo 0 > logs\tier2_v1_3_exitcode.txt || echo %ERRORLEVEL% > logs\tier2_v1_3_exitcode.txt"
```

**Result:** 452 passed, 1 skipped, 1 xfailed, 127 warnings
**Exit Code:** 0
**Log File:** `logs/tier2_v1_3.log`
**Log SHA256:** `823e48a2f21be11c2c66cfc8eaa2ff3603ef01b0071b8f9d34bc565f77784f0f`
**Exit Code File SHA256:** `f0cd2be81098275c345e58ca0cef5486272045a97fcaaafeb7d3fd8c9a8e9588`

### 1.3 A2 Reactive Determinism Tests

**Command (exact):**
```cmd
cmd /c "python -m pytest runtime/tests/test_reactive -v --tb=short > logs\reactive_determinism_v1_3.log 2>&1 && echo 0 > logs\reactive_determinism_v1_3_exitcode.txt || echo %ERRORLEVEL% > logs\reactive_determinism_v1_3_exitcode.txt"
```

**Result:** 35 passed
**Exit Code:** 0
**Log File:** `logs/reactive_determinism_v1_3.log`
**Log SHA256:** `670cf7ee53e4a37cd93db795fd0e2f745ee659325f1222c88894e2bd38e31c3c`
**Exit Code File SHA256:** `f0cd2be81098275c345e58ca0cef5486272045a97fcaaafeb7d3fd8c9a8e9588`

### 1.4 Post-Run Cleanliness
- **Post-run Status:** Empty (no tracked changes)
- **Post-run Diff:** Empty (no tracked changes)

## 2. Reactive v0.1 Determinism Invariants -> Assertions

| Invariant | Test Class | Test Function | File:Line | Assertion |
|-----------|------------|---------------|-----------|-----------|
| Public API Exports | TestCycle1PublicAPI | test_public_api_imports | test_spec_conformance.py:24 | All public symbols importable from runtime.reactive |
| Schema Exactness | TestCycle2SchemaConformance | test_plan_surface_schema_exact | test_spec_conformance.py:56 | Surface has exactly required keys |
| Constraints Default | TestCycle2SchemaConformance | test_constraints_default_matches_config | test_spec_conformance.py:72 | max_payload_chars matches config |
| Tags None Empty | TestCycle2SchemaConformance | test_tags_none_emits_empty_list | test_spec_conformance.py:82 | tags=None produces [] |
| Tags Order | TestCycle2SchemaConformance | test_tags_order_preserved | test_spec_conformance.py:91 | Tag order preserved in surface |
| Canonical JSON Stable | TestCycle3CanonicalJSON | test_canonical_json_is_stable | test_spec_conformance.py:107 | Same input produces identical JSON |
| Canonical JSON ASCII | TestCycle3CanonicalJSON | test_canonical_json_settings_are_pinned | test_spec_conformance.py:120 | ensure_ascii=True enforced |
| Canonical JSON Roundtrip | TestCycle3CanonicalJSON | test_canonical_json_roundtrip | test_spec_conformance.py:134 | json.loads matches original |
| Hash Stable | TestCycle4HashStability | test_surface_hash_is_stable | test_spec_conformance.py:149 | Same input produces identical SHA256 |
| Validate Valid | TestCycle5ValidationBoundaries | test_validate_request_accepts_valid | test_spec_conformance.py:171 | Valid request passes |
| Reject Empty ID | TestCycle5ValidationBoundaries | test_validate_request_rejects_empty_id | test_spec_conformance.py:179 | Empty id raises violation |
| Reject Invalid Tags | TestCycle5ValidationBoundaries | test_validate_request_rejects_invalid_tags_type | test_spec_conformance.py:192 | Non-tuple tags rejected |
| Reject Empty Title | TestCycle5ValidationBoundaries | test_validate_request_rejects_empty_title | test_spec_conformance.py:206 | Empty title raises violation |
| Reject Long Desc | TestCycle5ValidationBoundaries | test_validate_request_rejects_overlong_description | test_spec_conformance.py:219 | Overlong desc rejected |
| Reject Many Tags | TestCycle5ValidationBoundaries | test_validate_request_rejects_too_many_tags | test_spec_conformance.py:230 | Excess tags rejected |
| Reject Long Tag | TestCycle5ValidationBoundaries | test_validate_request_rejects_overlong_tag | test_spec_conformance.py:241 | Overlong tag rejected |
| Reject Oversize Surface | TestCycle5ValidationBoundaries | test_validate_surface_rejects_oversized_payload | test_spec_conformance.py:252 | Oversize payload rejected |
| Frozen Dataclasses | TestCycle6Immutability | test_dataclasses_are_frozen | test_spec_conformance.py:271 | Mutation raises FrozenInstanceError |
| Version Exists | TestVersionConstant | test_version_constant_exists_and_is_string | test_spec_conformance.py:292 | REACTIVE_LAYER_VERSION is string |
| Version Pattern | TestVersionConstant | test_version_constant_matches_semantic_pattern | test_spec_conformance.py:299 | Version matches semantic pattern |
| Surface Uses Version | TestVersionConstant | test_surface_uses_version_constant | test_spec_conformance.py:308 | Surface version matches constant |
| Dict Order Invariance | TestDeterminismHardening | test_dict_insertion_order_does_not_affect_canonical_json | test_spec_conformance.py:321 | Dict insertion order irrelevant |
| Field Order Invariance | TestDeterminismHardening | test_request_field_order_does_not_affect_surface | test_spec_conformance.py:334 | Field order irrelevant |
| Edge Title Limit | TestValidationEdgeCases | test_validate_request_at_exact_title_limit | test_spec_conformance.py:351 | Exact limit passes |
| Edge Desc Limit | TestValidationEdgeCases | test_validate_request_at_exact_description_limit | test_spec_conformance.py:362 | Exact limit passes |
| Edge Tags Limit | TestValidationEdgeCases | test_validate_request_at_exact_tags_limit | test_spec_conformance.py:373 | Exact limit passes |
| Edge Tag Char Limit | TestValidationEdgeCases | test_validate_request_at_exact_tag_char_limit | test_spec_conformance.py:384 | Exact limit passes |
| Unicode Title Escaped | TestUnicodeCoverage | test_unicode_in_title_is_escaped | test_spec_conformance.py:399 | Unicode escaped in title |
| Unicode Desc Escaped | TestUnicodeCoverage | test_unicode_in_description_is_escaped | test_spec_conformance.py:412 | Unicode escaped in desc |
| Unicode Tags Escaped | TestUnicodeCoverage | test_unicode_in_tags_is_escaped | test_spec_conformance.py:423 | Unicode escaped in tags |
| Build Surface Importable | TestBuildPlanSurface | test_build_plan_surface_is_importable | test_spec_conformance.py:438 | build_plan_surface exported |
| Build Surface Valid | TestBuildPlanSurface | test_build_plan_surface_produces_valid_surface | test_spec_conformance.py:443 | Returns valid surface |
| Build Rejects Invalid | TestBuildPlanSurface | test_build_plan_surface_rejects_invalid_request | test_spec_conformance.py:454 | Invalid request rejected |
| Build Rejects Oversize | TestBuildPlanSurface | test_build_plan_surface_rejects_oversized_payload | test_spec_conformance.py:463 | Oversize rejected |
| Build Deterministic | TestBuildPlanSurface | test_build_plan_surface_is_deterministic | test_spec_conformance.py:473 | Same input = same output |

## 3. Summary

| StepGate | Status | Evidence |
|----------|--------|----------|
| **A1 (Tier-2 Green)** | **DONE** | 452 passed; Exit=0; Log SHA256: 823e48a2... |
| **A2 (Reactive Det)** | **DONE** | 35 passed; Exit=0; Log SHA256: 670cf7ee... |
