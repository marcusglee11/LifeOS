---
source_docs:
  - docs/00_foundations/Agent_Roles_Reference_v1.0.md
  - docs/00_foundations/LifeOS_Constitution_v2.0.md
  - docs/02_protocols/Intent_Routing_Rule_v1.1.md
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
source_commit_max: 310aac1e0eda5cb96842d8a596bbadacbf4935f9
authority: derived
page_class: evergreen
concepts:
  - COO
  - CEO
  - EA
  - Antigravity
  - CSO
  - autonomy levels
  - provider routing
  - delegation tiers
---

## Summary

LifeOS uses a layered multi-agent model. CEO provides strategic intent. COO (OpenClaw) decomposes objectives and dispatches work. EAs (Claude Code, Codex) execute bounded tasks in worktrees. Antigravity is the primary builder for full-scope implementation work. A CSO tier (T1, provisional) interprets CEO intent and resolves deadlocks per Intent_Routing_Rule v1.1.

## Key Relationships

- [target-architecture](target-architecture.md) — control-plane flow for these actors
- [governance-model](governance-model.md) — CEO supremacy and invariants
- [openclaw-integration](openclaw-integration.md) — COO substrate details
- Source: `docs/00_foundations/Agent_Roles_Reference_v1.0.md` — autonomy model, memory layers
- Source: `docs/00_foundations/LifeOS Target Architecture v2.3c.md` — actor taxonomy
- Source: `docs/02_protocols/Intent_Routing_Rule_v1.1.md` — delegation tiers (WIP)

## Authority Note

Canonical sources: `docs/00_foundations/Agent_Roles_Reference_v1.0.md` and `docs/00_foundations/LifeOS Target Architecture v2.3c.md`. Those documents win on conflict. `docs/02_protocols/Intent_Routing_Rule_v1.1.md` is WIP/non-canonical; content from it is provisional.

## Current Truth

**Actor taxonomy:**

| Actor | Authority | Notes |
|-------|-----------|-------|
| CEO (human) | Ultimate | Sets objectives; approval authority |
| COO (OpenClaw) | Operational | Bounded, phase-scoped discretion |
| EA (Claude Code, Codex) | Execution | Stateless; triggered via GitHub Actions |
| Antigravity | Implementation | Primary builder; full-scope work |
| Advisory (Claude.ai, ChatGPT) | None | Read-only; not in operational loop |

**Delegation tiers (Intent_Routing_Rule v1.1, WIP):** T0=CEO, T1=CSO (intent interpretation, deadlock resolution), T2=Councils/Reviewers, T3=Agents, T4=Deterministic rules. Fail-closed: ambiguity escalates upward.

**COO autonomy levels:** L0 (auto-dispatch: `requires_approval=false` AND `risk=low`) → L3 (propose-and-wait) → L4 (mandatory escalation). L1/L2 deferred.

**COO memory layers:** `MEMORY.md` + memory files → `.context/wiki/` → `docs/11_admin/LIFEOS_STATE.md` → `config/agent_roles/coo.md`.

**Provider routing:** `codex` (bounded impl), `claude_code` (complex multi-file), `gemini` (analysis), `auto` (uncertain).

## Open Questions

> [!CONFLICT] `Intent_Routing_Rule_v1.1.md` introduces a CSO role (T1) not present in `Agent_Roles_Reference_v1.0.md` or `LifeOS Target Architecture v2.3c.md` actor taxonomy. CSO is WIP/non-canonical; its operational status is unresolved until the rule is ratified.
