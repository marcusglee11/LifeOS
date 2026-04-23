---
source_docs:
  - docs/11_admin/LIFEOS_STATE.md
  - docs/11_admin/BACKLOG.md
  - config/tasks/backlog.yaml
  - config/governance/delegation_envelope.yaml
last_updated: bf4d9ecd
concepts:
  - backlog
  - task proposal
  - delegation envelope
  - LIFEOS_STATE
  - COO workflow
---

# Backlog & Task System

## Summary

The COO reviews the structured backlog (`config/tasks/backlog.yaml`) and
proposes tasks to the CEO via `lifeos coo propose`. Approved tasks become
ExecutionOrders dispatched to sprint agents. `docs/11_admin/LIFEOS_STATE.md`
is the canonical source of truth for current phase and active WIP.

## Key Relationships

- **[agent-roles](agent-roles.md)** — COO drives the task proposal loop.
- **[openclaw-integration](openclaw-integration.md)** — live COO invocation produces proposals.
- **[governance-model](governance-model.md)** — delegation envelope defines COO authority bounds.
- **Backlog source**: `config/tasks/backlog.yaml`
- **Delegation bounds**: `config/governance/delegation_envelope.yaml`
- **State source of truth**: `docs/11_admin/LIFEOS_STATE.md`
- **Task queue**: `docs/11_admin/BACKLOG.md`

## Task Proposal Flow

```
COO reads backlog.yaml
  → proposes task_proposal.v1 YAML
  → CEO approves → ExecutionOrder YAML
  → sprint agent receives order + worktree path
  → builds in isolation
  → close_build gates
  → merged to main
```

## Delegation Envelope

Defines which actions the COO can take autonomously (L0) vs. must escalate (L4).
Key flags per task: `requires_approval` (bool), `risk` (low/medium/high).
L0 auto-dispatch: `requires_approval=false` AND `risk=low`.

## Current State (as of 2026-04-07)

- Active phase: Phase 7 `prod_ci` — canonical closure pending (117 commits ahead of `origin/main`).
- All COO Bootstrap steps (1-9) complete.
- Phase 10 Batch 1+2 merged (workspace inspection + repo artifact executors).
- Phase 9 ratified (`workspace_mutation_v1` approved).
- Agent Efficiency P0 (T-AE-01, T-AE-02, T-AE-03) closed; pytest PASS (3058 passed, 6 skipped).

## Key Files

| File | Role |
|------|------|
| `docs/11_admin/LIFEOS_STATE.md` | Canonical phase/WIP status |
| `docs/11_admin/BACKLOG.md` | Prioritized task queue (human-readable) |
| `config/tasks/backlog.yaml` | Machine-readable structured backlog |
| `config/governance/delegation_envelope.yaml` | COO authority bounds |
| `artifacts/plans/2026-03-05-coo-bootstrap-plan.md` | Superseded plan (historical) |

## Open Questions

None currently flagged.
