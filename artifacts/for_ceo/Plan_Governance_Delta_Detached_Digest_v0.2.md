---
artifact_id: "abe4774f-8914-4a70-87af-49bd3770f5c7"
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: "2026-01-06T20:15:00+11:00"
author: "Antigravity"
version: "0.2"
status: "PENDING_REVIEW"
parent_artifact: "artifacts/plans/Plan_Governance_Delta_Detached_Digest_v0.1.md"
mission_ref: "Governance_Delta_Detached_Digest"
council_trigger: "CT-2"
tags: [governance, g-cbs, detached-digest, attestation, activation]
---

# Plan: Governance Delta — Detached Digest + Two-Part Attestation (v0.2)

## Executive Summary

This plan formalizes Detached Digest mode and the Two-Part Attestation Model for G-CBS closure bundles. v0.2 fixes issues identified in v0.1 review:
1. Authority & Activation chain via expanded `ARTEFACT_INDEX.json` (now v3.0.0)
2. Correct provenance fields pointing to the activation index
3. Explicit validator semantics and deterministic error codes
4. Backward compatibility policy for role rename
5. Manual verification removed from DONE criteria

## Problem Statement

Same as v0.1, plus:
- No formal "activated protocols" index existed. Now resolved via `ARTEFACT_INDEX.json` v3.0.0 expansion.

---

## Authority & Activation (P1 Fix)

### Protocol Canon Location

| Layer | Path | Status |
|-------|------|--------|
| **Activation Index** | `docs/01_governance/ARTEFACT_INDEX.json` | **CANONICAL** (v3.0.0) |
| **G-CBS Standard** | `docs/02_protocols/G-CBS_Standard_v1.0.md` | To be created (becomes binding via index entry) |

### How Protocols Become Binding

1. A protocol is **BINDING** when listed in `ARTEFACT_INDEX.json` under the `artefacts` key.
2. New protocols must be added to the index with their repo-relative path.
3. The index is versioned (meta.version) and timestamped (meta.updated).
4. Fail-closed: If activation status is ambiguous, produce BLOCKED + Context Pack.

---

## Proposed Changes

### Component 1: Protocol Documentation

#### [NEW] `docs/02_protocols/G-CBS_Standard_v1.0.md`
Canonical G-CBS specification with:
- §1 Overview
- §2 Detached Digest Mode (marker, sidecar format, validator requirements)
- §3 Two-Part Attestation Model
- §4 Evidence Roles (`validator_payload_pass`)
- §5 Provenance Fields
- §6 Validator Output Contract
- §7 Deterministic Error Codes

#### [MODIFY] `docs/01_governance/ARTEFACT_INDEX.json`
- ✅ DONE: Expanded to v3.0.0 with 20 binding protocols
- Add: `gcbs_standard` entry for new G-CBS_Standard_v1.0.md

---

### Component 2: Provenance Fields (P2 Fix)

**Manifest/Addendum must include:**

```json
{
  "activated_protocols_ref": "docs/01_governance/ARTEFACT_INDEX.json",
  "activated_protocols_sha256": "<SHA256 of file>",
  "gcbs_standard_ref": "docs/02_protocols/G-CBS_Standard_v1.0.md",
  "gcbs_standard_version": "1.0"
}
```

**Current Index SHA256:** `3BAD376999F8B32CBF6A4FFA5F5274373ACD3876A72225EDA8B1398834403D25`

---

### Component 3: Validator Semantics (P3 Fix)

#### Two-Part Attestation Model

| Attestation | Domain | Evidence |
|-------------|--------|----------|
| **Payload Compliance** | All evidence files per `closure_manifest.json` | Role: `validator_payload_pass` |
| **Container Integrity** | Shipped ZIP bytes | Sidecar verification stdout line |

#### Validator Stdout Contract (Detached Mode)

```
Detached digest mode: true
Sidecar digest path: <path>
Sidecar digest verified: <SHA256>
```

On failure, print error code and exit nonzero.

---

### Component 4: Deterministic Error Codes (P6)

| Code | Condition | Message |
|------|-----------|---------|
| `E_DIGEST_SIDECAR_MISSING` | Sidecar file not found | `Sidecar not found: {path}` |
| `E_DIGEST_SIDECAR_MALFORMED` | Invalid sidecar format | `Malformed sidecar: {detail}` |
| `E_DIGEST_MISMATCH` | Hash mismatch | `Digest mismatch: expected {exp}, got {act}` |
| `E_REQUIRED_EVIDENCE_MISSING` | Missing evidence role | `Missing evidence: {role}` |
| `E_ROLE_DEPRECATED` | Legacy role used (compat) | `WARN: Deprecated role {old}, use {new}` |
| `E_PROTOCOLS_PROVENANCE_MISSING` | Provenance fields missing | `Missing: activated_protocols_ref` |

---

### Component 5: Backward Compatibility (P5 Fix)

**Policy: Option B (Compatibility Window)**

| Old Role | New Role | Behavior |
|----------|----------|----------|
| `validator_final_shipped` | `validator_payload_pass` | Accept both; emit warning for old |

**Cutoff:** v1.3.0 — after which old role will be rejected.

---

### Component 6: Manual Verification (P4 Fix)

> [!IMPORTANT]
> Manual verification is **OPTIONAL** and **NON-AUTHORITATIVE**.
> DONE criteria are **ONLY** machine-checkable gates:
> - Validator PASS
> - Tests PASS
> - Provenance hash match

---

## Verification Plan

### Automated Tests (Authoritative)
```bash
pytest tests_doc/test_tdd_compliance.py
pytest scripts/closure/tests/
python tools/validate_governance_index.py
```

### Manual Verification (Non-Authoritative, Optional)
- Visual inspection of bundle contents

---

## DONE Definition

DONE when ALL of the following pass:
1. [ ] `G-CBS_Standard_v1.0.md` created and listed in `ARTEFACT_INDEX.json`
2. [ ] Validator prints explicit sidecar verification lines
3. [ ] Error codes are deterministic per table above
4. [ ] Provenance fields included in manifest
5. [ ] `validator_payload_pass` role accepted (compat: old role warns)
6. [ ] `pytest tests_doc/test_tdd_compliance.py` PASS
7. [ ] `pytest scripts/closure/tests/` PASS
8. [ ] `python tools/validate_governance_index.py` PASS

---

## Non-Goals

- Changing ZIP determinism mechanics
- Broadening to unrelated protocol changes
- Manual verification as authoritative gate
