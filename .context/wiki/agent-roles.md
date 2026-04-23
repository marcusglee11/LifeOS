---
source_docs:
  - config/agent_roles/coo.md
  - docs/00_foundations/LifeOS_Constitution_v2.0.md
  - docs/02_protocols/Intent_Routing_Rule_v1.1.md
last_updated: bf4d9ecd
concepts:
  - COO
  - CEO
  - doc_steward
  - Antigravity
  - sprint agents
  - autonomy levels
  - provider routing
---

# Agent Roles

## Summary

LifeOS uses a layered multi-agent model. The CEO provides strategic intent.
The COO decomposes objectives and dispatches work. Sprint agents (Claude Code,
Codex, Gemini) execute bounded tasks in isolated worktrees. The doc_steward
owns document governance. Antigravity is the primary builder.

## Key Relationships

- **CEO** → issues missions, approves non-reversible actions. See [governance-model](governance-model.md).
- **COO** → proposes tasks, generates dispatch artifacts, supervises outcomes. Never writes product code directly.
- **Sprint agents** (Claude Code / Codex / Gemini) → own repo edits, `start_build.py`, `close_build.py`, commits, merges. Bounded scope only.
- **doc_steward** → agent (Antigravity or successor) owning all doc operations. See [doc-stewardship](doc-stewardship.md).
- **Antigravity** → primary builder; runs long-horizon builds. Claude Code = sprint insertion team for focused work.

## COO Autonomy Model

| Level | Permitted Actions |
|-------|------------------|
| L0 | Read-only, analysis, memory updates, auto-dispatch of `requires_approval=false, risk=low` tasks |
| L3 | Propose-and-wait for non-eligible actions |
| L4 | Mandatory escalation (strategy change, irreversible action, protected path, budget threshold, policy violation) |

## COO Memory Layers

- Layer 0: `MEMORY.md` — persistent cross-session index
- Layer 1: structured memory via `coo-memory.py`
- Layer 2: checkpoints per mission
- Layer 3: hygiene reports

## Provider Routing (COO dispatch)

| Provider | Use Case |
|----------|----------|
| `codex` | Bounded impl/test tasks |
| `claude_code` | Complex multi-file changes |
| `gemini` | Analysis, content generation |
| `auto` | Uncertain — COO must include rationale |

## COO Critical Rules

- Never assert execution state (started/completed/pushed) without runtime evidence.
- When declining, cite specific blocker (policy rule, missing evidence, protected path, blocked dependency).
- Optimize for advancing approved objectives; prefer dispatch over deferral when policy permits.

## Current State

Live COO operational via OpenClaw (gpt-5.3-codex). Gateway at `127.0.0.1:18789`.
COO invocation: `openclaw agent --agent main --message <json_str> --json`;
response at `result.payloads[0].text`. See [openclaw-integration](openclaw-integration.md).

## Open Questions

None currently flagged.
