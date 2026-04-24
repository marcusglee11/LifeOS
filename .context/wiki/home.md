---
source_docs:
  - docs/INDEX.md
  - docs/00_foundations/LifeOS_Constitution_v2.0.md
  - docs/10_meta/architecture_decisions/INDEX.md
source_commit_max: acd95ae997c49e76a9e64d566d3e9ef9d0d69ffc
authority: derived
page_class: evergreen
concepts:
  - navigation
  - authority chain
  - wiki home
---

## Summary

Agent navigation landing page for the LifeOS wiki layer. Start here. The wiki is a
**derived, non-authoritative** layer — canonical docs under `docs/**` always win.
For current operational state, read `docs/11_admin/LIFEOS_STATE.md` directly.

## Key Relationships

**Authority chain (top to bottom):**
- `docs/00_foundations/LifeOS_Constitution_v2.0.md` — supreme governing document
- `docs/11_admin/LIFEOS_STATE.md` — current phase and WIP (volatile; read directly)
- `docs/INDEX.md` — navigation index for all canonical docs
- `docs/10_meta/architecture_decisions/INDEX.md` — ratified architecture decision register (ADR-001, ADR-002)

**Wiki pages:**
- [target-architecture](target-architecture.md) — CEO→COO→EA control-plane design
- [governance-model](governance-model.md) — hard invariants, Council, amendment
- [agent-roles](agent-roles.md) — actor taxonomy, COO autonomy levels
- [coo-runtime](coo-runtime.md) — COO runtime FSM and orchestration specs
- [openclaw-integration](openclaw-integration.md) — OpenClaw gateway, invocation
- [doc-stewardship](doc-stewardship.md) — document steward protocol, DAP
- [mission-orchestration](mission-orchestration.md) — mission lifecycle, executors
- [protocols-index](protocols-index.md) — navigation index of active protocols
- [backlog-task-system](backlog-task-system.md) — backlog, task proposals, COO flow
- [build-workflow](build-workflow.md) — worktree isolation, branch naming, lifecycle

## Authority Note

Canonical source: `docs/INDEX.md` and `docs/00_foundations/LifeOS_Constitution_v2.0.md`.
This page is a navigation aid only. All substantive claims require canonical doc verification.

## Current Truth

`docs/INDEX.md` is the canonical navigation surface for the documentation corpus.
Architecture decision records live in `docs/10_meta/architecture_decisions/INDEX.md`.
For active phase, blockers, and current operational state, read `docs/11_admin/LIFEOS_STATE.md`
directly. This page is a derived landing page only.

## Open Questions

None.
