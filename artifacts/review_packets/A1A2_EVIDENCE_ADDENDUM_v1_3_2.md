# A1/A2 Evidence Closure Addendum v1.3.2

**Date:** 2026-01-05
**Scope:** A1 (Tier-2 Green Baseline), A2 (Reactive Determinism)
**Author:** Antigravity
**Evidence Level:** Audit-Grade Repack (v1.3.2)
**RUN_COMMIT:** b20e47b65e5ebb013930c05cbbd23d271fd15049

## 1. Execution Evidence

### 1.1 Artifacts (Path Corrected)

**Logs Directory:**
- `logs/tier2_v1_3.log`
  - SHA256: `823e48a2f21be11c2c66cfc8eaa2ff3603ef01b0071b8f9d34bc565f77784f0f`
- `logs/reactive_determinism_v1_3.log`
  - SHA256: `670cf7ee53e4a37cd93db795fd0e2f745ee659325f1222c88894e2bd38e31c3c`
- `logs/tier2_v1_3_exitcode.txt`
  - SHA256: `13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354`
- `logs/reactive_determinism_v1_3_exitcode.txt`
  - SHA256: `13bf7b3039c63bf5a50491fa3cfd8eb4e699d1ba1436315aef9cbe5711530354`

### 1.2 Bundle SHA256
**ZIP SHA256:** (See git_evidence_v1_3_2.txt for proof)
`a23f6b15767b50e9603877dbc1461d815e2194bf49fa43833d7172214a55e96a`

## 2. Invariant Evidence Note (A2)

| Invariant | Test Class | Test Function | File:Line | Assertion |
|-----------|------------|---------------|-----------|-----------|
| Public API Exports | TestCycle1PublicAPI | test_public_api_imports | test_spec_conformance.py:24 | All public symbols importable |
| Schema Exactness | TestCycle2SchemaConformance | test_plan_surface_schema_exact | test_spec_conformance.py:56 | Surface has exactly required keys |
| Constraints Default | TestCycle2SchemaConformance | test_constraints_default_matches_config | test_spec_conformance.py:72 | max_payload_chars matches config |
| Tags None Empty | TestCycle2SchemaConformance | test_tags_none_emits_empty_list | test_spec_conformance.py:82 | tags=None produces [] |
| Tags Order | TestCycle2SchemaConformance | test_tags_order_preserved | test_spec_conformance.py:91 | Tag order preserved |
| Canonical JSON Stable | TestCycle3CanonicalJSON | test_canonical_json_is_stable | test_spec_conformance.py:107 | Identical input -> identical JSON |
| Canonical JSON ASCII | TestCycle3CanonicalJSON | test_canonical_json_settings_are_pinned | test_spec_conformance.py:120 | ensure_ascii=True enforced |
| Canonical JSON Roundtrip | TestCycle3CanonicalJSON | test_canonical_json_roundtrip | test_spec_conformance.py:134 | Roundtrip integrity |
| Hash Stable | TestCycle4HashStability | test_surface_hash_is_stable | test_spec_conformance.py:149 | Identical input -> identical SHA256 |
| Validate Valid | TestCycle5ValidationBoundaries | test_validate_request_accepts_valid | test_spec_conformance.py:171 | Valid request passes |
| Reject Empty ID | TestCycle5ValidationBoundaries | test_validate_request_rejects_empty_id | test_spec_conformance.py:179 | Empty id rejected |
| Reject Invalid Tags | TestCycle5ValidationBoundaries | test_validate_request_rejects_invalid_tags_type | test_spec_conformance.py:192 | Invalid tags rejected |
| Reject Empty Title | TestCycle5ValidationBoundaries | test_validate_request_rejects_empty_title | test_spec_conformance.py:206 | Empty title rejected |
| Reject Long Desc | TestCycle5ValidationBoundaries | test_validate_request_rejects_overlong_description | test_spec_conformance.py:219 | Long desc rejected |
| Reject Many Tags | TestCycle5ValidationBoundaries | test_validate_request_rejects_too_many_tags | test_spec_conformance.py:230 | Too many tags rejected |
| Reject Long Tag | TestCycle5ValidationBoundaries | test_validate_request_rejects_overlong_tag | test_spec_conformance.py:241 | Long tag rejected |
| Reject Oversize Payload | TestCycle5ValidationBoundaries | test_validate_surface_rejects_oversized_payload | test_spec_conformance.py:252 | Oversize rejected |
| Frozen Dataclasses | TestCycle6Immutability | test_dataclasses_are_frozen | test_spec_conformance.py:271 | Mutation raises error |
| Version Exists | TestVersionConstant | test_version_constant_exists_and_is_string | test_spec_conformance.py:292 | Constant exists |
| Version Pattern | TestVersionConstant | test_version_constant_matches_semantic_pattern | test_spec_conformance.py:299 | Matches semantic pattern |
| Surface Version | TestVersionConstant | test_surface_uses_version_constant | test_spec_conformance.py:308 | Surface uses constant |
| Dict Order Invariance | TestDeterminismHardening | test_dict_insertion_order_does_not_affect_canonical_json | test_spec_conformance.py:321 | Order irrelevant |
| Field Order Invariance | TestDeterminismHardening | test_request_field_order_does_not_affect_surface | test_spec_conformance.py:334 | Order irrelevant |
| Edge Title | TestValidationEdgeCases | test_validate_request_at_exact_title_limit | test_spec_conformance.py:351 | Exact limit passes |
| Edge Desc | TestValidationEdgeCases | test_validate_request_at_exact_description_limit | test_spec_conformance.py:362 | Exact limit passes |
| Edge Tags | TestValidationEdgeCases | test_validate_request_at_exact_tags_limit | test_spec_conformance.py:373 | Exact limit passes |
| Edge Tag Char | TestValidationEdgeCases | test_validate_request_at_exact_tag_char_limit | test_spec_conformance.py:384 | Exact limit passes |
| Unicode Title | TestUnicodeCoverage | test_unicode_in_title_is_escaped | test_spec_conformance.py:399 | Escaped correctly |
| Unicode Desc | TestUnicodeCoverage | test_unicode_in_description_is_escaped | test_spec_conformance.py:412 | Escaped correctly |
| Unicode Tags | TestUnicodeCoverage | test_unicode_in_tags_is_escaped | test_spec_conformance.py:423 | Escaped correctly |
| Build Importable | TestBuildPlanSurface | test_build_plan_surface_is_importable | test_spec_conformance.py:438 | Import succeeds |
| Build Valid | TestBuildPlanSurface | test_build_plan_surface_produces_valid_surface | test_spec_conformance.py:443 | Valid surface produced |
| Build Invalid Reject | TestBuildPlanSurface | test_build_plan_surface_rejects_invalid_request | test_spec_conformance.py:454 | Rejected correctly |
| Build Oversize Reject | TestBuildPlanSurface | test_build_plan_surface_rejects_oversized_payload | test_spec_conformance.py:463 | Rejected correctly |
| Build Deterministic | TestBuildPlanSurface | test_build_plan_surface_is_deterministic | test_spec_conformance.py:473 | Deterministic output |
