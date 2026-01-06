---
artifact_id: ""              # [REQUIRED] Generate UUID v4
artifact_type: "PLAN"
schema_version: "1.0.0"
created_at: ""               # [REQUIRED] ISO 8601
author: "Antigravity"
version: "0.1"
status: "DRAFT"

# Optional
chain_id: ""
mission_ref: ""
council_trigger: ""          # CT-1 through CT-5 if applicable
parent_artifact: ""
tags: []
---

# <Topic> — Implementation Plan

| Field | Value |
|-------|-------|
| **Version** | 0.1 |
| **Date** | YYYY-MM-DD |
| **Author** | Antigravity |
| **Status** | DRAFT — Awaiting CEO Review |
| **Council Trigger** | <!-- CT-1..CT-5 or "None" --> |

---

## Executive Summary

<!-- 2-5 sentences summarizing the goal and approach -->

---

## Problem Statement

<!-- What problem does this solve? Why is it important? -->

---

## Proposed Changes

### Component 1: <Name>

#### [NEW] [filename](file:///path/to/file)

<!-- Description of changes -->

---

### Component 2: <Name>

#### [MODIFY] [filename](file:///path/to/file)

<!-- Description of changes -->

---

## Verification Plan

### Automated Tests

| Test | Command | Expected |
|------|---------|----------|
| <!-- Test name --> | `<!-- command -->` | <!-- expected outcome --> |

### Manual Verification

1. <!-- Step 1 -->
2. <!-- Step 2 -->

---

<!-- ============ OPTIONAL SECTIONS BELOW ============ -->

## User Review Required

> [!IMPORTANT]
> <!-- Key decisions requiring CEO input -->

### Key Decisions Needed

1. <!-- Decision 1 -->
2. <!-- Decision 2 -->

---

## Alternatives Considered

| Alternative | Pros | Cons | Rejection Reason |
|-------------|------|------|------------------|
| <!-- Alt 1 --> | <!-- pros --> | <!-- cons --> | <!-- why rejected --> |

---

## Rollback Plan

If this plan fails:

1. <!-- Rollback step 1 -->
2. <!-- Rollback step 2 -->

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| <!-- Criterion 1 --> | <!-- How measured --> |

---

## Non-Goals

- <!-- Explicit exclusion 1 -->
- <!-- Explicit exclusion 2 -->

---

*This plan was drafted by Antigravity under LifeOS Build Artifact Protocol v1.0.*
