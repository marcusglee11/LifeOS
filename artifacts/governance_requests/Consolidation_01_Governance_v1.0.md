# Council Governance Request: docs/01_governance/ Consolidation

**Request Type:** Protected Directory Modification
**Scope:** docs/01_governance/ (Governance Contracts & Rulings)
**Priority:** P2 (post-consolidation cleanup)
**Date:** 2026-02-15
**Requestor:** Documentation Consolidation (Batch 3)

## Executive Summary

Request Council approval to apply consolidation standards to docs/01_governance/, including version archiving, archive directory renaming, and ARTEFACT_INDEX updates to align with global governance pattern.

## Current State

**File count:** 31 markdown files + ARTEFACT_INDEX.json + _archive/
**Structure:** Has ARTEFACT_INDEX.json (v3.2.0) ✓, has _archive/ subdirectory (non-standard naming)
**Version duplicates detected:**
- Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.0.md / v1.1.md
- Council_Ruling_OpenCode_First_Stewardship_v1.0.md / v1.1.md
- OpenCode_First_Stewardship_Policy_v1.0.md / v1.1.md

**Protection status:** Article XV protected path (requires Council approval for modifications)

## Proposed Changes

### 1. Rename Archive Directory

**Current:** `docs/01_governance/_archive/`
**Proposed:** `docs/01_governance/archive/`

**Rationale:** Aligns with global naming standard (docs/02_protocols/archive/, docs/03_runtime/archive/, docs/99_archive/). Underscore prefix is non-standard.

### 2. Archive Superseded Versions

Create `docs/01_governance/archive/2026-02_versioning/` and archive:
- Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.0.md → superseded by v1.1.md
- Council_Ruling_OpenCode_First_Stewardship_v1.0.md → superseded by v1.1.md
- OpenCode_First_Stewardship_Policy_v1.0.md → superseded by v1.1.md

**Rationale:** v1.1 versions are canonical; v1.0 preserved for historical reference and lineage tracking.

### 3. Update ARTEFACT_INDEX.json

- Add entries for archived versions with supersession chains
- Mark archived files with `superseded_by` field pointing to active v1.1 versions
- Ensure all active files are indexed (orphan detection)

### 4. Archive Structure Compliance

- Ensure archive/ subdirs follow YYYY-MM_topic or YYYY-MM-DD_topic naming (§3.0)
- Add README.md to each dated subdir with disposition table
- Enforce max depth 2

### 5. Historical Rulings Consolidation (Optional)

**Consideration:** Some Council rulings may be historical/superseded. Recommend review of:
- Tier1_Hardening_Council_Ruling_v0.1.md (Tier 1 complete per STATE)
- Tier1_Tier2_Activation_Ruling_v0.2.md (Tiers activated)
- Tier1_Tier2_Conditions_Manifest_FP4x_v0.1.md (conditions met)

**Proposed:** If Council confirms these are superseded by current state, archive to `archive/2026-02_historical_rulings/`

## ARTEFACT_INDEX Schema

**No schema changes proposed.** This request maintains the existing v3.2.0 schema format used in docs/01_governance/ARTEFACT_INDEX.json.

**Optional future enhancement:** If Council desires, could add `status` field (active/superseded/historical) or `category` field (contract/ruling/policy). This would be a global schema change requiring Council approval and propagation to all ARTEFACT_INDEX files.

## Benefits

1. **Naming Consistency:** `archive/` instead of `_archive/` aligns with repo-wide pattern
2. **Version Clarity:** Supersession chains make ruling evolution explicit
3. **Automated Validation:** Structure validators can enforce governance compliance
4. **Historical Preservation:** Archived rulings preserved with context and lineage

## Risks & Mitigations

**Risk:** Renaming `_archive/` to `archive/` could break links
**Mitigation:**
- Global archive link ban already blocks active docs from linking to archived content
- Archive READMEs can link within their own dated subdirs
- Validate with `docs-archive-link-ban-check` before/after

**Risk:** Archiving historical rulings could lose important precedent
**Mitigation:**
- All archived rulings preserved with disposition notes
- ARTEFACT_INDEX maintains lineage
- Archive is immutable (I-ARCHIVE-IMMUTABLE)

## Council Decision Required

**Option A (Full Consolidation):** Approve all proposed changes including historical rulings archive
**Option B (Structure Only):** Approve archive rename + v1.0→v1.1 archiving, defer historical rulings review
**Option C (Defer):** Keep 01_governance/ in current state pending broader review
**Option D (Conditional):** Approve with specified modifications

## Implementation Timeline

If approved: Immediate (part of Batch 3 completion)

## Draft ARTEFACT_INDEX Updates

Attached as reference (see section below for proposed additions to current ARTEFACT_INDEX.json).

### Proposed Additions to artefacts:

```json
{
  "_comment_archived_versions": "=== Archived Versions (superseded) ===",
  "opencode_docsteward_ct2_v10": {
    "path": "docs/01_governance/archive/2026-02_versioning/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.0.md",
    "superseded_by": "docs/01_governance/Council_Ruling_OpenCode_DocSteward_CT2_Phase2_v1.1.md"
  },
  "opencode_first_stewardship_ruling_v10": {
    "path": "docs/01_governance/archive/2026-02_versioning/Council_Ruling_OpenCode_First_Stewardship_v1.0.md",
    "superseded_by": "docs/01_governance/Council_Ruling_OpenCode_First_Stewardship_v1.1.md"
  },
  "opencode_first_stewardship_policy_v10": {
    "path": "docs/01_governance/archive/2026-02_versioning/OpenCode_First_Stewardship_Policy_v1.0.md",
    "superseded_by": "docs/01_governance/OpenCode_First_Stewardship_Policy_v1.1.md"
  }
}
```

---

**Prepared by:** Documentation Consolidation (Batch 3)
**Awaiting Council Ruling**
