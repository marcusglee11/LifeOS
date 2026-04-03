# COO Output Schemas (Step 2)

This file defines parseable output contracts for COO dispatch artifacts.

## 1) TaskProposal (`task_proposal.v1`)

Parsed by `runtime/orchestration/coo/parser.py:parse_proposal_response()`.
Each proposal recommends an action on an existing backlog task.

```yaml
schema_version: task_proposal.v1
proposals:
  - task_id: T-001
    rationale: "Highest priority with all deps met."
    proposed_action: dispatch
    urgency_override: null
    suggested_owner: codex
  - task_id: T-002
    rationale: "Next priority; defer until T-001 complete."
    proposed_action: defer
    urgency_override: null
    suggested_owner: ""
```

Rules:
- `task_id` must reference an existing task in `config/tasks/backlog.yaml`.
- `proposed_action` must be one of: `dispatch`, `defer`, `escalate`.
- `urgency_override` is optional; if set, must be `P0`, `P1`, `P2`, or `P3`.
- `suggested_owner` is advisory; values: `codex`, `gemini`, `claude_code`, or empty string.

## 2) NothingToPropose (`nothing_to_propose.v1`)

```yaml
schema_version: nothing_to_propose.v1
reason: "No pending actionable tasks after policy checks."
recommended_follow_up: "Wait for blocked tasks to unblock."
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

## 4) OperationProposal (`operation_proposal.v1`)

```yaml
schema_version: operation_proposal.v1
proposal_id: OP-a1b2c3d4
title: "Write workspace note"
rationale: "The user asked for a workspace mutation that fits the allowlisted ops lane."
operation_kind: mutation
action_id: workspace.file.write
args:
  path: /workspace/notes/example.md
  content: "Hello from COO."
requires_approval: true
suggested_owner: lifeos
```

Allowed query actions:
- `workspace.file.read`
- `workspace.file.list`
- `workspace.status.inspect`

Allowed mutation actions:
- `workspace.file.write`
- `workspace.file.edit`
- `lifeos.note.record`

`operation_kind` must match the registry-backed action kind for the selected `action_id`.

## 5) EscalationPacket (`escalation_packet.v1`)

`type` values align with `EscalationType` enum in `runtime/orchestration/ceo_queue.py`.

```yaml
schema_version: escalation_packet.v1
type: ambiguous_task
objective: "the CEO objective text"
options:
  - option_id: A
    title: "Escalate to CEO"
    action: "Pause and request clarification."
  - option_id: B
    title: "Proceed at L3"
    action: "Continue with operator-visible risk."
```

Allowed escalation `type` values:
- `governance_surface_touch`
- `budget_escalation`
- `protected_path_modification`
- `ambiguous_task`
- `policy_violation`

## 6) StatusReport (`status_report.v1`)

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
