# WP4 — Design Packet: Lifecycle/Closure Semantics

**Status:** Proposal — design packet; no implementation
**Owner:** Active COO
**Source:** `docs/audit/LIFEOS_AUTHORITY_AUDIT_RESULT_2026-04-27.md` §G (G1-G6), §C-016, STATE-002, OD-AUDIT-002
**Date:** 2026-04-27
**Implementation target:** After CEO approval of this design packet
**DO NOT IMPLEMENT UNTIL CEO APPROVES**

---

## 1. Overview

The authority audit found that the current lifecycle allows `succeeded` to be read as terminal success, creating a false-closure risk (C-016, BLOCKING). The Target Architecture has useful work-order states but under-specifies the review-return and closure gap. The audit proposes a corrected minimal state set (section G2-G3) with a clear `closed` terminal state requiring closure receipt.

This design packet covers the minimal lifecycle schema changes, state transition guard plan, and closure receipt path. It does **not** change any runtime code until CEO approval.

---

## 2. `succeeded` disposition (OD-AUDIT-002)

### Problem

`succeeded` is currently a state that can be interpreted as terminal success. It is used by workers to report result status, but downstream processes (review, validation, approval for closure) are not represented in the state machine.

### Options

| Option | Effect | Migration effort |
|---|---|---|
| **A: Rename to `worker_succeeded`** | Makes it explicit that this is a worker result event, not terminal closure | Low: rename in state machine + tests |
| **B: Keep `succeeded` but add explicit non-terminal documentation** | Preserves existing state names; adds clarity in doc | Lowest: doc-only |
| **C: Replace `succeeded` with `review_returned`** | Aligns with corrected state machine (G2) where worker result goes to `review_returned`, not to a `succeeded` terminal | Medium: rename + transition logic change |

### Recommendation

**Option C** — align with the audit's corrected lifecycle (G2). The `review_returned` state makes the state machine honest: worker returns result → review/validation → closure.

If Option C is too aggressive, **Option A** as a transitional step. Never keep `succeeded` as a terminal-like state (not Option B alone).

### CEO decision needed

Choose A, B, or C.

---

## 3. `closed` requirements

### Definition

`closed` is the **terminal accepted completion** state. It is not reachable directly from `running` or `review_returned`. It requires:

1. All required validators/gates passed (or explicitly overridden by valid CEO receipt)
2. PR/commit/artifact/test refs for build work
3. Review disposition for reviewer-requested changes
4. Reconciliation receipt for projection/tracker conflicts (if applicable)
5. Open-decision list for unresolved issues
6. A valid closure receipt (see §4)

### Transition path

```
review_returned → under_validation → closed
```

Prohibited shortcuts:
- `running → closed` (no review/validation/closure receipt)
- `review_returned → closed` without `under_validation`

### Validation

A `close` attempt must fail (return to `review_returned` or `needs_decision`) if:
- Any blocking finding from review/validation is unresolved
- Required approval is missing or stale
- Closure receipt is missing
- An open decision list is non-empty

---

## 4. Closure receipt path

### Schema

```yaml
closure_receipt.v1:
  receipt_id: string
  work_order_id: string
  issue_id: string?
  previous_state: string
  new_state: string  # always "closed"
  closed_by: string
  closed_by_role: active_coo | ceo_authorized_operator
  validators_passed: [string]
  approval_refs: [string]
  artifact_refs: [string]
  pr_refs: [string]
  test_result_ref: string?
  reviewer_packet_refs: [string]
  unresolved_decisions: [string]
  reconciliation_ref: string?
  state_hash: string
  closed_at: datetime
```

### Receipt id format

`clr_<ISO timestamp>_<work_order_id>`

### Evidence bundle

A closure receipt is always accompanied by an evidence bundle containing:
- The receipts for each validator/gate that passed
- PR/commit refs for build work
- Test result summary
- Any review packets
- Any reconciliation receipts

### Implementation notes

- `closure_receipt.v1` data class in `runtime/orchestration/coo/closure.py`
- Serialization to YAML
- Stored in `artifacts/receipts/closure/`
- The `state_hash` is a hash of the lifecycle state record at closure time

---

## 5. Amended lifecycle schema: `lifecycle_state.v1`

Add to `artifacts/coo/schemas.md`:

```yaml
lifecycle_state.v1:
  work_order_id: string
  issue_id: string?
  state: string
  previous_state: string?
  state_version: integer
  state_updated_at: datetime
  state_updated_by: string
  active_coo_id: string
  phase: string
  policy_version: string
  approval_ref: string?
  execution_order_ref: string?
  attempt_id: string?
  workflow_run_id: string?
  reviewer_packet_ref: string?
  validator_result_refs: [string]
  closure_receipt_ref: string?
  blocked_reason: string?
  needs_decision_owner: string?
  state_hash: string
```

### Valid states

`intake`, `triaged`, `awaiting_approval`, `ready`, `dispatched`, `running`, `review_returned`, `under_validation`, `fixes_requested`, `blocked`, `needs_decision`, `timed_out`, `superseded`, `withdrawn`, `rejected`, `failed`, `closed`

### Terminal states

`closed`, `failed`, `rejected`, `withdrawn`, `superseded`

Note: `succeeded` is **not** in this state list. See §2 for disposition.

---

## 6. Review/validation closure path

### Review packet closure integration

When a review packet has `verdict: accept` and no blocking findings:

```
review_returned → under_validation → closed
```

If review has `verdict: request_fixes` with blocking findings:

```
review_returned → under_validation → fixes_requested
```

If review has `verdict: reject` or `veto`:

```
review_returned → under_validation → blocked/needs_decision
```

### Validator results

Each validator in `validator_result_refs` must have:
- `validator_name`: string
- `validator_version`: string
- `input_hash`: string
- `output`: pass | fail | warn
- `result_detail`: string

All required validators must pass before closure. A `fail` on any required validator blocks the `under_validation → closed` transition.

### Documentation receipt path

A doc-only closure (no build work) requires:
- Closure receipt
- Doc change summary (what changed, why)
- Reconciliation receipt if trackers were touched
- Approval ref if approval-required doc change
- No PR/commit refs needed (implied by nature of doc-only change — the commit IS the artifact)

---

## 7. Tests

### Lifecycle state tests

| Test | Scenario | Expected |
|---|---|---|
| `test_closed_requires_closure_receipt` | Try `review_returned → closed` without receipt | Transition rejected |
| `test_running_to_closed_rejected` | Try `running → closed` directly | Rejected — prohibited shortcut |
| `test_review_returned_to_closed_without_validation` | Try skip `under_validation` | Rejected |
| `test_valid_closure_path` | `review_returned → under_validation → closed` with all requirements | Accepted |
| `test_fixes_requested_path` | Review with blocking findings → `fixes_requested` | Correct state |
| `test_blocked_state_path` | Validator fail on critical gate → `blocked` or `needs_decision` | Correct state |
| `test_terminal_state_list` | Only `closed`, `failed`, `rejected`, `withdrawn`, `superseded` are terminal | Validation |
| `test_succeeded_not_terminal` | `succeeded` state (if retained) does not permit closure transition | Correct |

### Closure receipt tests

| Test | Scenario | Expected |
|---|---|---|
| `test_closure_receipt_valid` | All required fields present | Passes |
| `test_closure_receipt_missing_field` | Omit required field | Fails |
| `test_closure_receipt_evidence_bundle` | Bundle contains all required receipt refs | Passes |
| `test_closure_receipt_state_hash` | State hash matches current lifecycle state | Passes |
| `test_closure_receipt_invalid_state_hash` | State hash mismatch | Validation fails |

### FSM transition tests

| Test | Scenario | Expected |
|---|---|---|
| `test_fsm_allowed_transitions` | Allowed from-to pairs pass | Pass |
| `test_fsm_prohibited_shortcuts` | Prohibited pairs rejected (running→closed, etc.) | Fail |
| `test_fsm_all_states_documented` | Every state in FSM appears in valid state list | Pass |

---

## 8. Files to create/modify

| File | Action | Notes |
|---|---|---|
| `artifacts/coo/schemas.md` | Amend | Add `lifecycle_state.v1`, `closure_receipt.v1`; remove/rename `succeeded` |
| `runtime/orchestration/coo/closure.py` | **Create** | `ClosureReceipt` dataclass, closure validation, evidence bundle builder |
| `runtime/orchestration/coo/fsm.py` | **Create** | FSM definition, transition validator, guard evaluator |
| `runtime/orchestration/coo/state.py` | **Create** | `LifecycleState` dataclass, serialisation, state_hash computation |
| `runtime/tests/orchestration/coo/test_closure_receipt.py` | **Create** | Closure receipt schema tests |
| `runtime/tests/orchestration/coo/test_lifecycle_state.py` | **Create** | Lifecycle state transition tests |
| `runtime/tests/orchestration/coo/test_fsm.py` | **Create** | FSM allowed/prohibited transition tests |

---

## 9. Non-goals (explicitly out of scope for WP4)

- Changing `succeeded`/`closed` lifecycle semantics in existing runtime code without CEO decision (MAY NOT item #6)
- Building a full policy engine
- Adding new lifecycle names beyond the G2 set
- Implementing convenience shortcuts around closure gates
- UI or CLI changes for closure capture
- Migration of existing `succeeded` state data (separate migration plan needed)
- Integration with external approval/closure tools

---

## 10. Dependencies

- **WP3 (approval enforcement):** `closure_receipt.v1` references `approval_receipt.v1` IDs in `approval_refs`. The two schema sets must be designed together for type consistency.
- **WP2 D1 (G-CBS):** If G-CBS remains binding, the closure evidence bundle may need G-CBS-compliant structure. If demoted (recommended), the closure receipt is self-contained.
- **WP2 D4b (active COO registry):** `closed_by_role` references the registry.

---

## 11. Implementation sequence (after CEO approval)

1. Add `lifecycle_state.v1` and `closure_receipt.v1` to `schemas.md`
2. Create `fsm.py` with state definitions and transition map
3. Create `state.py` with `LifecycleState` dataclass and `state_hash` computation
4. Create `closure.py` with `ClosureReceipt` dataclass and validation
5. Test lifecycle state creation, serialisation, transitions
6. Test closure receipt schema and evidence bundle
7. Test FSM allowed/prohibited transitions
8. Integration test: full review→validation→closure path