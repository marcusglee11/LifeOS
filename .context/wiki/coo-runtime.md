---
source_docs:
  - docs/03_runtime/COO_Runtime_Clean_Build_Spec_v1.1.md
  - docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md
  - runtime/engine.py
last_updated: bf4d9ecd
concepts:
  - FSM
  - message bus
  - budget enforcement
  - sandbox
  - orchestration
  - COO runtime
---

# COO Runtime

## Summary

The COO Runtime is a multi-agent orchestration system: CEO issues missions,
COO plans, Engineer codes, QA reviews. All communication flows through a
durable SQLite message bus. Hard budget enforcement and network-isolated Docker
sandboxing are non-negotiable constraints, not configuration.

## Key Relationships

- **[agent-roles](agent-roles.md)** — defines who does what in the pipeline.
- **[mission-orchestration](mission-orchestration.md)** — Tier-2/3 mission lifecycle above the runtime.
- **Source specs** → `docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md`, `COO_Runtime_Clean_Build_Spec_v1.1.md`

## FSM States

```
created → planning → executing → reviewing → completed
                                           ↘ failed
         paused_budget / paused_approval (recoverable)
```

## Message Bus

- Transport: SQLite (no OpenAI runtime dependency)
- Message kinds: `TASK`, `RESULT`, `STREAM`, `ERROR`, `APPROVAL`, `SANDBOX_EXECUTE`, `CONTROL`, `QUESTION`, `SYSTEM`
- Backpressure: hard pause at >50 pending messages; resume at <30
- Context window: mission desc + last 5 messages (no summarization in v1.0)

## Budget Enforcement

- Safety margin: 0.95 (stops at 95% of budget cap)
- Pre-call check: `worst_case = max_tokens × price_per_1k_output`; if `spent + worst_case > cap × 0.95` → `paused_budget`
- Post-call rollback: if actual cost exceeds limit, revert artifacts and spent counter
- Max 3 budget increase requests per mission

## Sandbox

```
docker run --network none --user 1000:1000 \
  --security-opt=no-new-privileges -m 512m --cpus 0.5
```

Non-root, resource-limited, fully network-isolated. No exceptions.

## Crash Recovery

- Stale messages reclaimed after 5-min heartbeat timeout
- `sandbox_runs` abandoned if `started_at < now - 10min` → marked failed
- Orchestrator kill+restart is a tested scenario

## Current State

Spec at v1.1 Clean Build. 4 active build threads: Runtime Core, User Surface,
Governance, Productisation. Phase 0-4 implementation pipeline. Phase 0 = core
DB + message store.

## Open Questions

None currently flagged.
