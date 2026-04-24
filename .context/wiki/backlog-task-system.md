---
source_docs:
  - docs/11_admin/LIFEOS_STATE.md
  - docs/11_admin/BACKLOG.md
  - docs/02_protocols/Intent_Routing_Rule_v1.1.md
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
source_commit_max: bf4d9ecd01e5124584e96a42b95f16c7f39e3fd2
authority: derived
page_class: status
concepts:
  - backlog
  - task proposal
  - delegation
  - COO workflow
---

## Summary

The COO reviews the structured backlog and proposes tasks. CEO approves proposals, which
become ExecutionOrders dispatched to sprint agents. `docs/11_admin/LIFEOS_STATE.md` is the
canonical source for current phase, active WIP, and blockers.

## Key Relationships

- [agent-roles](agent-roles.md) — COO autonomy levels that govern proposal routing
- [openclaw-integration](openclaw-integration.md) — how COO proposals are invoked
- [governance-model](governance-model.md) — CEO approval authority
- Source: `docs/11_admin/LIFEOS_STATE.md` — current phase and WIP (volatile)
- Source: `docs/11_admin/BACKLOG.md` — prioritized work items
- Source: `docs/02_protocols/Intent_Routing_Rule_v1.1.md` — routing and autonomy rules

## Authority Note

Canonical sources: `docs/11_admin/LIFEOS_STATE.md` (current state) and
`docs/11_admin/BACKLOG.md` (backlog). This page summarizes structure only; read those
docs directly for current operational state.

## Current Truth

**Proposal flow:**
1. COO reads backlog → proposes `task_proposal.v1` YAML via `lifeos coo propose`
2. CEO approves → `ExecutionOrder` YAML created
3. Sprint agent receives order + worktree → builds in isolation
4. `close_build` gates (tests, quality, doc stewardship) → merged to main

**Auto-dispatch (L0):** `requires_approval=false` AND `risk=low` per `Intent_Routing_Rule_v1.1.md`.

**Key files:** `docs/11_admin/LIFEOS_STATE.md` (current phase), `docs/11_admin/BACKLOG.md`
(prioritized queue), `artifacts/active_branches.json` (in-flight builds).

## Open Questions

For current active phase, blockers, and WIP, read `docs/11_admin/LIFEOS_STATE.md` directly —
this page (page_class: status) only summarizes the structural flow, not current state values.
