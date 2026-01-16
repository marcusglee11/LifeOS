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

## 4. RTR-1.0 — Rewrite Threshold Rule (Reviewer Behavior)

### 4.1 Purpose

When reviewing a plan, if the reviewer discovers multiple P0 invariant violations, incremental fix requests create churn. This rule mandates a full rewrite to eliminate ambiguity.

### 4.2 Rule

1. On **first review pass**, count P0 invariant violations (see §4.3).
2. If **violations >= 2**, reviewer MUST **STOP** issuing incremental fix bullets.
3. Instead, reviewer MUST produce a **full rewritten plan** in "**Plan Normal Form**" (see §4.4).
4. The rewrite MUST preserve stated intent/scope, remove all discretionary branches ("or/if present/unless"), and be presented as the plan to execute "**AS GIVEN**".
5. Reviewer output MUST include:
   - (a) **GO/NO-GO** decision,
   - (b) **Rewritten plan** (full text),
   - (c) Single build-agent instruction: "**Use this plan AS GIVEN.**"

### 4.3 P0 Invariant Violations (Minimum Set)

A P0 invariant violation is any of:

- **Spec Contradiction**: Conflicting definitions across plan sections (e.g., digest scope conflicts).
- **Multiple Algorithms/Paths**: "X or Y" without binding precedence or single-choice resolution.
- **Required/Optional Ambiguity**: "Required if present" or similar conditional required status.
- **Naming/Token Drift**: Filenames, IDs, or literal tokens inconsistent across sections.
- **Capability Mismatch**: A check requires an input that the validator/driver does not accept.
- **Outcome Taxonomy Mismatch**: e.g., "BLOCK" required but output schema only allows "PASS/FAIL".

### 4.4 Plan Normal Form (Template)

When RTR-1.0 triggers, use this skeleton:

```markdown
# [Title] — Plan Normal Form
Date: YYYY-MM-DD | Status: USE AS GIVEN

## 1. Goal
[1-3 sentence description of desired outcome]

## 2. Scope / Non-goals
- **Scope**: [What is included]
- **Non-goals**: [What is explicitly excluded]

## 3. Hard Contracts (Single-Choice Invariants)
### 3.1 [Contract Name]
- [Single deterministic rule, no "or"]
### 3.2 [Contract Name]
- [Single deterministic rule, no "or"]
[... repeat as needed]

## 4. Inputs / Outputs
### 4.1 Inputs
- [List of required inputs with exact names/schemas]
### 4.2 Outputs
- [List of outputs with exact schemas]

## 5. File Partition
### 5.1 REQUIRED (Missing = FAIL)
- `filename1`
- `filename2`
### 5.2 OPTIONAL (Missing = SKIP Check)
- `filename3`

## 6. Idempotence
- **Algorithm**: [Single algorithm, e.g., SHA256]
- **Input Set**: [Explicit list of files included in digest]
- **Excludes**: [Explicit list of files excluded]
- **Skip Rule**: [Exact condition for skip, e.g., "prior PASS + digest match"]

## 7. Waiver-Only Skips
- **Binding**: [Exact field/path for waiver lookup]
- **Fail-Closed**: [What happens if waiver missing/invalid]

## 8. Check Registry
| ID | Category | Status | Description |
|----|----------|--------|-------------|
| CHK-001 | [Cat] | Required | [Description] |
[... repeat as needed]

## 9. Evidence Requirements
- [Exact logs/outputs required]

## 10. DONE Definition
- [Bullet list of acceptance criteria]
```

---
**Template Reference**:
See `docs/02_protocols/implementation_plan_schema_v1.0.yaml` for structural details.
