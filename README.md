# LifeOS

> A personal operating system that makes Marcus the CEO of his life.

**Current Status**: Live COO operations with repo-backed governance, issue-based execution, and ongoing May 2026 bus/hub/runtime documentation reconciliation.

---

## What is LifeOS?

LifeOS exists to extend Marcus's operational reach into the world. It converts CEO intent into COO operations, agent execution, and auditable evidence.

The system is designed to **augment and amplify human agency and judgment**, not originate strategic intent.

## Current operating model

LifeOS now runs as a multi-surface operating system:

| Surface | Role | What lives there |
|---|---|---|
| `LifeOS` | Canonical doctrine, runtime, state, and documentation | Constitution, protocols, runtime code, canonical admin/state docs, derived corpus/wiki surfaces |
| `lifeos-operational-bus` | Operational work-order and evidence bus | Cross-repo issues, execution receipts, dispatch/merge gates, runtime/agent control trackers |
| `lifeos-common-hub` | Shared reusable standards | Extracted schemas, common skills, cross-agent protocol assets after they stabilise |

GitHub issues are the operational bus: they hold work orders, evidence, review receipts, continuation batons, and closure records. Chat memory and agent transcripts help operators navigate, but they are not completion truth.

## Roles

| Role | Responsibility |
|---|---|
| **CEO** | Defines intent, values, priorities, and final authority |
| **COO** | Converts intent into bounded work, manages evidence gates, escalates real decisions |
| **Executing agents / workers** | Perform scoped implementation, verification, review, or maintenance tasks |
| **Advisory agents** | Provide critique, review, or architecture assurance; they inform decisions but do not own truth |

## Authority and conflict rules

When surfaces disagree, use this order:

1. Canonical repo docs and governance records in `LifeOS`.
2. Live GitHub issue/PR state and verified receipts.
3. Derived surfaces such as `docs/LifeOS_Strategic_Corpus.md` and `.context/wiki/`.
4. Chat memory, local notes, and agent summaries.

The strategic corpus and wiki are navigation aids. They are useful, but they are derived. Repo canon wins on conflict.

## Operator / AI read order

A new operator or AI should read in this order:

1. This `README.md` for the current map.
2. [`docs/INDEX.md`](docs/INDEX.md) for the authoritative documentation index.
3. [`docs/08_manuals/LifeOS_Operator_Onboarding.md`](docs/08_manuals/LifeOS_Operator_Onboarding.md) for the operator entry chain and role boundaries.
4. [`docs/LifeOS_Strategic_Corpus.md`](docs/LifeOS_Strategic_Corpus.md) for a derived high-context snapshot.
5. [`docs/11_admin/LIFEOS_STATE.md`](docs/11_admin/LIFEOS_STATE.md) for current focus, WIP, blockers, and recent state.
6. [`docs/00_foundations/LifeOS Target Architecture v2.3c.md`](docs/00_foundations/LifeOS%20Target%20Architecture%20v2.3c.md) for the current canonical target architecture.
7. Root agent guidance: [`CLAUDE.md`](CLAUDE.md), [`AGENTS.md`](AGENTS.md), [`GEMINI.md`](GEMINI.md).
8. [`.context/REPO_MAP.md`](.context/REPO_MAP.md) for repository layout when available.

## Repository structure

- `docs/`: canonical governance, protocols, runtime specs, manuals, admin state, and derived navigation surfaces.
- `runtime/`: LifeOS COO runtime implementation.
- `recursive_kernel/`: recursive builder agent runtime.
- `doc_steward/`: document stewardship automation and validators.
- `scripts/`: maintenance, workflow, and quality-gate utilities.
- `config/`: governance, backlog, schema, model, and workflow configuration.
- `artifacts/`: agent-generated plans, packets, receipts, and evidence.
- `tests/`, `tests_doc/`, `runtime/tests/`: project, documentation, and runtime tests.
- Root guidance files: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`.

## Before changing docs

Check `config/docs/authority_registry.yaml` before promoting or editing documentation authority. Do not promote proposal-only, archive, wiki, corpus, or chat-memory material into canon without explicit evidence and approval.
