# Work Management Framework v0.1

<!-- markdownlint-disable MD013 MD040 MD060 -->

**Status**: Active
**Version**: 0.1
**Effective**: 2026-04-27
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0 → active COO execution order

---

## 1. Purpose

The Work Management Framework (WMF) is the lightweight repo-backed project-management layer for COO-managed LifeOS work. It uses existing repository surfaces to support intake, prioritisation, dispatch, review, and closure without introducing a PM application or runtime orchestration changes.

WMF v0.1 answers one operational question: what is the canonical state of each COO-managed work item, and what evidence is required to move it forward?

---

## 2. Non-goals

WMF v0.1 does **not** implement:

- PM dashboards or application UI.
- GitHub API reconciliation.
- Automated GitHub issue creation or closing.
- WIP limits or capacity planning.
- Full transition-matrix enforcement.
- `BACKLOG.md` auto-generation.
- Parallel COO locking or transactional ID services.
- Runtime execution behavior changes.
- Broad architecture normalization.

---

## 3. Operating model

### 3.1 Role boundaries

| Role | WMF responsibility |
|------|--------------------|
| CEO | Approves kickoff, answers judgment blockers, accepts or rejects final result |
| Active COO | Sole operational coordinator; owns dispatch, scope control, backlog writes, evidence review, and escalation |
| EA/build agent | Makes repo edits, runs validator/tests, and reports evidence |
| Reviewer | Reviews PR/diff/evidence and returns accept or fixes-requested |
| Standby COO | May review or advise; must not write operational state unless explicitly promoted |

### 3.2 Active-COO substrate semantics

Only the active COO writes WMF operational state. Standby COOs, reviewers, and build agents may propose changes, but state transitions are not canonical until the active COO records them in `config/tasks/backlog.yaml`.

Current v0.1 limitation: WMF assumes one active writer. It does not provide concurrent ID minting, file locking, or transaction semantics. If parallel operational writers are introduced, v0.2 must add a locked or transactional mint/write mechanism before more than one writer can mutate WMF state.

### 3.3 Minimum manual loop

New COO-managed work defaults to a `WI-YYYY-NNN` entry in `config/tasks/backlog.yaml`.

The minimum manual operating loop is:

1. Intake issue or request.
2. Triage and mint `WI-YYYY-NNN`.
3. Update `config/tasks/backlog.yaml` state.
4. Dispatch through an execution order or approved manual handoff.
5. Review diff, PR, receipt, or evidence.
6. Close by recording `closure_evidence` in `config/tasks/backlog.yaml`.

`docs/11_admin/BACKLOG.md` may summarize this loop but must not originate or uniquely store any step.

---

## 4. Authority matrix

| Surface | Role | Authority |
|---------|------|-----------|
| GitHub issues | Intake and coordination bus | Non-canonical coordination; useful for discussion, acceptance criteria, PR links, and external visibility |
| `config/tasks/backlog.yaml` | Canonical queue state | Authoritative for work-item status, priority, workstream, dispatch readiness, blockers, and closure evidence |
| `docs/11_admin/BACKLOG.md` | Derived, view-only human summary | Non-canonical; must not contain unique work-item state |
| `artifacts/workstreams.yaml` | Workstream taxonomy | Authoritative source for valid `workstream` values |
| `docs/02_protocols/Project_Planning_Protocol_v1.0.md` | Formal planning protocol | Authoritative for formal plan content and review expectations |
| `execution_order.v1` | Dispatch authority | Authorizes an executor to perform bounded work |
| `closure_evidence` | Completion proof | Required evidence bundle for `CLOSED` work |

Conflict rule: if GitHub issues, `BACKLOG.md`, or status summaries disagree with `config/tasks/backlog.yaml`, `backlog.yaml` wins for WMF queue state.

---

## 5. ID model

- WMF work items use `id: WI-YYYY-NNN` as the primary identifier.
  - `YYYY` is the four-digit calendar year.
  - `NNN` is a three-digit zero-padded sequence number within that year.
  - Example: `WI-2026-001`.
- IDs are minted at `TRIAGED`, not `INTAKE`.
- ID minting is valid only when the new ID and item state are written atomically to `config/tasks/backlog.yaml` in the same operational update.
- Legacy COO tasks use `id: T-NNN`; they coexist in `config/tasks/backlog.yaml` and are not WMF-managed.
- No separate `wi_id` field exists. The `id` field is canonical.

---

## 6. State machine

### 6.1 Active v0.1 states

| State | Meaning | Entry requirement | Exit requirement |
|-------|---------|-------------------|------------------|
| `INTAKE` | Captured but not yet assessed | Issue, note, or request exists | Triage decision |
| `TRIAGED` | Assessed and accepted for tracking | `WI-YYYY-NNN` minted and `github_issue` recorded | Priority/workstream/next action clear |
| `READY` | Ready to dispatch | Acceptance criteria or acceptance reference exists | Executor selected or blocker found |
| `DISPATCHED` | Assigned to an executor | Dispatch authority exists, usually `execution_order.v1` | Work complete, blocked, or deferred |
| `REVIEW` | Work submitted for review | Evidence or PR exists | Accepted/closed or fixes requested |
| `CLOSED` | Accepted and complete | Closure evidence recorded | Terminal |
| `BLOCKED` | Progress is blocked | `blocked_reason` or equivalent evidence exists | Unblocked, deferred, or re-triaged |
| `DEFERRED` | Intentionally deferred | Deferral reason recorded | Re-triaged or rejected |
| `REJECTED` | Not accepted for execution | Rejection reason recorded | Terminal |
| `DUPLICATE` | Duplicate of another item | `duplicate_of` should identify canonical item | Terminal |
| `SUPERSEDED` | Replaced by another item | `superseded_by` should identify replacement | Terminal |

### 6.2 Legal transitions

```text
INTAKE       → TRIAGED | REJECTED | DUPLICATE
TRIAGED      → READY | DEFERRED | REJECTED | BLOCKED
READY        → DISPATCHED | BLOCKED | DEFERRED
DISPATCHED   → REVIEW | BLOCKED
REVIEW       → CLOSED | DISPATCHED
CLOSED       → (terminal)
BLOCKED      → READY | TRIAGED | DEFERRED
DEFERRED     → TRIAGED | REJECTED
REJECTED     → (terminal)
DUPLICATE    → (terminal)
SUPERSEDED   → (terminal)
```

`REVIEW → DISPATCHED` is the fixes-requested path. Review fixes return to the executor; they do not go back to `READY`.

### 6.3 Deferred states and concepts

The following labels are intentionally not v0.1 states: `PLANNING_REQUIRED`, `IN_PROGRESS`, `ACCEPTED`, `BACKLOG_READY`, `READY_FOR_DISPATCH`. Represent these concepts with v0.1 fields instead:

- Planning need: `plan_mode`, `plan_path`, `plan_followup_required`.
- Active execution: `DISPATCHED` plus owner/executor metadata.
- Acceptance: `CLOSED` plus `closure_evidence`.
- Dispatch readiness: `READY` plus acceptance criteria/ref and planning fields.

---

## 7. Planning and dispatch rules

### 7.1 Plan modes

Every WMF item must declare `plan_mode`.

| Value | Meaning | Minimum expectation |
|-------|---------|---------------------|
| `none` | No separate plan needed | Acceptance criteria are enough |
| `plan_lite` | Lightweight inline plan | Scope, risks, and verification fit inside the work item or issue |
| `formal` | Formal implementation plan required | `plan_path` points to a plan governed by `Project_Planning_Protocol_v1.0.md` |

`plan_mode=formal` requires a non-empty `plan_path`. No v0.1 exception changes that requirement. The expedited P0 path uses `plan_lite`, not `formal`.

### 7.2 Formal plan threshold

Use `plan_mode=formal` when work changes runtime behavior, touches multiple subsystems, affects protected/authority surfaces, introduces non-trivial migration risk, or has ambiguous acceptance criteria that need explicit review before implementation.

### 7.3 Plan-lite threshold

Use `plan_mode=plan_lite` for bounded work where scope, risks, and verification can be captured in the issue or backlog item. A plan-lite item should still state:

- Scope.
- Non-scope.
- Acceptance criteria or acceptance reference.
- Verification commands.
- Known risk or rollback note.

### 7.4 P0 expedited path

P0 expedited dispatch is allowed when all three fields are present:

```yaml
priority: P0
plan_mode: plan_lite
plan_followup_required: true
```

Under this path:

- The item may enter `DISPATCHED` without `plan_path`.
- The follow-up plan item may be created after dispatch.
- The original item cannot enter `CLOSED` until `followup_backlog_item` is populated.

### 7.5 Dispatch readiness checklist

A WMF item is dispatch-ready only when:

- `status` is `READY`.
- `priority` and `priority_rationale` are present or the rationale is evident from the item context.
- `workstream` is valid in `artifacts/workstreams.yaml`.
- Acceptance criteria or `acceptance_ref` exists.
- `plan_mode` is valid and any required `plan_path` exists.
- Known blockers are absent or explicitly accepted by the active COO.
- Dispatch authority is available before moving to `DISPATCHED`.

---

## 8. Backlog schema

### 8.1 backlog.v1 compatibility

Until `backlog.v2` or a dedicated `WorkItemEntry` schema exists, WI records in `config/tasks/backlog.yaml` remain `backlog.v1 TaskEntry`-compatible. A WI item that passes the WMF validator must also remain loadable by `runtime/orchestration/coo/backlog.py`.

Legacy `T-NNN` items remain valid and are not subject to WMF validation.

### 8.2 Required WMF fields for active items

The canonical schema must support these fields for active WI items:

| Field | Requirement |
|-------|-------------|
| `id` | `WI-YYYY-NNN` |
| `github_issue` | Required at `TRIAGED` or later |
| `title` | Non-empty work title |
| `status` | One of the v0.1 states |
| `priority` | `P0`, `P1`, `P2`, or `P3` |
| `priority_rationale` | Why the priority is appropriate; may be omitted only when obvious from linked context |
| `workstream` | Key from `artifacts/workstreams.yaml` |
| `owner` | Current responsible owner or executor, if assigned |
| `blocked_by` | Blocking item/person/system when blocked |
| `plan_mode` | `none`, `plan_lite`, or `formal` |
| `plan_path` | Required for `plan_mode=formal` |
| `acceptance_criteria` | Required at `READY`/`DISPATCHED` unless `acceptance_ref` is present |
| `acceptance_ref` | Pointer to acceptance criteria; alternative to inline criteria |
| `dispatch_ready` | Optional explicit readiness flag; status still controls lifecycle |
| `closure_evidence` | Required at `CLOSED` |

### 8.3 Optional fields

WMF v0.1 may also use: `size`, `risk`, `created_at`, `updated_at`, `awaiting_decision_by`, `blocked_reason`, `unblock_condition`, `defer_until`, `defer_reason`, `duplicate_of`, `superseded_by`, `plan_followup_required`, `followup_backlog_item`, `related_prs`, `related_commits`, and `last_material_update_at`.

`class` is explicitly **not** required at any stage. Its presence must not fail validation, and its absence must not fail validation.

---

## 9. Prioritisation rules

| Priority | Meaning |
|----------|---------|
| `P0` | Critical: safety, authority, data-loss, blocked core operations, or urgent CEO-directed work |
| `P1` | High: unblocks important programme work or completes active commitments |
| `P2` | Normal: valuable but not immediately blocking |
| `P3` | Low: cleanup, opportunistic improvement, or deferred polish |

Use `priority_rationale` where the reason is not self-evident. Tie-breakers should be qualitative and evidence-based, not a hidden numeric scoring formula:

1. Safety/authority risk.
2. Work that unblocks multiple downstream items.
3. Commitments already made to CEO or external parties.
4. Small high-confidence closure wins.
5. Cleanup only after active obligations are safe.

---

## 10. Stale item rules

WMF v0.1 does not enforce stale windows mechanically, but the active COO must review stale items during backlog maintenance:

| State | Stale signal | Expected action |
|-------|--------------|-----------------|
| `TRIAGED` | No material update or route to readiness | Clarify acceptance criteria, defer, or reject |
| `READY` | Not dispatched after becoming ready | Dispatch, downgrade priority, or defer |
| `DISPATCHED` | No executor progress/evidence | Ask for evidence, move to `BLOCKED`, or reassign |
| `REVIEW` | Review not resolved | Accept/close or send fixes back to `DISPATCHED` |

Use `last_material_update_at`, `blocked_reason`, `unblock_condition`, and comments/evidence refs where helpful. Avoid inventing state only in `BACKLOG.md` to compensate for stale data.

---

## 11. CEO attention queue

CEO attention is represented in canonical queue state, not by ad hoc notes. Use fields such as:

- `awaiting_decision_by: CEO`
- `blocked_reason`
- `unblock_condition`
- `acceptance_ref`
- `priority: P0` or `P1` when justified

A CEO-facing summary may be rendered in `BACKLOG.md`, but the underlying decision/blocker state must exist in `config/tasks/backlog.yaml` or linked evidence.

---

## 12. Closure evidence

Every item entering `CLOSED` must include a non-empty `closure_evidence` list. Each entry must contain:

| Key | Type | Requirement |
|-----|------|-------------|
| `type` | `str` | Non-empty evidence type, such as `commit`, `pr`, `test`, `artifact`, or `receipt` |
| `ref` | `str` | Non-empty commit SHA, PR URL/number, artifact path, command, or receipt ref |
| `note` | `str` | Non-empty explanation of what the evidence proves |

Example:

```yaml
closure_evidence:
  - type: pr
    ref: https://github.com/marcusglee11/LifeOS/pull/67
    note: Framework doc, backlog annotations, validator, and tests landed.
```

---

## 13. Reconciliation invariants

- No canonical work-item state may exist only in `docs/11_admin/BACKLOG.md`.
- GitHub issue status, PR status, and backlog status should be reconciled when work closes.
- A merged PR alone does not prove closure unless closure evidence is recorded for the WMF item.
- `BACKLOG.md` may summarize; it must not originate unique state transitions.
- Workstream values come from `artifacts/workstreams.yaml`.
- Broad architecture documents must not be rewritten as part of WMF v0.1 except for required index/corpus stewardship.

---

## 14. BACKLOG.md derived status

`docs/11_admin/BACKLOG.md` is a derived, view-only summary. It is not canonical. The canonical queue state lives in `config/tasks/backlog.yaml`.

Phase 1 target: `BACKLOG.md` should either be generated from `config/tasks/backlog.yaml` or removed if the generated view is not useful.

---

## 15. Phase 0 validator requirements

The Phase 0 validator lives at `scripts/validate_work_items.py` and runs locally with:

```bash
python3 scripts/validate_work_items.py --check
```

It must check:

- Unique WMF IDs.
- ID format `WI-YYYY-NNN`.
- Valid status.
- Valid priority.
- `TRIAGED` or later items have `github_issue`.
- Valid `workstream` values from `artifacts/workstreams.yaml`.
- `READY` and `DISPATCHED` items have `acceptance_criteria` or `acceptance_ref`.
- `plan_mode=formal` requires `plan_path`.
- P0 expedited items cannot close without `followup_backlog_item`.
- `CLOSED` items require `closure_evidence`.
- Each `closure_evidence` entry contains `type`, `ref`, and `note`.
- `BACKLOG.md` contains a derived/view-only header if retained.
- `class` is not required.

Implementation constraints:

- Deterministic error ordering.
- Clear file/path/item identifiers in errors.
- Fail closed on malformed YAML.
- No network or GitHub API access.
- Narrow v0.1 scope; no dashboard or full transition enforcement.
- Non-zero exit on blocking validation failures.

The standard repo quality gate runs the same validator for relevant WMF changes:

```bash
python3 scripts/workflow/quality_gate.py check --scope changed --json
```

Relevant changes include `config/tasks/backlog.yaml`, `artifacts/workstreams.yaml`, `docs/11_admin/BACKLOG.md`, this framework document, and `scripts/validate_work_items.py`.

---

## 16. Deferred v0.2 work

Defer the following until v0.1 has operational evidence:

- `backlog.v2` or dedicated `WorkItemEntry` schema.
- Auto-generated `BACKLOG.md`.
- GitHub issue/backlog reconciliation.
- Locked/transactional ID minting.
- Full legal-transition enforcement.
- WIP/capacity planning.
- Runtime orchestration integration.
- Dashboards or PM application views.
