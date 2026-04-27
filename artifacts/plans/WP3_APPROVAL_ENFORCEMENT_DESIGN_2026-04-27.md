# WP3 — Design Packet: Minimal Approval/Authority Enforcement

**Status:** Proposal — design packet; no implementation
**Owner:** Active COO
**Source:** `docs/audit/LIFEOS_AUTHORITY_AUDIT_RESULT_2026-04-27.md` §J (J1-J8), §C-006, C-007, APPROVAL-002
**Date:** 2026-04-27
**Implementation target:** After CEO approval of this design packet
**DO NOT IMPLEMENT UNTIL CEO APPROVES**

---

## 1. Overview

The authority audit diagnosed that canonical prose is ahead of enforceable schema mechanics (executive verdict §B). The COO Contract defines an approval tuple and sole-writer rule (§7-9), but the runtime-facing schemas, parser, and tracker surfaces do not carry enough authority, approval, lifecycle, or receipt fields to prevent invalid dispatch, inferred approval, stale approval, or peer/standby bypass.

This design packet covers the minimal schema/parser changes needed to make invalid authority non-actionable. It does **not** build a full policy engine.

---

## 2. New schema: `approval_receipt.v1`

### Schema (target: `artifacts/coo/schemas.md`)

```yaml
approval_receipt.v1:
  description: Durable record of a human approval event captured into canonical store.
  required:
    - receipt_id
    - proposal_id
    - proposal_fingerprint
    - rendered_summary_hash
    - approval_action
    - captured_from_channel
    - captured_at
    - captured_by
    - captured_by_role
    - source_event_ref
    - policy_version
    - phase
    - authority_scope
    - canonical_store_ref
  optional:
    - work_order_id
    - issue_id
    - expires_at
    - delegated_authority_ref
    - override_reason
  rules:
    - captured_by_role in [active_coo, ceo_authorized_operator]
    - approval_action in [approve, reject, waive, override, go, hold]
    - material_change_policy defaults to reapproval_required
```

### Receipt id format

`apr_<ISO timestamp>_<8-char hex prefix of proposal_fingerprint>`

### Implementation notes

- New file or section in `artifacts/coo/schemas.md`
- A Python dataclass `ApprovalReceipt` in `runtime/orchestration/coo/approval.py`
- Serialisation to YAML for file-based receipts; JSON for GitHub issue comment receipts
- The `approval_action` enum must match the COO Contract §9 action vocabulary

### Tests

| Test | Scenario | Expected |
|---|---|---|
| `test_approval_receipt_valid` | Create receipt with all required fields | Passes schema validation |
| `test_approval_receipt_missing_field` | Omit any required field | Validation fails |
| `test_approval_receipt_invalid_role` | Set captured_by_role to `peer_agent` | Validation rejects |
| `test_approval_receipt_invalid_action` | Set approval_action to `maybe` | Validation rejects |
| `test_approval_receipt_serialize_roundtrip` | YAML serialize → deserialize | Fields match exactly |

---

## 3. Amend `execution_order.v1` — authority fields

### Add to existing schema in `artifacts/coo/schemas.md`

```yaml
# Additional fields for execution_order.v1
work_order_id: string
issue_id: string?
attempt_id: string
issued_by: string
issued_by_role: active_coo | ceo_authorized_operator
authority_path: active_coo | ceo_authorized_operator
active_coo_id: string
phase: string
policy_version: string
state_precondition:
  required_state: ready
  state_hash: string?
approval_ref: string?
scope_paths: [string]
protected_paths: [string]
validators_required: [string]
receipt_refs: [string]
idempotency_key: string
```

### Rules

- `approval_ref` required when `requires_approval == true`, protected paths present, retry/redirect requires CEO approval, or governance policy requires it
- `issued_by_role` cannot be `standby`, `peer_agent`, `reviewer`, `execution_agent`, `wiki`, `drive`, or `workspace`
- `idempotency_key = issue_id + attempt_id + workflow_run_id` when workflow_run_id exists

### Tests

| Test | Scenario | Expected |
|---|---|---|
| `test_execution_order_approval_ref_required` | Approval-required order without ref | Parser rejects |
| `test_execution_order_valid_roles` | active_coo, ceo_authorized_operator roles | Accepted |
| `test_execution_order_invalid_roles` | standby, peer_agent, reviewer roles | Rejected |
| `test_execution_order_idempotency_key` | Same key reused | Idempotency check passes |

---

## 4. Parser guard plan (`runtime/orchestration/coo/parser.py`)

### Current state

The parser (`parser.py`) currently validates schema structure but does not check:
- authority path / issuer role
- approval reference validity
- state precondition match
- source canonicality
- closure receipt requirements

### Required guards (implement one at a time, test each)

| # | Guard | Failure mode prevented | Priority |
|---|---|---|---|
| G1 | Reject missing `active_coo_id`, `attempt_id`, `state_precondition`, `policy_version` | Incomplete execution orders | P0 |
| G2 | Reject missing required `approval_ref` | Unapproved protected work | P0 |
| G3 | Reject invalid `issued_by_role` values | Standby/peer bypass | P0 |
| G4 | Reject non-canonical sources as authority | Drive/wiki/advisory bypass | P1 |
| G5 | Reject proposal fingerprint/hash mismatch against approval receipt | Stale approval | P1 |
| G6 | Reject terminal closure unless `closure_receipt_ref` and validator results exist | False closure | P1 |

### Implementation approach

Each guard is a separate function in `parser.py` or a new `parser_guards.py`:

```python
def guard_active_coo_id(execution_order: dict) -> list[str]:
    """Check active_coo_id is present and matches registry."""
    errors = []
    if not execution_order.get("active_coo_id"):
        errors.append("active_coo_id is required")
    return errors
```

Guard functions return a list of error strings. Empty list = pass. The `parse_execution_order` function calls all applicable guards and collects errors.

### Guard G4 — source canonicality classifier

A helper function classifies a source path:

```python
CANONICALITY_CLASSES = {
    "canonical": ["docs/01_governance/", "docs/00_foundations/LifeOS Target Architecture"],
    "derived": [".context/wiki/"],
    "proposal": ["docs/00_foundations/ARCH_"],
    "draft": [],
    "stale": ["docs/99_archive/"],
    "external": [],  # Drive, Workspace, chat
}

def classify_source(path: str) -> str:
    """Return the canonicality class of a source path."""
```

Only `canonical` sources may satisfy canonical authority guards by default.

### Tests for parser guards

| Test | Guard | Scenario | Expected |
|---|---|---|---|
| `test_guard_missing_active_coo_id` | G1 | No active_coo_id | Error returned |
| `test_guard_missing_approval_ref` | G2 | Approval-required without ref | Error returned |
| `test_guard_invalid_issued_by_role` | G3 | standby as issuer | Error returned |
| `test_guard_canonical_source_pass` | G4 | Path under docs/01_governance/ | Pass |
| `test_guard_proposal_source_fail` | G4 | Path under ARCH_ proposal | Fail |
| `test_guard_fingerprint_mismatch` | G5 | Hash differs from approval receipt | Error returned |
| `test_guard_closure_no_receipt` | G6 | Try close without closure_receipt_ref | Error returned |

---

## 5. Files to create/modify

| File | Action | Notes |
|---|---|---|
| `artifacts/coo/schemas.md` | Amend | Add `approval_receipt.v1`; amend `execution_order.v1`, `task_proposal.v1`, `escalation_packet.v1` |
| `runtime/orchestration/coo/approval.py` | **Create** | `ApprovalReceipt` dataclass, serialisation, validation |
| `runtime/orchestration/coo/parser_guards.py` | **Create** | Guard functions for authority checks |
| `runtime/orchestration/coo/parser.py` | Amend | Integrate guard calls into `parse_execution_order` |
| `runtime/tests/orchestration/coo/test_approval_receipt.py` | **Create** | Tests for approval receipt schema |
| `runtime/tests/orchestration/coo/test_parser_guards.py` | **Create** | Tests for each guard function |

---

## 6. Non-goals (explicitly out of scope for WP3)

- Full policy engine
- Drive/Workspace polling, ingress, or approval adapters
- New Hermes/OpenClaw peer command semantics
- Active COO registry mechanism (only the field reference; see WP2 D4b for registry)
- Semantic validator sophistication beyond guard functions
- General identity/provenance framework
- Productisation
- UI or CLI changes for approval capture

---

## 7. Dependencies

- **WP2 D1 (G-CBS):** If G-CBS is demoted (recommended), the `approval_receipt.v1` schema does not need to conform to G-CBS receipt formats. If ratified, alignment may be needed.
- **WP2 D4b (active COO registry):** The `active_coo_id` field references the registry; implementation of the registry itself is a separate concern.
- **WP4 (lifecycle/closure):** The `approval_ref` in lifecycle state records references an `approval_receipt.v1` ID. WP3 and WP4 schemas should be designed together to ensure `approval_ref` types are consistent.

---

## 8. Implementation sequence (after CEO approval)

1. Add `approval_receipt.v1` schema to `schemas.md`
2. Create `approval.py` with dataclass and validation
3. Amend `execution_order.v1` in `schemas.md` with authority fields
4. Create `parser_guards.py` with G1, G2, G3 (P0 guards)
5. Test G1-G3
6. Add G4-G6 guards incrementally with tests
7. Amend `parser.py` to call guards
8. Final test pass on all guard tests