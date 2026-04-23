# Agent Roles Reference v1.0

**Status:** Active  
**Applies To:** All agents in the LifeOS system

---

## Actor Taxonomy

| Actor | Type | Authority |
| ----- | ---- | --------- |
| CEO | Human | Ultimate; sets strategic intent; approval authority |
| COO | AI agent (OpenClaw) | Operational; bounded, phase-scoped discretion |
| EA (Executing Agent) | AI agent (Claude Code, Codex) | Stateless worker; executes in worktrees |
| Antigravity | AI agent | Primary builder; full-scope implementation |
| Advisory | AI agents (Claude.ai, ChatGPT) | Read-only; not in operational loop |

## COO Autonomy Levels

Current active levels (L1 and L2 remain deferred — not yet operational):

| Level | Trigger | Action |
| ----- | ------- | ------ |
| L0 | `requires_approval=false` AND `risk=low` per delegation_envelope | Auto-dispatch without CEO review |
| L3 | Everything not eligible for L0 | Propose-and-wait for CEO approval |
| L4 | Architectural / governance / enumerated escalation triggers | Mandatory escalation to Council/CEO |

Fail-closed: unknown action category → L4. Everything not explicitly L0 defaults to L3.

## COO Memory Layers

1. `MEMORY.md` + memory files — persistent cross-session facts
2. `.context/wiki/` — derived context layer
3. `docs/11_admin/LIFEOS_STATE.md` — current operational state
4. `config/agent_roles/coo.md` — operational rules and invocation spec

## Provider Routing

| Provider | When to use |
| -------- | ----------- |
| `codex` | Bounded implementation tasks |
| `claude_code` | Complex multi-file changes |
| `gemini` | Analysis and research |
| `auto` | Uncertain; let orchestrator decide |
