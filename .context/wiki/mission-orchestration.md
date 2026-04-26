---
source_docs:
  - docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
  - docs/11_admin/LIFEOS_STATE.md
source_commit_max: 8b2fa0d4c94ffca6229b86fb83ad98970d27be1f
authority: derived
page_class: status
concepts:
  - mission
  - orchestration
  - executor
  - pipeline
  - tier model
---

## Summary

LifeOS orchestrates work through a tiered mission model (runtime specs) and a phased
CEO→COO→EA control plane (target architecture). These two models may represent compatible
layers or competing designs — see Open Questions.

## Key Relationships

- [coo-runtime](coo-runtime.md) — FSM, message bus, and runtime details
- [agent-roles](agent-roles.md) — actor types for each tier
- [target-architecture](target-architecture.md) — current canonical control-plane model
- Source: `docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md`
- Source: `docs/00_foundations/LifeOS Target Architecture v2.3c.md`
- Source: `docs/11_admin/LIFEOS_STATE.md` — executor merge status

## Authority Note

Canonical source for target state: `docs/00_foundations/LifeOS Target Architecture v2.3c.md`.
Canonical source for runtime spec: `docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md`.
These sources conflict — see Open Questions. Executor merge status sourced from
`docs/11_admin/LIFEOS_STATE.md`.

## Current Truth

**Implementation history (COO_Runtime_Core_Spec_v1.0.md — Tier model):**
- Tier-3: mission registry (long-horizon goals, COO)
- Tier-2: execution orchestration (task dispatch, result collection)
- Tier-1: sprint execution (bounded file edits in worktrees)

Executor types (per spec): `workspace_mutation_v1`, `workspace_inspection_v1`, `repo_artifact_v1`.
Merge status per `docs/11_admin/LIFEOS_STATE.md`: `workspace_mutation_v1` ratified;
`workspace_inspection_v1` and `repo_artifact_v1` merged (Phase 10).

**Canonical target (LifeOS Target Architecture v2.3c.md):**
CEO→COO→EA via GitHub issues as work orders. EAs are stateless workers triggered by
GitHub Actions. COO reconciles results and reports to CEO. COO Commons provides
deterministic shared-services layer (webhook ingestion, schema validation, phase config).

## Open Questions

> [!CONFLICT] `docs/03_runtime/COO_Runtime_Core_Spec_v1.0.md` describes a Tier-1/2/3
> orchestration model with a SQLite message bus and FSM. `docs/00_foundations/LifeOS Target
> Architecture v2.3c.md` describes a CEO→COO→EA model with GitHub as the relay bus. These
> may be (a) compatible layerings at different abstraction levels, (b) old spec vs. target
> state, or (c) competing designs. Resolution requires explicit Council ruling or doc update.
