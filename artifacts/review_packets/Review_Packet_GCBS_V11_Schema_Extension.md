# Review Packet: G-CBS v1.1 Schema Extension

**Mode**: Standard Build  
**Date**: 2026-01-11  
**Files Changed**: 6

---

## Summary

Implemented G-CBS v1.1 additive schema extension conformant with existing G-CBS v1.0 infrastructure. Added `inputs[]`, `outputs[]`, and `verification.gates[]` fields to support Phase 5 automation while maintaining full backward compatibility with all v1.0 bundles.

---

## Issue Catalogue

| ID | Issue | Resolution |
|----|-------|------------|
| P0.1 | Schema extension needed for automation | Created `closure_manifest_v1_1.json` |
| P0.2 | Validator must accept both versions | Updated dispatch logic in validator |
| P0.3 | StepGate profile needs stricter gates | Implemented SG-1/SG-2/SG-3 gates |
| P0.4 | Builder needs v1.1 emission support | Added `--schema-version` and inventory args |
| P0.5 | Tests needed for v1.1 validation | Added 8 new test cases |

---

## Acceptance Criteria

| ID | Criterion | Status |
|----|-----------|--------|
| AC1 | V1.0 bundles validate PASS unchanged | ✅ PASS |
| AC2 | V1.1 bundles with inputs/outputs/gates validate PASS | ✅ PASS |
| AC3 | Tamper tests fail as expected | ✅ PASS |
| AC4 | Registry updated per policy | ✅ PASS |

---

## Non-Goals

- Did NOT replace `closure_manifest.json` naming
- Did NOT introduce `closure.json`
- Did NOT weaken fail-closed semantics
- Did NOT change v1.0 behavior

---

## Evidence

### Pytest (19 passed)

```
python -m pytest scripts/closure/tests/test_gcbs_a1a2_regressions.py -v
19 passed in 3.18s
```

### Manual Bundle Build

```
SUCCESS. Bundle: temp_v11_test/Bundle_GCBS_V11_Test.zip
Audit Status: PASS
schema_version: G-CBS-1.1
```

---

## Appendix: Diff-Based Context

### [NEW] schemas/closure_manifest_v1_1.json (263 lines)

JSON Schema for G-CBS-1.1 with:

- `schema_version`: `"G-CBS-1.1"`
- `inputs[]` array with `artefact_ref` items
- `outputs[]` array with `artefact_ref` items
- `verification.gates[]` array with gate results
- `safe_relative_path` definition (no absolute, no `..`, no backslash)

### [MODIFIED] scripts/closure/validate_closure_bundle.py

```diff
-MANIFEST_SCHEMA_VERSION = "G-CBS-1.0"
+MANIFEST_SCHEMA_VERSIONS = {"G-CBS-1.0", "G-CBS-1.1"}
...
+def validate_v11_fields(manifest):
+    """Validate G-CBS-1.1 specific fields."""
...
+def validate_artefact_ref(item, field_name):
+    """Validate an artefact reference (input or output)."""
...
+def is_unsafe_path(path):
+    """Check if a path is unsafe."""
```

### [MODIFIED] scripts/closure/profiles/step_gate_closure.py

Expanded from 5-line stub to 180+ lines implementing:

- `check_sg1_no_truncation()` - 64-hex SHA enforcement
- `check_sg2_ordering()` - lexicographic array sorting
- `check_sg3_v11_required()` - verification.gates requirement

### [MODIFIED] scripts/closure/build_closure_bundle.py

```diff
+parser.add_argument("--schema-version", choices=["1.0", "1.1"], default="1.0")
+parser.add_argument("--inputs-file", help="...")
+parser.add_argument("--outputs-file", help="...")
+parser.add_argument("--gates-file", help="...")
...
+def load_inventory_file(filepath, field_name):
+def load_gates_file(filepath):
```

### [MODIFIED] scripts/closure/tests/test_gcbs_a1a2_regressions.py

Added `TestGCBS11SchemaExtension` class with 8 tests:

- `test_v10_still_passes_unchanged`
- `test_v11_happy_path_passes`
- `test_sg1_truncated_hash_in_inputs_fails`
- `test_sg2_unsorted_inputs_fails`
- `test_sg3_missing_verification_fails`
- `test_v11_unsafe_path_absolute_fails`
- `test_v11_unsafe_path_parent_traversal_fails`
- `test_v11_hash_mismatch_fails`

### [NEW] docs/02_protocols/G-CBS_Standard_v1.1.md

Full specification document for v1.1 extension including:

- New field definitions
- Path safety constraints
- StepGate profile gates (SG-1, SG-2, SG-3)
- Backward compatibility guarantees
- Builder CLI documentation
