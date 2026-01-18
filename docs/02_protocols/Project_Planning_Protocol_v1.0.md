# Implementation Plan Protocol v1.0

**Status**: Active  
**Authority**: Gemini System Protocol  
**Version**: 1.0  
**Effective**: 2026-01-12

---

## 1. Purpose

To ensure all build missions in LifeOS are preceded by a structured, schema-compliant Implementation Plan that can be parsed, validated, and executed by automated agents (Recursive Kernel).

## 2. Protocol Requirements

### 2.1 Trigger Condition

ANY "Build" mission (writing code, changing configuration, infrastructure work) MUST start with the creation (or retrieval) of an Implementation Plan.

### 2.2 Naming Convention

Plans must be stored in `artifacts/plans/` and follow the strict naming pattern:
`PLAN_<TaskSlug>_v<Version>.md`

- `<TaskSlug>`: Uppercase, underscore-separated (e.g., `OPENCODE_SANDBOX`, `FIX_CI_PIPELINE`).
- `<Version>`: Semantic version (e.g., `v1.0`, `v1.1`).

### 2.3 Schema Compliance

All plans MUST adhere to `docs/02_protocols/implementation_plan_schema_v1.0.yaml`.
Key sections include:

1. **Header**: Metadata (Status, Version).
2. **Context**: Why we are doing this.
3. **Goals**: Concrete objectives.
4. **Proposed Changes**: Table of files to Create/Modify/Delete.
5. **Verification Plan**: Exact commands to run.
6. **Risks & Rollback**: Safety measures.

### 2.4 Lifecycle

1. **DRAFT**: Agent creates initial plan.
2. **REVIEW**: User (or Architect Agent) reviews.
3. **APPROVED**: User explicitly approves (e.g. "Plan approved"). ONLY when Status is APPROVED can the Builder proceed to Execution.
4. **OBSOLETE**: Replaced by a newer version.

## 3. Enforcement

### 3.1 AI Agent (Gemini)

- **Pre-Computation**: Before writing code, the Agent MUST check for an APPROVED plan.
- **Self-Correction**: If the user asks to build without a plan, the Agent MUST pause and propose: "I need to draft a PLAN first per Protocol v1.0."

### 3.2 Automated Validation

- Future state: `scripts/validate_plan.py` will run in CI/pre-build to reject non-compliant plans.

---
**Template Reference**:
See `docs/02_protocols/implementation_plan_schema_v1.0.yaml` for structural details.
