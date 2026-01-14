# Review Packet: Phase 3 Mission Types — Steward Envelope Semantics Fix

**Version**: v1.1  
**Date**: 2026-01-10  
**Mission**: Tier-2.5 Phase 3 — Steward Envelope Semantics Fix

---

## 1. Summary

Fixed StewardMission envelope policy to ensure "out-of-envelope" never implies "allowed":

| Requirement | Status |
|-------------|--------|
| P0.1 — Define A/B/C classification | DONE |
| P0.2 — Fail-closed for all categories | DONE |
| P0.3 — Replace incorrect tests | DONE |
| P0.4 — Pytest verification | PASS (47/47) |

---

## 2. Path Classification (P0.1)

| Category | Pattern | Enforcement |
|----------|---------|-------------|
| **A) in_envelope** | `docs/**/*.md` excluding protected roots | BLOCK (requires OpenCode routing) |
| **B) protected** | `docs/00_foundations/**`, `docs/01_governance/**`, `scripts/**`, `config/**` | BLOCK unconditionally |
| **C) disallowed** | Everything else (non-doc, non-.md) | BLOCK by default (no allowlist) |

**Only allowed case**: Empty artifact list (steward commits nothing)

---

## 3. Files Changed (sorted)

| File | Change Type |
|------|-------------|
| runtime/orchestration/missions/steward.py | MODIFY |
| runtime/tests/test_missions_phase3.py | MODIFY |

---

## 4. Key Changes

### steward.py

1. Added `_classify_path(path)` returning `"in_envelope"`, `"protected"`, or `"disallowed"`
2. Added `_validate_steward_targets(artifacts)` with fail-closed for all categories
3. Updated `run()` to use new validation (step: `validate_steward_targets`)
4. Evidence now includes `classified_paths` dict with all three category lists

### test_missions_phase3.py

1. Renamed `TestStewardOpenCodeEnforcement` → `TestStewardTargetValidation`
2. Removed `test_steward_allows_out_of_envelope_changes` (incorrect!)
3. Added `test_steward_blocks_protected_roots` (category B)
4. Added `test_steward_blocks_disallowed_paths` (category C)
5. Added `test_steward_succeeds_with_empty_artifact_list` (only allowed case)
6. Updated `test_steward_rejects_payload_handler_override` to expect FAIL
7. Updated `test_path_classification_all_categories` to use `_classify_path`

---

## 5. Test Output (verbatim)

```
============================= test session starts =============================
platform win32 -- Python 3.12.6, pytest-8.3.4, pluggy-1.5.0
collected 47 items

runtime/tests/test_missions_phase3.py::TestMissionType::test_all_types_defined PASSED
runtime/tests/test_missions_phase3.py::TestMissionType::test_string_enum PASSED
runtime/tests/test_missions_phase3.py::TestMissionRegistry::test_contains_all_mission_types PASSED
runtime/tests/test_missions_phase3.py::TestMissionRegistry::test_get_mission_class_valid PASSED
runtime/tests/test_missions_phase3.py::TestMissionRegistry::test_get_mission_class_unknown_fails_closed PASSED
runtime/tests/test_missions_phase3.py::TestMissionRegistry::test_run_mission_unknown_fails_closed PASSED
runtime/tests/test_missions_phase3.py::TestMissionRegistry::test_list_mission_types_deterministic PASSED
runtime/tests/test_missions_phase3.py::TestSchemaValidation::test_load_schema_succeeds PASSED
runtime/tests/test_missions_phase3.py::TestSchemaValidation::test_valid_definition_passes PASSED
runtime/tests/test_missions_phase3.py::TestSchemaValidation::test_missing_required_field_fails PASSED
runtime/tests/test_missions_phase3.py::TestSchemaValidation::test_invalid_type_enum_fails PASSED
runtime/tests/test_missions_phase3.py::TestSchemaValidation::test_error_messages_sorted PASSED
runtime/tests/test_missions_phase3.py::TestDesignMission::test_mission_type PASSED
runtime/tests/test_missions_phase3.py::TestDesignMission::test_valid_inputs_pass PASSED
runtime/tests/test_missions_phase3.py::TestDesignMission::test_missing_task_spec_fails PASSED
runtime/tests/test_missions_phase3.py::TestDesignMission::test_run_succeeds PASSED
runtime/tests/test_missions_phase3.py::TestDesignMission::test_run_fails_when_packet_missing PASSED
runtime/tests/test_missions_phase3.py::TestDesignMission::test_run_fails_when_packet_invalid PASSED
runtime/tests/test_missions_phase3.py::TestDesignMission::test_run_with_context_refs PASSED
runtime/tests/test_missions_phase3.py::TestReviewMission::test_mission_type PASSED
runtime/tests/test_missions_phase3.py::TestReviewMission::test_valid_inputs_pass PASSED
runtime/tests/test_missions_phase3.py::TestReviewMission::test_missing_subject_packet_fails PASSED
runtime/tests/test_missions_phase3.py::TestReviewMission::test_invalid_review_type_fails PASSED
runtime/tests/test_missions_phase3.py::TestReviewMission::test_run_succeeds PASSED
runtime/tests/test_missions_phase3.py::TestBuildMission::test_mission_type PASSED
runtime/tests/test_missions_phase3.py::TestBuildMission::test_valid_inputs_pass PASSED
runtime/tests/test_missions_phase3.py::TestBuildMission::test_unapproved_fails PASSED
runtime/tests/test_missions_phase3.py::TestBuildMission::test_run_succeeds PASSED
runtime/tests/test_missions_phase3.py::TestStewardMission::test_mission_type PASSED
runtime/tests/test_missions_phase3.py::TestStewardMission::test_valid_inputs_pass PASSED
runtime/tests/test_missions_phase3.py::TestStewardMission::test_unapproved_fails PASSED
runtime/tests/test_missions_phase3.py::TestStewardMission::test_run_succeeds PASSED
runtime/tests/test_missions_phase3.py::TestStewardMission::test_run_fails_with_deterministic_error PASSED
runtime/tests/test_missions_phase3.py::TestStewardTargetValidation::test_steward_blocks_in_envelope_docs_without_opencode PASSED
runtime/tests/test_missions_phase3.py::TestStewardTargetValidation::test_steward_blocks_protected_roots PASSED
runtime/tests/test_missions_phase3.py::TestStewardTargetValidation::test_steward_blocks_disallowed_paths PASSED
runtime/tests/test_missions_phase3.py::TestStewardTargetValidation::test_steward_succeeds_with_empty_artifact_list PASSED
runtime/tests/test_missions_phase3.py::TestStewardTargetValidation::test_steward_rejects_payload_handler_override PASSED
runtime/tests/test_missions_phase3.py::TestStewardTargetValidation::test_path_classification_all_categories PASSED
runtime/tests/test_missions_phase3.py::TestAutonomousBuildCycleMission::test_mission_type PASSED
runtime/tests/test_missions_phase3.py::TestAutonomousBuildCycleMission::test_valid_inputs_pass PASSED
runtime/tests/test_missions_phase3.py::TestAutonomousBuildCycleMission::test_run_composes_correctly PASSED
runtime/tests/test_missions_phase3.py::TestAutonomousBuildCycleMission::test_run_full_cycle_success PASSED
runtime/tests/test_missions_phase3.py::TestMissionResultSerialization::test_to_dict_deterministic PASSED
runtime/tests/test_missions_phase3.py::TestMissionResultSerialization::test_to_dict_consistent PASSED
runtime/tests/test_missions_phase3.py::TestEngineMissionDispatch::test_design_mission_via_registry PASSED
runtime/tests/test_missions_phase3.py::TestEngineMissionDispatch::test_unknown_mission_fails_closed PASSED

======================== 47 passed, 1 warning in 1.84s ========================
```

---

## 6. File Hashes (SHA-256, full, no truncation)

| File | SHA-256 |
|------|---------|
| runtime/orchestration/missions/steward.py | 9e09aed101846a5cfe21abddbb376acc860762141b08e0f35838898cc787d27a |
| runtime/tests/test_missions_phase3.py | 54712f675ea055d1bc99315822d99f5871f07e1aa2eee62da9e5cf3802e29a3a |

---

## 7. Done Criteria Check

| Criterion | Status |
|-----------|--------|
| A/B/C classification defined | ✓ PASS |
| Protected roots blocked | ✓ PASS |
| Disallowed paths blocked | ✓ PASS |
| Only empty artifact list allowed | ✓ PASS |
| Incorrect tests replaced | ✓ PASS |
| Pytest 47/47 PASS | ✓ PASS |

---

**END OF REVIEW PACKET**
