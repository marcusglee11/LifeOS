---
artifact_id: "aace660e-6fb2-4169-9bd7-99462c647350"
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: "2026-01-06T20:25:00+11:00"
author: "Antigravity"
version: "0.2.1"
status: "SUPERSEDED"
parent_artifact: "artifacts/plans/Plan_Governance_Delta_Detached_Digest_v0.2.md"
mission_ref: "Governance_Delta_Detached_Digest"
council_trigger: "CT-2"
tags: [governance, g-cbs, detached-digest, attestation, activation]
superseded_by: "artifacts/plans/Plan_Governance_Delta_Detached_Digest_v0.2.2.md"
---

# Plan: Governance Delta — Detached Digest + Two-Part Attestation (v0.2.1)

## Executive Summary

v0.2.1 fixes issues in v0.2:
1. **P1:** Binding semantics clarified (artefacts vs protocols)
2. **P2:** Correct count: 17 binding artefacts (9 protocols)
3. **P3:** Cutoff anchor: `G-CBS_Standard_v1.0.md` §7 (compat ends at G-CBS v1.1)
4. **P4:** Hashing policy: raw file bytes (stable formatting enforced)
5. **P5:** Required evidence roles + compat window behavior specified

---

## P1 — Binding Semantics (Fixed)

### Artefact Index Semantics

`docs/01_governance/ARTEFACT_INDEX.json` lists **binding artefacts** across four layers:

| Layer | Binding Class | Description |
|-------|---------------|-------------|
| `00_foundations` | FOUNDATIONAL | Core principles; immutable except via constitutional amendment |
| `01_governance` | GOVERNANCE | Contracts and rulings; CEO-controlled |
| `02_protocols` | PROTOCOL | Active protocols; binding for all agents and runtime |
| `03_runtime` | RUNTIME | Runtime specifications; binding for implementation |

**Key Clarification:**
- All entries in `ARTEFACT_INDEX.json` are **binding artefacts**.
- Only entries under `02_protocols` are **protocols**.
- Protocol binding semantics (validator enforcement, TDD compliance) apply only to `02_protocols` entries.

---

## P2 — Correct Artefact Count (Fixed)

**Actual counts from ARTEFACT_INDEX.json v3.0.0:**

| Layer | Count |
|-------|-------|
| 00_foundations | 3 |
| 01_governance | 4 |
| 02_protocols | 9 |
| 03_runtime | 3 |
| context | 1 |
| **Total** | **17 binding artefacts** |

**Of which:**
- **9 are protocols** (under `02_protocols`)
- **8 are other binding artefacts** (foundations, governance, runtime, context)

---

## P3 — Cutoff Anchor (Fixed)

### Legacy Role Compatibility Window

| Anchor Artefact | Version | Effect |
|-----------------|---------|--------|
| `docs/02_protocols/G-CBS_Standard_v1.0.md` | v1.0 | Legacy role `validator_final_shipped` accepted with warning |
| `docs/02_protocols/G-CBS_Standard_v1.1.md` | v1.1 | Legacy role **rejected** — must use `validator_payload_pass` |

**Enforcement:**
- Validator reads `gcbs_standard_version` from manifest
- If `>= 1.1` AND legacy role present → `E_ROLE_DEPRECATED` (fail)
- If `< 1.1` AND legacy role present → warning, continue

---

## P4 — Hashing Policy (Fixed)

### Policy: Raw File Bytes

| Aspect | Policy |
|--------|--------|
| **Hash Input** | Raw bytes of `ARTEFACT_INDEX.json` as stored on disk |
| **Algorithm** | SHA-256, lowercase hex |
| **Formatting** | File must be deterministically formatted (enforced by `validate_governance_index.py`) |
| **Canonicalization** | None; format is fixed by tool/test enforcement |

**Enforcement:**
- `validate_governance_index.py` computes SHA-256 of raw bytes
- Build/validator compares computed hash to `activated_protocols_sha256` in manifest
- Mismatch → `E_PROTOCOLS_PROVENANCE_MISMATCH` (fail)

**Deterministic Formatting Rules:**
- 4-space indentation
- Keys: double-quoted, sorted alphabetically within each section
- No trailing whitespace
- Final newline required
- UTF-8 encoding, LF line endings

---

## P5 — Required Evidence Roles (Fixed)

### Role Semantics

| Role | Status | Behavior |
|------|--------|----------|
| `validator_payload_pass` | **REQUIRED** (CURRENT) | Attestation of payload compliance |
| `validator_final_shipped` | DEPRECATED (compat window) | Accepted with warning until G-CBS v1.1 |

### Validator Behavior

```
IF neither role present:
  → E_REQUIRED_EVIDENCE_MISSING (exit 1)

IF validator_final_shipped present AND gcbs_version < 1.1:
  → print "WARN: Deprecated role validator_final_shipped, use validator_payload_pass"
  → continue

IF validator_final_shipped present AND gcbs_version >= 1.1:
  → E_ROLE_DEPRECATED (exit 1)

IF validator_payload_pass present:
  → accept (no warning)
```

### Test Matrix

| Test Case | Role Present | gcbs_version | Expected Result |
|-----------|--------------|--------------|-----------------|
| test_missing_role | none | any | FAIL: E_REQUIRED_EVIDENCE_MISSING |
| test_legacy_in_window | validator_final_shipped | 1.0 | PASS + warning |
| test_legacy_after_cutoff | validator_final_shipped | 1.1 | FAIL: E_ROLE_DEPRECATED |
| test_required_role | validator_payload_pass | any | PASS (no warning) |

---

## Updated ARTEFACT_INDEX.json Structure

Update `meta` section to include binding class definitions:

```json
{
  "meta": {
    "version": "3.0.1",
    "updated": "2026-01-06",
    "description": "Canonical Binding Artefacts Index",
    "sha256_policy": "Hash raw file bytes for provenance",
    "binding_classes": {
      "FOUNDATIONAL": "Core principles; immutable except via constitutional amendment",
      "GOVERNANCE": "Contracts and rulings; CEO-controlled amendments",
      "PROTOCOL": "Active protocols; binding for agents and runtime",
      "RUNTIME": "Runtime specifications; binding for implementation"
    }
  },
  "artefacts": { ... }
}
```

---

## Provenance Fields (Updated)

```json
{
  "activated_protocols_ref": "docs/01_governance/ARTEFACT_INDEX.json",
  "activated_protocols_sha256": "<SHA256 of raw bytes>",
  "gcbs_standard_ref": "docs/02_protocols/G-CBS_Standard_v1.0.md",
  "gcbs_standard_version": "1.0"
}
```

---

## DONE Definition (Explicit)

DONE when ALL pass:
1. [ ] Plan v0.2.1 approved
2. [ ] `ARTEFACT_INDEX.json` updated to v3.0.1 with binding classes
3. [ ] Validator implements role compat logic per P5
4. [ ] Test cases per P5 test matrix added and passing
5. [ ] `validate_governance_index.py` prints SHA-256 on success
6. [ ] `pytest tests_doc/test_tdd_compliance.py` PASS
7. [ ] No manual verification in DONE criteria

---

## Non-Goals

- Changing ZIP determinism mechanics
- Broadening to unrelated changes
- Manual verification as authoritative gate
