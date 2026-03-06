# COO Output Schemas (Step 2)

This file defines parseable output contracts for COO dispatch artifacts.

## 1) TaskProposal (`task_proposal.v1`)

```yaml
schema_version: task_proposal.v1
generated_at: "2026-03-06T00:00:00Z"
mode: propose
objective_ref: "OBJ-001"
proposals:
  - id: "COO-TASK-001"
    title: "Implement dispatch parser"
    description: "Add parser for COO YAML output"
    dod: "Parser handles TaskProposal + ExecutionOrder"
    priority: "P1"
    risk: "med"
    scope_paths:
      - "runtime/orchestration/coo/"
    status: "pending"
    requires_approval: true
    owner: "coo"
    evidence: ""
    task_type: "build"
    tags:
      - "dispatch"
      - "parser"
    objective_ref: "OBJ-001"
    created_at: "2026-03-06T00:00:00Z"
    completed_at: null
    provider: "codex"
    provider_rationale: "Bounded implementation with tests"
notes: "All proposals are L3 during burn-in"
```

Rules:
- `id` should match `[A-Za-z0-9_\-]{1,64}`.
- Task fields mirror `TaskEntry` in `runtime/orchestration/coo/backlog.py`.
- `provider` advisory values: `codex`, `gemini`, `claude_code`, `auto`.

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
