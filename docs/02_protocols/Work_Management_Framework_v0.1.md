# Work Management Framework v0.1

<!-- markdownlint-disable MD013 MD040 MD060 -->

**Status**: Active
**Version**: 0.1
**Effective**: 2026-04-27
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0

---

## Purpose

Provides a lightweight repo-backed project management layer for COO-managed work. Uses existing repo surfaces to support intake, prioritisation, dispatch, review, and closure of work items without a PM app, dashboard, or runtime orchestration changes.

---

## Surfaces

| Surface | Role |
|---------|------|
| GitHub issues | Intake and coordination bus |
| `config/tasks/backlog.yaml` | Canonical queue state |
| `docs/11_admin/BACKLOG.md` | Derived, view-only summary (non-canonical) |
| `artifacts/workstreams.yaml` | Workstream taxonomy |
| `docs/02_protocols/Project_Planning_Protocol_v1.0.md` | Planning protocol reference |
| `execution_order.v1` | Dispatch authority |
| Closure evidence | Completion proof |

---

## ID Model

- WMF work items use `id: WI-YYYY-NNN` as the primary identifier.
  - `YYYY` is the 4-digit calendar year.
  - `NNN` is a 3-digit zero-padded sequence number within that year (e.g., `001`, `042`).
  - Example: `WI-2026-001`.
- IDs are minted at `TRIAGED` state, atomically with the backlog write.
- Legacy COO tasks use `id: T-NNN` format and are not WMF-managed.
- No separate `wi_id` field. The `id` field is the canonical WMF identifier.

---

## backlog.v1 Compatibility

Until `backlog.v2` or a dedicated `WorkItemEntry` schema exists, WI-* records in
`config/tasks/backlog.yaml` are stored as `backlog.v1 TaskEntry`-compatible records.
They must include the existing `backlog.v1` required fields **in addition to** WMF fields:

| Required legacy field | Allowed values |
|-----------------------|----------------|
| `id` | `WI-YYYY-NNN` |
| `title` | non-empty string |
| `priority` | `P0 \| P1 \| P2 \| P3` |
| `risk` | `low \| med \| high` |
| `status` | WMF state (see §State Machine) |
| `task_type` | `build \| content \| hygiene` |
| `objective_ref` | non-empty string |
| `created_at` | ISO 8601 timestamp |
| `scope_paths` | list (may be empty) |
| `tags` | list (may be empty) |

Do not omit required legacy fields or introduce hidden defaults. A WI item that passes
the WMF validator must also be loadable by `runtime/orchestration/coo/backlog.py`
without error.

---

## WMF Field Schema

Fields specific to WMF work items (`id: WI-YYYY-NNN`):

| Field | Required | Type | Notes |
|-------|----------|------|-------|
| `github_issue` | at `TRIAGED`+ | `int` | GitHub issue number |
| `workstream` | always | `str` | Key from `artifacts/workstreams.yaml` |
| `acceptance_criteria` | at `READY`/`DISPATCHED` | `list[str]` or `str` | Or use `acceptance_ref` |
| `acceptance_ref` | at `READY`/`DISPATCHED` | `str` | Pointer to external AC doc; alternative to `acceptance_criteria` |
| `plan_mode` | always | `none \| plan_lite \| formal` | |
| `plan_path` | if `formal` | `str` | Required when `plan_mode=formal` (no exceptions) |
| `plan_followup_required` | no | `bool` | `true` = plan deferred; P0 expedited path |
| `followup_backlog_item` | if P0 expedited | `WI-YYYY-NNN` | Required before `CLOSED` if P0 expedited |
| `closure_evidence` | at `CLOSED` | `list[{type,ref,note}]` | All three keys required per entry |

`class` is explicitly not required at any stage.

`acceptance_criteria` accepts:

- A non-empty string.
- A non-empty `list[str]` (all entries non-empty). **Preferred format.**

---

## State Machine

Work items progress through the following states:

| State | Meaning |
|-------|---------|
| `INTAKE` | Captured but not yet assessed |
| `TRIAGED` | Assessed, ID minted, github_issue assigned |
| `READY` | Acceptance criteria defined, ready to dispatch |
| `DISPATCHED` | Assigned to an agent or executor |
| `REVIEW` | Work complete, under review |
| `CLOSED` | Accepted and closed; closure evidence recorded |
| `BLOCKED` | Progress blocked; blocker documented in evidence |
| `DEFERRED` | Intentionally deferred |
| `REJECTED` | Rejected after assessment |
| `DUPLICATE` | Duplicate of an existing item |
| `SUPERSEDED` | Replaced by another item |

### Legal Transitions

```
INTAKE       → TRIAGED | REJECTED | DUPLICATE
TRIAGED      → READY | DEFERRED | REJECTED | BLOCKED
READY        → DISPATCHED | BLOCKED | DEFERRED
DISPATCHED   → REVIEW | BLOCKED
REVIEW       → CLOSED | DISPATCHED  ← fixes-requested returns here
CLOSED       → (terminal)
BLOCKED      → READY | TRIAGED | DEFERRED
DEFERRED     → TRIAGED | REJECTED
REJECTED     → (terminal)
DUPLICATE    → (terminal)
SUPERSEDED   → (terminal)
```

`REVIEW` fixes-requested returns to `DISPATCHED` (not `READY`), as the executor
must address the review findings before re-submitting.

---

## Plan Mode Rules

Every WMF item must declare a `plan_mode`. Allowed values:

| Value | Meaning |
|-------|---------|
| `none` | No plan required |
| `plan_lite` | Lightweight inline plan |
| `formal` | Formal plan document required |

### Rule: plan_mode=formal

`plan_mode=formal` **always** requires `plan_path`. No exceptions.

### P0 Expedited Path

P0 expedited dispatch applies when all three conditions hold:

```yaml
priority: P0
plan_mode: plan_lite
plan_followup_required: true
```

Under P0 expedited:

- The item may enter `DISPATCHED` without `plan_path`.
- A follow-up work item (`followup_backlog_item`) must be created before `CLOSED`.
- `plan_mode=formal` is **not** the expedited path. Formal plan items always need `plan_path`.

---

## Closure Evidence

Every item reaching `CLOSED` must include a `closure_evidence` list. Each entry must contain:

| Key | Type | Requirement |
|-----|------|-------------|
| `type` | `str` | Non-empty |
| `ref` | `str` | Non-empty (commit SHA, PR number, artifact path, etc.) |
| `note` | `str` | Non-empty |

Example:

```yaml
closure_evidence:
  - type: commit
    ref: abc1234
    note: Framework doc and validator merged on build/work-management-framework-v0.1
```

---

## Sole-Writer Rule

The active COO is the sole writer of operational state. Work item state transitions
(changes to `status`, `closure_evidence`, `followup_backlog_item`, etc.) must be
recorded in `config/tasks/backlog.yaml` by the COO, not by other agents writing
directly to `docs/11_admin/BACKLOG.md`.

---

## BACKLOG.md Derived Status

`docs/11_admin/BACKLOG.md` is a **derived, view-only summary**. It is not canonical.
The canonical queue state lives in `config/tasks/backlog.yaml`.

All edits to work item state belong in `config/tasks/backlog.yaml`.

---

## Notes

- `class` is not a required field at any stage.
- T-NNN items coexist with WI-YYYY-NNN items in `config/tasks/backlog.yaml` and are not WMF-managed.
- WMF validation applies only to items whose `id` starts with `WI-`.
- The Phase 0 validator is at `scripts/validate_work_items.py`. Run with `python scripts/validate_work_items.py`.
