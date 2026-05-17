---
source_docs:
  - docs/INDEX.md
  - docs/00_foundations/LifeOS_Constitution_v2.0.md
  - docs/10_meta/architecture_decisions/INDEX.md
source_commit_max: d20b026591ace96ba926735b1f48bd6c8c5c19f5
derived_edit_mode: generated
source_command: python3 scripts/wiki/refresh_wiki.py
source_change_ref: https://github.com/marcusglee11/LifeOS/pull/134
authority: derived
page_class: evergreen
concepts:
  - navigation
  - authority chain
  - wiki home
---

## Summary

Agent navigation landing page for the LifeOS wiki layer. Start here, then verify substantive claims against canonical docs under `docs/**`. The wiki is **derived and non-authoritative**; canonical docs and live GitHub readback win.

## Key Relationships

**Authority chain (top to bottom):**
- `docs/00_foundations/LifeOS_Constitution_v2.0.md` — supreme governing document
- `docs/11_admin/LIFEOS_STATE.md` — current phase and WIP (volatile; read directly)
- `docs/INDEX.md` — navigation index for all canonical docs
- `docs/10_meta/ARCHITECTURE_SOURCE_OF_TRUTH.md` — architecture authority map, including bus/hub/runtime reconciliation
- `docs/10_meta/architecture_decisions/INDEX.md` — ratified architecture decision register

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

Canonical source: `docs/INDEX.md` and `docs/00_foundations/LifeOS_Constitution_v2.0.md`. This page is a navigation aid only. All architecture, governance, and completion claims require canonical doc or GitHub readback.

## Current Truth

`docs/INDEX.md` is the canonical navigation surface for the documentation corpus. Current bus/hub/runtime reconciliation is represented in canonical LifeOS meta/admin docs and linked review packets; generated corpora and wiki pages remain derived.

Architecture decision records live in `docs/10_meta/architecture_decisions/INDEX.md`. For active phase, blockers, and current operational state, read `docs/11_admin/LIFEOS_STATE.md` directly.

## Open Questions

None.
