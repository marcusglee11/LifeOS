---
source_docs:
  - docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md
  - runtime/mission/
  - runtime/orchestration/
last_updated: bf4d9ecd
concepts:
  - mission
  - orchestration
  - Tier-2
  - Tier-3
  - executor
  - pipeline
---

# Mission Orchestration

## Summary

LifeOS uses a tiered orchestration model. Tier-3 is the mission registry
(long-horizon goals). Tier-2 is execution orchestration (task dispatch,
sandboxed execution, result collection). Sprint agents operate at Tier-1
(bounded file-level changes in isolated worktrees).

## Key Relationships

- **[coo-runtime](coo-runtime.md)** — runtime engine drives Tier-2 execution.
- **[agent-roles](agent-roles.md)** — COO plans; Engineer/QA execute.
- **[backlog-task-system](backlog-task-system.md)** — missions originate from approved tasks.
- **Source**: `runtime/mission/` (Tier-3 registry), `runtime/orchestration/` (Tier-2 execution)

## Tier Model

| Tier | Layer | Owner | Scope |
|------|-------|-------|-------|
| Tier-3 | Mission registry | COO | Long-horizon goals, multi-sprint |
| Tier-2 | Execution orchestration | COO Runtime | Task dispatch, sandbox, result collection |
| Tier-1 | Sprint execution | Sprint agents | Bounded file edits in worktrees |

## Executor Types (Phase 10+)

| Executor | Capability | Status |
|----------|-----------|--------|
| `workspace_mutation_v1` | File read/write ops | Ratified (Phase 9) |
| `workspace_inspection_v1` | Repo inspection | Merged (Phase 10 Batch 1) |
| `repo_artifact_v1` | Artifact management | Merged (Phase 10 Batch 2) |

## Mission Lifecycle (Tier-3)

```
mission created → COO decomposes → tasks proposed → approved
→ ExecutionOrders dispatched → Tier-2 executes → results collected
→ mission updated → next iteration or completion
```

## Current State

Phase 10 Batch 1+2 executors live on main. Tier-2 orchestration active;
COO invoking via OpenClaw gateway. See [coo-runtime](coo-runtime.md) for
runtime FSM details and [backlog-task-system](backlog-task-system.md)
for current phase status.

## Open Questions

None currently flagged.
