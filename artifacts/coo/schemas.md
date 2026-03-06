# COO Output Schemas (Step 2)

This file defines parseable output contracts for COO dispatch artifacts.

## 1) TaskProposal (`task_proposal.v1`)

Parsed by `runtime/orchestration/coo/parser.py:parse_proposal_response()`.
Each proposal recommends an action on an existing backlog task.

```yaml
schema_version: task_proposal.v1
generated_at: "2026-03-06T00:00:00Z"
mode: propose
objective_ref: "OBJ-001"
proposals:
  - task_id: "T-001"
    rationale: "Highest priority, all dependencies met, low risk"
    proposed_action: "dispatch"
    urgency_override: null
    suggested_owner: "codex"
  - task_id: "T-009"
    rationale: "Blocked by missing provider health data; defer until monitoring is in place"
    proposed_action: "defer"
    urgency_override: null
    suggested_owner: ""
  - task_id: "T-004"
    rationale: "Scope ambiguity — CEO must clarify deliverable format before dispatch"
    proposed_action: "escalate"
    urgency_override: "P0"
    suggested_owner: ""
notes: "All proposals are L3 during burn-in"
```

Rules:
- `task_id` must reference an existing task in `config/tasks/backlog.yaml`.
- `proposed_action` must be one of: `dispatch`, `defer`, `escalate`.
- `urgency_override` is optional; if set, must be `P0`, `P1`, `P2`, or `P3`.
- `suggested_owner` is advisory; values: `codex`, `gemini`, `claude_code`, or empty string.

## 2) NothingToPropose (`nothing_to_propose.v1`)

```yaml
schema_version: nothing_to_propose.v1
generated_at: "2026-03-06T00:00:00Z"
mode: propose
objective_ref: "OBJ-001"
reason: "No pending actionable tasks after policy checks"
recommended_follow_up: "Request new objective or resolve blocked tasks"
```

## 3) ExecutionOrder (`execution_order.v1`)

Matches `runtime/orchestration/dispatch/order.py`.

```yaml
schema_version: execution_order.v1
order_id: "ORDER-COO-001"
task_ref: "COO-TASK-001"
created_at: "2026-03-06T00:00:00Z"
steps:
  - name: "implement"
    role: "builder"
    provider: "codex"
    mode: "blocking"
    lens_providers: {}
constraints:
  governance_policy: "default"
  worktree: true
  max_duration_seconds: 3600
  scope_paths:
    - "runtime/orchestration/coo/"
shadow:
  enabled: false
  provider: "codex"
  receives: "full_task_payload"
supervision:
  per_cycle_check: true
  batch_id: "BATCH-001"
  cycle_number: 1
```

Validation notes:
- `schema_version` must be exactly `execution_order.v1`.
- `order_id` must match `[a-zA-Z0-9_\-]{1,128}`.
- `steps` must be non-empty; each step requires `name` and `role`.
- `provider` routing is advisory in Step 2; runtime enforcement is deferred.

## 4) EscalationPacket (`escalation_packet.v1`)

`type` values align with `EscalationType` enum in `runtime/orchestration/ceo_queue.py`.

```yaml
schema_version: escalation_packet.v1
generated_at: "2026-03-06T00:00:00Z"
run_id: "run_20260306_000000"
type: "ambiguous_task"
context:
  summary: "Objective scope conflicts with current governance envelope"
  objective_ref: "OBJ-001"
  task_ref: "COO-TASK-001"
  files_considered:
    - "config/governance/delegation_envelope.yaml"
analysis:
  issue: "Unable to classify action under known autonomy categories"
options:
  - label: "Escalate to CEO"
    tradeoff: "Slower, governance-safe"
  - label: "Proceed at L3"
    tradeoff: "Faster, but policy risk"
recommendation: "Escalate to CEO"
```

Allowed escalation `type` values:
- `governance_surface_touch`
- `budget_escalation`
- `protected_path_modification`
- `ambiguous_task`
- `policy_violation`

## 5) StatusReport (`status_report.v1`)

```yaml
schema_version: status_report.v1
generated_at: "2026-03-06T00:00:00Z"
period: "daily"
summary:
  health: "green"
  headline: "Dispatch queue stable; no blocked critical tasks"
metrics:
  backlog_pending: 12
  backlog_in_progress: 3
  dispatch_inbox: 2
  dispatch_completed_24h: 5
escalations:
  pending: 1
  ids:
    - "ESC-0007"
next_actions:
  - "Propose parser hardening tasks"
  - "Review resolved escalations"
```
