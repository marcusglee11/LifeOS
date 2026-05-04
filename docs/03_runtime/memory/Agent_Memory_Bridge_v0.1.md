# Agent Memory Bridge v0.1

**Status:** Canonical bridge-boundary documentation; no runtime implementation
**Authority:** LifeOS Memory and Knowledge Architecture v0.5; GitHub work order `lifeos-operational-bus#33`
**Scope:** Hermes, OpenClaw, LifeOS, Obsidian memory and knowledge surfaces
**Classification:** INTERNAL
**Review basis:** AA review `lifeos-operational-bus#31`, verdict `APPROVE_WITH_AMENDMENTS`, final status satisfied
for local note/navigation bridge

---

## 1. Purpose

This document promotes the AA-satisfied Obsidian agent memory bridge into repo-native LifeOS documentation.

The bridge has one narrow job: make Obsidian useful as a human-facing knowledge and navigation surface without
letting it become an ungoverned runtime memory, governance authority, or automation trigger.

This document does **not** add automation, watcher behavior, runtime ingestion, vector-memory import,
native-memory mutation, or automatic promotion.

## 2. Source evidence

Primary work order:

- `lifeos-operational-bus#33`: <https://github.com/marcusglee11/lifeos-operational-bus/issues/33>

AA review trail:

- AA review issue: <https://github.com/marcusglee11/lifeos-operational-bus/issues/31>
- Amendment receipt: <https://github.com/marcusglee11/lifeos-operational-bus/issues/31#issuecomment-4368327276>
- Final AA status receipt: <https://github.com/marcusglee11/lifeos-operational-bus/issues/31#issuecomment-4368351481>

Local source artifacts captured by the work order:

| Source artifact | sha256 |
| --- | --- |
| `/mnt/c/Users/cabra/Projects/ObsidianVault/LifeOS/Knowledge Framework/Agent Memory Bridge.md` | `a7e9ae96ee352178627c0cae93f47e21d4c4bdd0935089d2e322c1090c1e8321` |
| `/mnt/c/Users/cabra/Projects/ObsidianVault/LifeOS/Knowledge Framework/AA Review Spec - Agent Memory Bridge.md` | `5d05abc22be3d7fc9c89dd907db749cc609f7df6d1e5fea8a68c9136db9449fa` |
| `/home/cabra/.openclaw/workspace/memory/2026-05-04-obsidian-bridge.md` | `7163d2c67a40f2bf08760c81382be9b18f30b8432d3ac78fb86a4994d19457bd` |

Post-review COO structured-memory decision pointer:

- `obsidian-bridge-aa-review-20260504`

## 3. Authority model

Authority precedence, highest to lowest:

1. GitHub and canonical LifeOS repo documentation for reviewed work orders, architecture, governance, and programme state.
2. COO structured memory for durable facts and decisions written through an approved gate with readback.
3. OpenClaw runtime grounding under `/home/cabra/.openclaw/workspace/`.
4. Hermes compact persistent memory and Hermes skills as runtime and procedural hints.
5. Obsidian notes as human-facing navigation, summaries, maps, and working context.

| Layer | Role | Authority |
| --- | --- | --- |
| GitHub / LifeOS repo docs | Authority-bearing coordination, review trail, architecture, governance, and programme state | Highest authority for governed LifeOS work |
| COO structured memory | Durable fact and decision records written through an approved gate | Authoritative only after review, gate write, and readback |
| OpenClaw runtime grounding | OpenClaw local memory and workspace context | Runtime grounding for OpenClaw; not cross-system governance by itself |
| Hermes compact memory / skills | Always-loaded hints and reusable procedures | Runtime/procedural hints only; not canonical policy by themselves |
| Obsidian vault | Human-facing knowledge, summaries, maps, handoffs, and indexes | Navigation and reflection layer only unless content is promoted through the correct authority path |

## 4. Obsidian role

Obsidian is the **knowledge display and working-note layer**, not the LifeOS control plane.

Allowed Obsidian uses:

- session summaries
- workstream handoffs
- decision digests
- source maps
- reading notes
- user-facing artifacts
- indexes linking to canonical GitHub, LifeOS, COO, Hermes, or OpenClaw evidence

Forbidden Obsidian uses by default:

- authority-bearing execution orders
- runtime memory writes
- governance changes
- canonical architecture decisions
- approval receipts
- external/public actions
- automatic promotion into Hermes, OpenClaw, COO, or LifeOS state

Obsidian may mirror, summarize, and link authority-bearing surfaces. It must not replace them.

## 5. Promotion controls

Pre-review memory or procedural writes related to this bridge are provisional pointers only. They are not approved
governance policy, not durable LifeOS memory, and not evidence that a source has been promoted.

Promotion from Obsidian or Obsidian-derived notes requires all of the following:

1. Review appropriate to the target authority surface.
2. Classification and source-reference check.
3. Mechanical secret/classification scan over the candidate content.
4. Path plus content hash or excerpt hash for each local artifact being promoted.
5. Explicit invocation of the correct write gate or repo workflow.
6. Readback from the destination surface before claiming promotion.

Promotion tags such as `#promote/...` are triage/request metadata only. Tags must never trigger automatic writes.

## 6. Destination-specific rules

| Destination | Required path | Explicit non-authority |
| --- | --- | --- |
| Hermes durable memory | Hermes `memory` tool, only for compact durable facts that reduce future steering | No raw note import, task-progress logs, archive dumps, or canonical policy claims |
| Hermes procedural memory | Hermes `skill_manage`, only for reusable procedures | No governance authority by skill text alone |
| OpenClaw runtime grounding | OpenClaw workspace memory surface with source metadata | No cross-system governance authority by local runtime note alone |
| COO structured memory | Approved COO structured-memory gate with readback | No pre-review or ungated durable-write authority |
| LifeOS canonical docs | LifeOS repo work-order, branch, PR, validation, review, and merge path | No vault-only canonical policy |

If content affects programme architecture, governance, memory authority, writer boundaries, approval capture,
or canonical/proposal classification, the LifeOS repo PR path is required before it becomes canonical.

## 7. Retrieval policy

When answering memory or knowledge questions, agents should check authority surfaces in this order:

1. GitHub and canonical LifeOS repo docs for governed programme facts, review trails, and authority-bearing work state.
2. COO structured memory for durable facts and decisions written through an approved gate.
3. OpenClaw runtime grounding for OpenClaw-local context.
4. Hermes compact memory and skills for runtime hints and procedural recall.
5. Obsidian for human-facing notes, maps, summaries, and personal knowledge.

Answers should cite source paths or URLs when authority matters.

## 8. Non-goals

This work does not authorize or implement:

- Obsidian auto-sync into LifeOS, Hermes, OpenClaw, or COO memory.
- Obsidian watcher automation.
- Runtime ingestion from the Obsidian vault.
- Vector-memory import, ranking, or reranking.
- Automatic durable memory writes.
- Automatic promotion based on tags.
- Native-memory mutation.
- New Gateway, MCP, or runtime tools.
- Broad promotion of Obsidian vault contents.

## 9. Relationship to existing memory architecture

This bridge is a companion boundary document for
`docs/03_runtime/memory/LIFEOS_MEMORY_KNOWLEDGE_ARCHITECTURE_v0.5.md` and
`docs/03_runtime/memory/LIFEOS_MEMORY_PHASE1_OPERATING_CONTRACT.md`.

If this document conflicts with the LifeOS Memory and Knowledge Architecture v0.5, the architecture document wins
unless a later reviewed PR explicitly changes the authority model.

The bridge narrows Obsidian's role; it does not expand runtime write authority.

## 10. Current local vault binding

Observed local Obsidian vault path:

```text
/mnt/c/Users/cabra/Projects/ObsidianVault
```

This path is recorded for local navigation and source evidence only. It is not a runtime ingestion binding and does
not authorize automation.
