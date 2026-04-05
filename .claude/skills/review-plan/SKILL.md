---
name: review-plan
description: Review any LifeOS implementation plan (Markdown or YAML BUILD_PACKET). Applies the LifeOS plan review rubric, emits a structured verdict with findings, and returns a revised draft inline without overwriting the source.
---

# Review Plan

Critique a LifeOS plan artifact and return a structured review with a revised draft.

Use for:
- Implementation plans in `artifacts/plans/` (`PLAN_<Slug>_v<Version>.md`)
- Pasted plan text before it is saved
- YAML BUILD_PACKET artifacts from the designer role
- Any draft plan shared for review before APPROVED status

## Inputs

The user will provide one of:
- A file path (e.g., `artifacts/plans/PLAN_FOO_v1.0.md`)
- Pasted plan text
- A BUILD_PACKET YAML block

If a file path is given, read it first.

## Step 1: Identify Plan Type

- **Markdown implementation plan** — has `PLAN_` filename pattern or contains a Header section with status/version fields
- **BUILD_PACKET YAML** — has `packet_type:` or `task_id:` at the root
- **Freeform draft** — anything else; treat as Markdown plan

## Step 2: Schema Compliance Check (Markdown plans only)

Validate against `docs/02_protocols/schemas/implementation_plan_schema_v1.0.yaml`.

Required sections:
- **Header**: title, status (`DRAFT|FINAL|APPROVED|OBSOLETE`), version (`X.Y`), authors
- **Context**: background and motivation (min 50 chars)
- **Goals**: at least one bullet-point objective
- **Proposed Changes**: markdown table with columns `file | operation | description`; allowed operations: `CREATE | MODIFY | DELETE | RENAME`
- **Verification Plan**: must include automated tests AND manual verification subsections
- **Risks**: potential issues and mitigations
- **Rollback**: how to revert if the build fails

Flag any missing or empty section as a schema violation.

## Step 3: Apply LifeOS Review Rubric

Work through each item. Mark each as `pass`, `warn`, or `fail`.

| # | Check | Pass criteria |
|---|-------|--------------|
| 1 | **Schema compliance** | All required sections present and non-empty |
| 2 | **Goal clarity** | Goals are concrete and testable, not vague ("improve X") |
| 3 | **Protected path gate** | Plan does not touch `docs/00_foundations/`, `docs/01_governance/`, or `config/governance/protected_artefacts.json` without noting Council approval is required |
| 4 | **Worktree isolation** | Plan specifies `start_build.py` or equivalent worktree creation before any code changes |
| 5 | **Test discipline** | Verification plan includes `pytest runtime/tests -q` before AND after changes |
| 6 | **Quality gate** | Verification plan includes `python3 scripts/workflow/quality_gate.py check --scope changed --json` |
| 7 | **Proposed changes completeness** | Every file mentioned in the plan body appears in the Proposed Changes table |
| 8 | **Failure modes** | Risks section addresses at least one failure mode per significant change |
| 9 | **Rollback viability** | Rollback is a concrete procedure, not "revert the commit" alone |
| 10 | **Scope discipline** | Plan does not include unrequested refactoring or improvements beyond stated goals |
| 11 | **No bare TODOs** | No `TODO`, `FIXME`, `HACK`, or `XXX` — only `LIFEOS_TODO[P0|P1|P2]` |
| 12 | **Assumptions explicit** | Implicit assumptions (external dependencies, model availability, timing) are stated |

For BUILD_PACKET YAML: skip checks 1–2; apply checks 3, 4, 7–12 adapted to packet fields.

## Step 4: Identify Missing Decisions

List any decisions the plan defers or leaves ambiguous that would block execution. Examples:
- Schema not specified for a new data structure
- Which agent role executes which step
- Error handling strategy not chosen

## Step 5: Emit Output

Use this exact structure. Do not omit any section.

---

**Plan Reviewed**: `<filename or "pasted plan">`

**Verdict**: `approved` | `needs_revision` | `blocked`

- `approved` — all rubric items pass or warn with minor notes
- `needs_revision` — one or more `fail` items that are fixable
- `blocked` — protected path violation without Council approval, or schema so incomplete execution is impossible

**Findings**:
| # | Check | Status | Detail |
|---|-------|--------|--------|
| 1 | Schema compliance | pass/warn/fail | ... |
| ... | | | |

**Missing Decisions**:
- (list, or "none")

**Assumptions**:
- (list implicit assumptions found, or "none")

**Revised Draft**:

> Return a complete rewritten version of the plan with all findings addressed.
> For plans larger than ~300 lines, offer to write the draft to `artifacts/plans/<original_name>_revised.md` instead of inlining it.

---

## Defaults

- Never overwrite the source plan. Return the revised draft in the response only, unless the user explicitly asks to save it.
- The rubric is LifeOS-specific. Do not apply generic software review criteria that conflict with LifeOS conventions (e.g., do not flag worktree isolation as "unnecessary overhead").
- For freeform drafts that don't yet follow the schema, note the schema violations but still provide a revised draft that brings the plan into compliance.
