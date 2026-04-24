# Agent Roles Reference v1.0

**Status:** Active orientation reference — non-authoritative  
**Authority:** Derived/supporting only. On conflict, `docs/00_foundations/LifeOS Target Architecture v2.3c.md`, `docs/01_governance/COO_Operating_Contract_v1.0.md`, and ratified governance docs win.  
**Applies To:** Orientation for agents in the LifeOS system

---

## Actor Taxonomy

| Actor | Type | Authority |
| ----- | ---- | --------- |
| CEO | Human | Ultimate; sets strategic intent; approval authority |
| COO | AI substrate / control-plane agent | Operational decision-maker with bounded, phase-scoped discretion; active substrate determined by canonical architecture and operating state |
| COO substrates | OpenClaw, Hermes, or successor adapters | Candidate / replaceable substrates; only the active COO has mutation authority |
| EA (Executing Agent) | AI execution worker | Stateless worker; executes bounded tasks in worktrees |
| Advisory | AI agents such as Claude.ai / ChatGPT | Read-only advisory role; not in operational loop |

This file is an orientation reference, not a ratification surface for substrate selection, actor activation, or authority expansion.

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
