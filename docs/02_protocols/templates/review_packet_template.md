---
artifact_id: ""              # [REQUIRED] Generate UUID v4
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
created_at: ""               # [REQUIRED] ISO 8601
author: "Antigravity"
version: "1.0"
status: "PENDING_REVIEW"

# Optional
chain_id: ""
mission_ref: ""
council_trigger: ""
parent_artifact: ""
tags: []
---

# Review_Packet_<Mission>_v1.0

**Mission:** <!-- Mission name -->
**Date:** YYYY-MM-DD
**Author:** Antigravity
**Status:** PENDING_REVIEW

---

## 1. Executive Summary

<!-- 2-5 sentences summarizing mission outcome -->

**Verification Status:**
- **Component Health:** <!-- GREEN/YELLOW/RED (X passed, Y failed) -->
- **Stewardship:** <!-- COMPLETE/PARTIAL/N/A -->

---

## 2. Issue Catalogue & Resolutions

| Issue ID | Description | Resolution | Status |
|----------|-------------|------------|--------|
| <!-- ID --> | <!-- Description --> | <!-- How resolved --> | **RESOLVED** |

---

## 3. Acceptance Criteria Status

| Criteria | Description | Status | Verification Method |
|----------|-------------|--------|---------------------|
| **AT1** | <!-- Criterion --> | **PASS** | <!-- How verified --> |
| **AT2** | <!-- Criterion --> | **PASS** | <!-- How verified --> |

---

## 4. Stewardship Evidence

<!-- Required if any files in docs/ were modified -->

**Objective Evidence of Compliance:**

1. **Documentation Update:**
   - **Command:** `python docs/scripts/generate_strategic_context.py`
   - **Result:** <!-- Success message -->
2. **Files Modified (Verified by Git):**
   - `docs/INDEX.md` (Timestamp update)
   - `docs/LifeOS_Strategic_Corpus.md` (Regeneration)

---

## 5. Verification Proof

**Target Component:** <!-- Component path -->
**Verified Commit:** `<!-- commit hash -->`

**Command:** `<!-- test command -->`
**Output Snapshot:**
```text
<!-- Test output -->
```
**Status:** **<!-- GREEN/YELLOW/RED --> (X Failed)**

---

<!-- ============ OPTIONAL SECTIONS BELOW ============ -->

## 6. Constraints & Boundaries

<!-- If applicable, document runtime limits -->

| Constraint | Limit | Rationale |
|------------|-------|-----------|
| <!-- Name --> | <!-- Value --> | <!-- Why --> |

---

## 7. Non-Goals

- <!-- Explicit exclusion 1 -->
- <!-- Explicit exclusion 2 -->

---

## Appendix — Flattened Code Snapshots

### File: `<!-- path/to/file -->`

```<!-- language -->
<!-- Full file content -->
```

### File: `<!-- path/to/another/file -->`

```<!-- language -->
<!-- Full file content -->
```

---

*This review packet was created under LifeOS Build Artifact Protocol v1.0.*
