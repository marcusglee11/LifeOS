---
artifact_id: "c56ec75a-c88d-49c9-a8dc-97eb3cd018a4"
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: "2026-01-06T20:35:00+11:00"
author: "Antigravity"
version: "0.2.2"
status: "PENDING_REVIEW"
parent_artifact: "artifacts/plans/Plan_Governance_Delta_Detached_Digest_v0.2.1.md"
mission_ref: "Governance_Delta_Detached_Digest"
council_trigger: "CT-2"
tags: [governance, g-cbs, detached-digest, attestation, tightening]
---

# Plan: Governance Delta — Detached Digest + Two-Part Attestation (v0.2.2)

## Executive Summary

v0.2.2 applies 4 tightening fixes to v0.2.1:
1. **P1:** Negative test for provenance hash mismatch
2. **P2:** Negative test for missing `gcbs_standard_version`
3. **P3:** Clarification of `gcbs_standard_version` source-of-truth
4. **P4:** Clarification of key ordering scope

---

## P1 — Negative Test: Provenance Hash Mismatch (Added)

**Test:** `test_provenance_hash_mismatch_fails`
- Manifest contains wrong `activated_protocols_sha256`
- Expected: Validator fails with `E_PROTOCOLS_PROVENANCE_MISMATCH`
- Location: `scripts/closure/tests/test_gcbs_a1a2_regressions.py`

---

## P2 — Negative Test: Missing gcbs_standard_version (Added)

**Test:** `test_missing_gcbs_standard_version_fails_closed`
- Manifest omits `gcbs_standard_version` entirely
- Expected: Validator fails with `E_GCBS_STANDARD_VERSION_MISSING`
- Location: `scripts/closure/tests/test_gcbs_a1a2_regressions.py`

---

## P3 — `gcbs_standard_version` Source-of-Truth (Clarified)

### Source-of-Truth Statement

| Aspect | Policy |
|--------|--------|
| **Writer** | Builder (`build_closure_bundle.py`) writes `gcbs_standard_version` |
| **Verifier** | Validator reads and enforces; fails if missing |
| **Derivation** | Value comes from the profile version in `build_closure_bundle.py` (not derived from index) |
| **Authority** | The manifest value is authoritative; validator does not re-derive |

**Enforcement:**
```
IF gcbs_standard_version missing from manifest:
  → E_GCBS_STANDARD_VERSION_MISSING (exit 1)

IF gcbs_standard_version present:
  → Use for cutoff logic (legacy role compat)
```

---

## P4 — Key Ordering Scope (Clarified)

### ARTEFACT_INDEX.json Key Ordering

| Scope | Rule |
|-------|------|
| **Within `meta`** | Keys in natural order (version, updated, description, sha256_policy, binding_classes) |
| **Within `artefacts`** | `_comment_*` keys appear immediately before their section's artefacts; artefacts sorted lexicographically within section |
| **Sections** | Sections follow directory order: `00_foundations` → `01_governance` → `02_protocols` → `03_runtime` → context |

**Example:**
```json
{
  "artefacts": {
    "_comment_foundations": "=== 00_foundations ===",
    "anti_failure": "...",
    "architecture_skeleton": "...",
    "constitution": "...",
    "_comment_governance": "=== 01_governance ===",
    ...
  }
}
```

**Note:** Current file follows this convention. No structural change required.

---

## Tests Added

| Test | File | Purpose |
|------|------|---------|
| `test_provenance_hash_mismatch_fails` | `test_gcbs_a1a2_regressions.py` | Fail on wrong SHA256 |
| `test_missing_gcbs_standard_version_fails_closed` | `test_gcbs_a1a2_regressions.py` | Fail-closed on missing version |

---

## DONE Definition

DONE when ALL pass:
1. [x] `test_provenance_hash_mismatch_fails` added
2. [x] `test_missing_gcbs_standard_version_fails_closed` added
3. [x] `gcbs_standard_version` source-of-truth documented
4. [x] Key ordering scope documented
5. [ ] `pytest tests_doc/test_tdd_compliance.py` PASS
6. [ ] `pytest scripts/closure/tests/` PASS (or document expected failures pending validator update)
