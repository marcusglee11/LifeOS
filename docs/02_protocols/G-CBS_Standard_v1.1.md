# Generic Closure Bundle Standard (G-CBS) v1.1

| Field | Value |
|-------|-------|
| **Version** | 1.1 |
| **Date** | 2026-01-11 |
| **Author** | Antigravity |
| **Status** | DRAFT |
| **Governance** | CT-2 Council Review Required for Activation |
| **Supersedes** | G-CBS v1.0 (backward compatible) |

---

## 1. Overview

G-CBS v1.1 is a **strictly additive extension** of G-CBS v1.0. All v1.0 bundles remain valid. This version adds structured fields for inputs, outputs, and verification gate results to support Phase 5 automation (task intake, replay, audit).

**Authority:** This protocol becomes binding when (1) approved via CT-2 council review and (2) listed in `docs/01_governance/ARTEFACT_INDEX.json`.

---

## 2. New Fields (v1.1 Extensions)

### 2.1 inputs[]

| Aspect | Specification |
|--------|---------------|
| **Purpose** | Explicit list of input artefacts consumed by the closure |
| **Type** | Array of artefact references |
| **Required** | No (backward compatible) |
| **Ordering** | Sorted by `path` lexicographically (SG-2) |

Each input item:

```json
{
  "path": "specs/requirement.md",
  "sha256": "<64-hex-uppercase>",
  "role": "spec|context|config|other"
}
```

### 2.2 outputs[]

| Aspect | Specification |
|--------|---------------|
| **Purpose** | Explicit list of output artefacts produced by the closure |
| **Type** | Array of artefact references |
| **Required** | No (backward compatible) |
| **Ordering** | Sorted by `path` lexicographically (SG-2) |

Each output item:

```json
{
  "path": "artifacts/bundle.zip",
  "sha256": "<64-hex-uppercase>",
  "role": "artifact|report|code|other"
}
```

### 2.3 verification.gates[]

| Aspect | Specification |
|--------|---------------|
| **Purpose** | Structured verification gate results |
| **Type** | Object with `gates` array |
| **Required** | Required for `schema_version: "G-CBS-1.1"` under StepGate profile (SG-3) |
| **Ordering** | `gates[]` sorted by `id`, `evidence_paths[]` sorted lexicographically (SG-2) |

Each gate item:

```json
{
  "id": "G1_TDD_COMPLIANCE",
  "status": "PASS|FAIL|SKIP|WAIVED",
  "command": "pytest tests/",
  "exit_code": 0,
  "evidence_paths": ["evidence/pytest_output.txt"]
}
```

---

## 3. Path Safety Constraints

All `path` fields in `inputs[]`, `outputs[]`, and `verification.gates[].evidence_paths[]` must be **safe relative paths**:

| Constraint | Description |
|------------|-------------|
| No absolute paths | Path must not start with `/` |
| No drive prefixes | Path must not contain `:` at position 1 (e.g., `C:`) |
| No parent traversal | Path must not contain `..` |
| No backslashes | Path must use forward slashes only |

Violation triggers: `V11_UNSAFE_PATH` failure.

---

## 4. StepGate Profile Gates

When profile is `step_gate_closure`, these additional gates apply:

| Gate ID | Description | Scope |
|---------|-------------|-------|
| **SG-1** | No Truncation | All SHA256 fields must be exactly 64 hex characters (except `DETACHED_SEE_SIBLING_FILE` sentinel) |
| **SG-2** | Deterministic Ordering | All arrays (`inputs`, `outputs`, `evidence`, `verification.gates`, nested `evidence_paths`) must be sorted |
| **SG-3** | Required V1.1 Fields | `verification.gates` must be present and array-typed for `schema_version: "G-CBS-1.1"` |

---

## 5. Schema Version Dispatch

The validator accepts both versions:

| `schema_version` | Behavior |
|------------------|----------|
| `G-CBS-1.0` | Validate against v1.0 schema; skip v1.1 field validation |
| `G-CBS-1.1` | Validate against v1.1 schema; enforce v1.1 fields and SG-3 |

---

## 6. Backward Compatibility

| Aspect | Guarantee |
|--------|-----------|
| **V1.0 bundles** | All valid G-CBS-1.0 bundles pass validation unchanged |
| **New fields** | `inputs[]`, `outputs[]`, `verification` are optional in v1.0 |
| **Profile gates** | StepGate gates only fire when profile matches |

---

## 7. Builder Support

The builder (`scripts/closure/build_closure_bundle.py`) supports v1.1 via:

```bash
python scripts/closure/build_closure_bundle.py \
  --profile step_gate_closure \
  --schema-version 1.1 \
  --inputs-file inputs.txt \
  --outputs-file outputs.txt \
  --gates-file gates.json \
  --deterministic \
  --output bundle.zip
```

| Argument | Format |
|----------|--------|
| `--inputs-file` | One line per entry: `path|sha256|role` |
| `--outputs-file` | One line per entry: `path|sha256|role` |
| `--gates-file` | JSON array of gate objects |

For `--schema-version 1.1` + `step_gate_closure` profile: at least one of `--inputs-file` or `--outputs-file` is required (fail-closed, no heuristics).

---

## 8. Implementation Files

| Component | Path |
|-----------|------|
| **V1.1 Schema** | `schemas/closure_manifest_v1_1.json` |
| **Validator** | `scripts/closure/validate_closure_bundle.py` |
| **StepGate Profile** | `scripts/closure/profiles/step_gate_closure.py` |
| **Builder** | `scripts/closure/build_closure_bundle.py` |
| **Tests** | `scripts/closure/tests/test_gcbs_a1a2_regressions.py` |

---

## 9. Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-06 | Initial release |
| 1.1 | 2026-01-11 | Added `inputs[]`, `outputs[]`, `verification.gates[]`; SG-1/SG-2/SG-3 gates |

---

*This protocol was created under LifeOS governance. Changes require Council review (CT-2).*
