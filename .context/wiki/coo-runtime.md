---
source_docs:
  - docs/03_runtime/COO_Runtime_Clean_Build_Spec_v1.1.md
  - docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
  - docs/11_admin/LIFEOS_STATE.md
source_commit_max: 8b2fa0d4c94ffca6229b86fb83ad98970d27be1f
authority: derived
page_class: status
concepts:
  - FSM
  - orchestration
  - COO runtime
  - build spec
---

## Summary

The COO runtime specs (`docs/03_runtime/`) describe a multi-agent orchestration system
with a FSM lifecycle, durable message store, budget enforcement, and Docker sandboxing.
The target architecture (`docs/00_foundations/LifeOS Target Architecture v2.3c.md`) describes
a CEO→COO→EA control plane using GitHub as relay bus. See Open Questions for conflict.

## Key Relationships

- [target-architecture](target-architecture.md) — current canonical architecture model
- [agent-roles](agent-roles.md) — actor definitions
- [mission-orchestration](mission-orchestration.md) — mission lifecycle
- Source: `docs/03_runtime/COO_Runtime_Clean_Build_Spec_v1.1.md`
- Source: `docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md`
- Source: `docs/00_foundations/LifeOS Target Architecture v2.3c.md`
- Source: `docs/11_admin/LIFEOS_STATE.md` — current operational state

## Authority Note

Canonical source for target state: `docs/00_foundations/LifeOS Target Architecture v2.3c.md`.
Canonical source for runtime spec history: `docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md`.
These sources conflict — see Open Questions. Current operational state sourced from
`docs/11_admin/LIFEOS_STATE.md`.

## Current Truth

**Implementation history (COO_Runtime_Core_Spec_v1.0.md):**
This spec describes a multi-agent FSM runtime with SQLite message bus, Engineer/QA/COO roles,
and Docker sandbox. States: `created → planning → executing → reviewing → completed | failed`.
Recoverable pauses: `paused_budget`, `paused_approval`. Budget enforcement: pre-call check,
post-call rollback, max 3 increase requests. Sandbox: Docker `--network none`, non-root.

**Canonical target (LifeOS Target Architecture v2.3c.md):**
COO validates CEO commands and creates GitHub issues as work orders. EAs execute stateless
from issue body via GitHub Actions. Results posted as comments; COO reconciles.

**Current operational state (LIFEOS_STATE.md):**
COO is currently invoked via OpenClaw gateway. FSM runtime is not the active execution model.

## Open Questions

> [!CONFLICT] `docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md` describes a SQLite message
> bus, Engineer/QA/COO multi-agent model, and Docker sandboxed execution as the runtime
> design. `docs/00_foundations/LifeOS Target Architecture v2.3c.md` (2026-04-17) describes
> a different model: CEO→COO→EA via GitHub issues and Actions.
>
> These may represent (a) implementation history vs. aspirational target, (b) different
> system layers, or (c) a superseded vs. current design. Resolution needed: which spec
> is canonical for the current operating model?
