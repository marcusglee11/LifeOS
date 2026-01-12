# Review Packet: Post-GO Hardening (v0.1)

**Mission**: Stabilize Raw-Bytes Hashing & Packaging Clarity
**Author**: Antigravity
**Date**: 2026-01-06
**Status**: REVIEW_READY

---

## 1. Summary

This hardening patch addresses two specific audit risks:
1.  **Hash Instability**: Enforces LF line endings for governance indices to prevent cross-platform SHA256 churn.
2.  **Review Clarity**: Explicitly segregates "changed" files from "reference-only" inclusions in the bundle.

---

## 2. P0 — Governance Hashing Stability

### Issue
"Raw bytes" hashing is sensitive to CRLF vs LF. Windows checkouts could accidentally produce different hashes.

### Fix
1.  **.gitattributes**: Enforce `eol=lf` for `docs/01_governance/*.json`.
2.  **Validator**: `tools/validate_governance_index.py` now fails if CRLF is detected.
3.  **Policy**: Updated `ARTEFACT_INDEX.json` text to explicitly specify "LF-normalized bytes".

---

## 3. P2 — Packaging Clarity

The bundle ZIP structure has been updated to prevent confusion about what is being changed.

### Changed Files (Root)
*Apply these changes to the repo.*
- `docs/01_governance/ARTEFACT_INDEX.json`
- `.gitattributes`
- `tools/validate_governance_index.py`
- `scripts/package_audit_fixpack.py`

### Reference Only (`reference_only/`)
*Do NOT apply. Included for context.*
- `G-CBS_Standard_v1.0.md`

---

## 4. Evidence
- **Test Report**: `artifacts/TEST_REPORT_POSTGO_HARDENING_GOV_INDEX_EOL_AND_PACKAGING_v0.1.md`
- **Diff**: `artifacts/PATCH_POSTGO_HARDENING_GOV_INDEX_EOL_AND_PACKAGING_v0.1.diff`

---

## 5. Deliverables

| Artifact | Path |
|----------|------|
| Bundle ZIP | `artifacts/bundles/Bundle_PostGo_Hardening_GovIndex_EOL_v0.1.zip` |
| Unified Diff | `artifacts/PATCH_POSTGO_HARDENING_GOV_INDEX_EOL_AND_PACKAGING_v0.1.diff` |
