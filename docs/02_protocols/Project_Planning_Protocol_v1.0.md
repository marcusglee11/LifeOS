# Implementation Plan Protocol v1.0

**Status**: Active
**Authority**: Gemini System Protocol
**Version**: 1.0
**Effective**: 2026-01-12

---

## 1. Purpose

To ensure all build missions in LifeOS are preceded by a structured, schema-compliant Implementation Plan
that can be parsed, validated, and executed by automated agents (Recursive Kernel).

## 2. Protocol Requirements

### 2.1 Trigger Condition

ANY "Build" mission (writing code, changing configuration, infrastructure work) MUST start with the
creation (or retrieval) of an Implementation Plan.

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
3. **APPROVED**: User explicitly approves (e.g. "Plan approved").
   ONLY when Status is APPROVED can the Builder proceed to Execution.
4. **OBSOLETE**: Replaced by a newer version.

## 3. Enforcement

### 3.1 AI Agent (Gemini)

- **Pre-Computation**: Before writing code, the Agent MUST check for an APPROVED plan.
- **Self-Correction**: If the user asks to build without a plan, the Agent MUST pause and propose:
  "I need to draft a PLAN first per Protocol v1.0."

### 3.2 Automated Validation

- Future state: `scripts/validate_plan.py` will run in CI/pre-build to reject non-compliant plans.

---

**Template Reference**:
See `docs/02_protocols/implementation_plan_schema_v1.0.yaml` for structural details.

---

## 4. Plan Review Rubric

When a plan is in REVIEW status, evaluate it against these checks before setting status to APPROVED.

| # | Check | Pass criteria |
| --- | --- | --- |
| 1 | Schema compliance | All required sections present and non-empty per §2.3 |
| 2 | Goal clarity | Goals are concrete and testable, not vague |
| 3 | Protected path gate | No edits to protected paths without Council approval noted |
| 4 | Worktree isolation | Plan specifies `start_build.py` before any code changes |
| 5 | Test discipline | Verification plan includes `pytest runtime/tests -q` before AND after |
| 6 | Quality gate | Verification plan includes `quality_gate.py check --scope changed` |
| 7 | Changes completeness | Every file mentioned in body appears in the Proposed Changes table |
| 8 | Failure modes | Risks section covers at least one failure mode per significant change |
| 9 | Rollback viability | Rollback is a concrete procedure, not "revert the commit" alone |
| 10 | Scope discipline | Plan does not include unrequested refactoring beyond stated goals |
| 11 | No bare TODOs | Only `LIFEOS_TODO[P0/P1/P2]` format permitted |
| 12 | Assumptions explicit | Implicit dependencies (external services, timing, model availability) are stated |

Protected paths (check 3): `docs/00_foundations/`, `docs/01_governance/`,
`config/governance/protected_artefacts.json`.

**Verdict levels**:

- **approved** — all checks pass or have minor warnings
- **needs_revision** — one or more checks fail but are fixable
- **blocked** — protected path violation without Council approval, or schema so incomplete execution
  is impossible

For automated or agent-assisted review, use the `/review-plan` Claude Code skill
(`.claude/skills/review-plan/SKILL.md`), which applies this rubric and returns a revised draft.
