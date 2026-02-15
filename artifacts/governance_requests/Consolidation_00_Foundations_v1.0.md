# Council Governance Request: docs/00_foundations/ Consolidation

**Request Type:** Protected Directory Modification
**Scope:** docs/00_foundations/ (Constitution & Architecture)
**Priority:** P2 (post-consolidation cleanup)
**Date:** 2026-02-15
**Requestor:** Documentation Consolidation (Batch 3)

## Executive Summary

Request Council approval to apply consolidation standards to docs/00_foundations/, including version archiving, ARTEFACT_INDEX creation, and structure alignment with the global archive governance pattern established in Batches 1A-2.

## Current State

**File count:** 13 markdown files (no archive/ subdirectory)
**Structure:** Flat directory, no ARTEFACT_INDEX.json
**Version duplicates detected:**
- ARCH_LifeOS_Operating_Model_v0.3.md
- ARCH_LifeOS_Operating_Model_v0.4.md

**Protection status:** Article XV protected path (requires Council approval for modifications)

## Proposed Changes

### 1. Create ARTEFACT_INDEX.json

Add ARTEFACT_INDEX.json following the schema established in docs/01_governance/ARTEFACT_INDEX.json (v3.2.0 format).

**Proposed entries (13 active files):**
- LifeOS_Constitution_v2.0.md (canonical)
- Anti_Failure_Operational_Packet_v0.1.md
- Architecture_Skeleton_v1.0.md
- Tier_Definition_Spec_v1.1.md
- QUICKSTART.md
- LifeOS_Overview.md
- lifeos-maximum-vision.md
- lifeos-agent-architecture.md
- ARCH_Builder_North-Star_Operating_Model_v0.5.md
- ARCH_Future_Build_Automation_Operating_Model_v0.2.md
- ARCH_LifeOS_Operating_Model_v0.4.md (keep latest)
- SPEC-001_ LifeOS Operating Model - Agentic Platform & Evaluation Framework.md

### 2. Archive Superseded Versions

Create `docs/00_foundations/archive/2026-02_versioning/` and archive:
- ARCH_LifeOS_Operating_Model_v0.3.md → superseded by v0.4.md

**Rationale:** v0.4 is more recent; v0.3 preserved for historical reference.

### 3. Structure Alignment

- Create `archive/` subdirectory with dated subdirs per §3.0 naming standard
- Add archive README with disposition table
- Ensure max depth 2 compliance

## No Schema Changes Proposed

This request does NOT propose any schema changes to ARTEFACT_INDEX format. Uses existing v3.2.0 schema from docs/01_governance/ as template.

## Benefits

1. **Consistency:** Aligns 00_foundations/ with governance pattern from 02_protocols/, 03_runtime/
2. **Orphan Detection:** ARTEFACT_INDEX enables automated detection of undocumented files
3. **Version Clarity:** Supersession chains make version lineage explicit
4. **Immutability:** Archive structure supports I-ARCHIVE-IMMUTABLE invariant

## Risks & Mitigations

**Risk:** Moving Constitution-adjacent files could affect system stability
**Mitigation:** Only archiving v0.3 of a spec (v0.4 remains active); Constitution v2.0 untouched

**Risk:** ARTEFACT_INDEX adds maintenance overhead
**Mitigation:** Automated validators (artefact-index-check) enforce compliance

## Council Decision Required

**Approve:** Proceed with proposed changes (archive v0.3, create ARTEFACT_INDEX, add archive/ structure)
**Approve with Conditions:** Specify constraints or modifications
**Defer:** Wait for future consolidation phase
**Reject:** Keep 00_foundations/ in current state

## Implementation Timeline

If approved: Immediate (part of Batch 3 completion)

---

**Prepared by:** Documentation Consolidation (Batch 3)
**Awaiting Council Ruling**
