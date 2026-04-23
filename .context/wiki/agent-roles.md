---
source_docs:
  - docs/00_foundations/Agent_Roles_Reference_v1.0.md
  - docs/00_foundations/LifeOS_Constitution_v2.0.md
  - docs/02_protocols/Intent_Routing_Rule_v1.1.md
  - docs/00_foundations/LifeOS Target Architecture v2.3c.md
source_commit_max: 7c3464d6a229e8530cda12c3bade71d027a7fe6a
authority: derived
page_class: evergreen
concepts:
  - COO
  - CEO
  - EA
  - Antigravity
  - autonomy levels
  - provider routing
---

## Summary

LifeOS uses a layered multi-agent model. CEO provides strategic intent. COO (OpenClaw)
decomposes objectives and dispatches work. EAs (Claude Code, Codex) execute bounded tasks
in worktrees. Antigravity is the primary builder for full-scope implementation work.

## Key Relationships

- [target-architecture](target-architecture.md) — control-plane flow for these actors
- [governance-model](governance-model.md) — CEO supremacy and invariants
- [openclaw-integration](openclaw-integration.md) — COO substrate details
- Source: `docs/00_foundations/Agent_Roles_Reference_v1.0.md` — autonomy model
- Source: `docs/00_foundations/LifeOS Target Architecture v2.3c.md` — actor taxonomy

## Authority Note

Canonical sources: `docs/00_foundations/Agent_Roles_Reference_v1.0.md` and
`docs/00_foundations/LifeOS Target Architecture v2.3c.md`. Those documents win on conflict.

## Current Truth

**Actor taxonomy:**

| Actor | Authority | Notes |
|-------|-----------|-------|
| CEO (human) | Ultimate | Sets objectives; approval authority |
| COO (OpenClaw) | Operational | Bounded, phase-scoped discretion |
| EA (Claude Code, Codex) | Execution | Stateless; triggered via GitHub Actions |
| Antigravity | Implementation | Primary builder; full-scope work |
| Advisory (Claude.ai, ChatGPT) | None | Read-only; not in operational loop |

**COO autonomy levels (current):** L0 (auto-dispatch: `requires_approval=false` AND `risk=low`
per delegation_envelope) → L3 (propose-and-wait for everything else) → L4 (mandatory
escalation for architectural/governance triggers). L1/L2 remain deferred.

**Provider routing:** `codex` (bounded impl), `claude_code` (complex multi-file),
`gemini` (analysis), `auto` (uncertain, let orchestrator decide).

## Open Questions

None.
