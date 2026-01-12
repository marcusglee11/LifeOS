---
artifact_id: ""              # [REQUIRED] Generate UUID v4
artifact_type: "GAP_ANALYSIS"
schema_version: "1.0.0"
created_at: ""               # [REQUIRED] ISO 8601
author: "Antigravity"
version: "0.1"
status: "DRAFT"

# Optional
chain_id: ""
mission_ref: ""
parent_artifact: ""
tags: []
---

# Gap Analysis: <Scope>

**Date:** YYYY-MM-DD
**Author:** Antigravity
**Version:** 0.1

---

## Scope

### Directories Scanned

- `<!-- path/to/dir1 -->`
- `<!-- path/to/dir2 -->`

### Analysis Focus

<!-- What aspects were analyzed (coverage, consistency, completeness, etc.) -->

---

## Findings

| Finding ID | Description | Severity | Location |
|------------|-------------|----------|----------|
| GAP-001 | <!-- Description --> | P1_CRITICAL | `<!-- path:line -->` |
| GAP-002 | <!-- Description --> | P2_MAJOR | `<!-- path:line -->` |
| GAP-003 | <!-- Description --> | P3_MINOR | `<!-- path:line -->` |

### Severity Legend

| Severity | Meaning |
|----------|---------|
| P0_BLOCKER | Must fix before any progress |
| P1_CRITICAL | Must fix before merge/deploy |
| P2_MAJOR | Should fix, may proceed with tracking |
| P3_MINOR | Nice to fix, non-blocking |
| P4_TRIVIAL | Cosmetic/style only |

---

## Remediation Recommendations

### GAP-001: <Title>

**Issue:** <!-- Detailed description -->

**Recommended Fix:**
<!-- How to fix -->

**Effort:** <!-- T-shirt size or hours -->

---

### GAP-002: <Title>

**Issue:** <!-- Detailed description -->

**Recommended Fix:**
<!-- How to fix -->

**Effort:** <!-- T-shirt size or hours -->

---

<!-- ============ OPTIONAL SECTIONS BELOW ============ -->

## Methodology

<!-- How the analysis was performed -->

1. <!-- Step 1 -->
2. <!-- Step 2 -->

---

## Priority Matrix

| Priority | Count | Action |
|----------|-------|--------|
| P0_BLOCKER | 0 | Immediate |
| P1_CRITICAL | <!-- N --> | This sprint |
| P2_MAJOR | <!-- N --> | Next sprint |
| P3_MINOR | <!-- N --> | Backlog |
| P4_TRIVIAL | <!-- N --> | Optional |

---

*This gap analysis was created under LifeOS Build Artifact Protocol v1.0.*
