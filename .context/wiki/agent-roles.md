---
source_docs:
  - docs/00_foundations/Agent_Roles_Reference_v1.0.md
  - docs/00_foundations/LifeOS_Constitution_v2.0.md
  - docs/02_protocols/Intent_Routing_Rule_v1.1.md
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
source_commit_max: c7df98632ed6dfee99daaada103cd613dc630501
authority: derived
page_class: evergreen
concepts:
  - COO
  - CEO
  - EA
  - COO substrates
  - CSO
  - autonomy levels
  - provider routing
  - delegation tiers
---

## Summary

LifeOS uses a layered multi-agent model. CEO provides strategic intent and holds ultimate authority; CEO authority is exercised by directing the COO, not by direct state mutation. COO is a control-plane substrate role with bounded, phase-scoped discretion. EAs (Claude Code, Codex) execute bounded tasks in worktrees. Advisory agents remain outside the operational loop. A CSO tier from `Intent_Routing_Rule_v1.1` remains provisional / WIP, not canon.

## Key Relationships

- [target-architecture](target-architecture.md) — control-plane flow for these actors
- [governance-model](governance-model.md) — CEO supremacy and invariants
- [openclaw-integration](openclaw-integration.md) — COO substrate details
- Source: `docs/00_foundations/Agent_Roles_Reference_v1.0.md` — autonomy model, memory layers
- Source: `docs/00_foundations/LifeOS Target Architecture v2.3c.md` — actor taxonomy, state mutation rules
- Source: `docs/02_protocols/Intent_Routing_Rule_v1.1.md` — delegation tiers (WIP)

## Authority Note

Canonical sources: `docs/00_foundations/LifeOS Target Architecture v2.3c.md` and ratified governance docs. `docs/00_foundations/Agent_Roles_Reference_v1.0.md` is an active orientation reference only and loses on conflict. `docs/02_protocols/Intent_Routing_Rule_v1.1.md` is WIP/non-canonical; content from it is provisional.

## Current Truth

**Actor taxonomy:**

| Actor | Authority | Notes |
|-------|-----------|-------|
| CEO (human) | Ultimate | Sets objectives; directs COO; never writes canonical state directly |
| COO (active substrate) | Operational | Sole execution agent for canonical state mutations; bounded, phase-scoped discretion |
| COO substrates | Orientation only | OpenClaw, Hermes, or successor adapters; replaceable via adapter layer |
| EA (Claude Code, Codex) | Execution | Stateless; triggered via GitHub Actions; evidence producers, not state mutators |
| Advisory (Claude.ai, ChatGPT) | None | Read-only; not in operational loop |

**Google Drive / Workspace:** ratified non-canonical surface (2026-04-26). May be used for drafts, briefings, advisory communication. Not canonical state; no operational effect until captured into GitHub by the active COO path.

**Delegation tiers (Intent_Routing_Rule v1.1, WIP):** T0=CEO, T1=CSO (intent interpretation, deadlock resolution), T2=Councils/Reviewers, T3=Agents, T4=Deterministic rules. Fail-closed: ambiguity escalates upward.

**COO autonomy levels:** L0 (auto-dispatch: `requires_approval=false` AND `risk=low`) → L3 (propose-and-wait) → L4 (mandatory escalation). L1/L2 deferred.

**COO memory layers:** `MEMORY.md` + memory files → `.context/wiki/` → `docs/11_admin/LIFEOS_STATE.md` → `config/agent_roles/coo.md`.

**Provider routing:** `codex` (bounded impl), `claude_code` (complex multi-file), `gemini` (analysis), `auto` (uncertain).

## Open Questions

> [!CONFLICT] `Intent_Routing_Rule_v1.1.md` introduces a CSO role (T1) not present in `Agent_Roles_Reference_v1.0.md` or `LifeOS Target Architecture v2.3c.md` actor taxonomy. CSO is WIP/non-canonical; its operational status is unresolved until the rule is ratified.
