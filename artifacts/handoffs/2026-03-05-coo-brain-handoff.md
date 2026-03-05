# Handoff: Step 2 — COO Brain (Surgical Seed Procedure)

**Date:** 2026-03-05
**From:** Claude Code (bootstrap coordination session)
**To:** Claude Code (interactive COO brain session)
**Type:** Outbound — parallel stream

---

## Branch

Start now: `/new-build coo-brain` from current `main`.

> The review branch (`build/coo-bootstrap-review`) is still merging — do NOT wait for it. The plan is available right now at the review worktree path:
> ```
> /mnt/c/Users/cabra/Projects/LifeOS/.worktrees/sprint-deferments-d1-d3/.worktrees/coo-bootstrap-review/artifacts/plans/2026-03-05-coo-bootstrap-plan.md
> ```
> Read it directly from there. All essential context is also summarised in this handoff document.

---

## Commits

None yet — this is a net-new build.

---

## Test Results

Baseline (before your work): 2303 passed, 7 skipped (2026-03-05). Run `pytest runtime/tests -q` to confirm.

---

## What Was Done

- COO Bootstrap plan fully approved (council review: Codex + Gemini, all 7 conditions incorporated)
- Plan at `artifacts/plans/2026-03-05-coo-bootstrap-plan.md` (merged from `build/coo-bootstrap-review`)
- Step 1A (structured backlog), 1B (delegation envelope), 1C (hygiene) are being built in parallel by the coordination session

---

## What Remains (Your Scope)

**This is Step 2 of the COO Bootstrap: the surgical seed procedure.**

This is the highest-value artifact in the entire plan. Do not rush it.

### Deliverable 1: `config/agent_roles/coo.md`

The COO system prompt. This is what gets loaded into every OpenClaw COO session. It encodes:

- Role definition (who the COO is, what it does, what it doesn't do)
- Input/output contracts (what the COO receives, what it produces, in what format)
- Reasoning patterns (how to decompose objectives → tasks → orders)
- Escalation rules (exactly which decisions require CEO approval — reference the 3-level model: L0/L3/L4)
- Delegation rules (what's in the COO's autonomy vs. what must be proposed)
- Re-prioritization protocol (when/how the COO can reorder the backlog)
- Sub-objective authority (COO decomposes objectives at L3 during burn-in — propose before acting)
- Output format schemas (proposal YAML, status report, escalation format)
- **Burn-in constraints** (everything not explicitly L0 goes to L3 — no exceptions)

### Deliverable 2: `artifacts/coo/memory_seed.md`

The COO's persistent memory seed — what the COO should know at first invocation:
- Project history summary (relevant wins, current state)
- Active objectives (from CEO)
- Known agent patterns (provider preferences, failure modes observed)
- Current campaign state (COO Bootstrap campaign status)
- Decision log seed (key architectural decisions the COO needs to know)

### Deliverable 3: `artifacts/coo/brief.md` (first draft)

The session-start brief — what the COO puts in front of every new session to orient it:
- Current project state snapshot
- Active tasks in structured backlog
- Pending escalations
- Recommended next action

---

## How to Execute

### Phase 1: Deep Codebase Study (no code yet)

Read these files before drafting anything:

**Governance foundations:**
- `docs/01_governance/COO_Operating_Contract_v1.0.md` — the ratified COO role
- `docs/01_governance/COO_Expectations_Log_v1.0.md` — CEO expectations
- `artifacts/plans/2026-03-05-coo-bootstrap-plan.md` — the approved bootstrap plan (Parts 1-2 especially)

**Infrastructure the COO orchestrates:**
- `runtime/orchestration/dispatch/engine.py` — dispatch engine (submit ExecutionOrders here)
- `runtime/orchestration/dispatch/order.py` — ExecutionOrder schema (COO generates these)
- `runtime/orchestration/dispatch/ports.py` — SupervisorPort / CuratorPort protocols
- `runtime/orchestration/ceo_queue.py` — escalation queue (COO writes here, CEO resolves)
- `runtime/orchestration/loop/spine.py` — LoopSpine (executes orders)
- `runtime/agents/cli_dispatch.py` — how execution agents are invoked
- `runtime/agents/openclaw_bridge.py` — how OpenClaw is invoked (COO's own invocation path)
- `runtime/cli.py` — existing CLI surface (COO commands will be added here by Step 3F)

**Existing agent role patterns:**
- `config/agent_roles/builder.md` — pattern for role files
- `config/agent_roles/council_reviewer.md` — pattern for structured output schemas

**Config context:**
- `config/governance/` — existing governance configs
- `config/models.yaml` — provider configuration

### Phase 2: Draft with CEO

After studying the codebase, draft `config/agent_roles/coo.md`. **Present it to the CEO and iterate.** This is an interactive session — don't commit until the CEO approves the draft.

Key questions to answer in the draft:
1. What context does the COO receive at session start? (proposal request, status check, post-build hook, etc.)
2. What is the exact YAML schema for a task proposal? (must match the `TaskEntry` schema from Step 1A)
3. What is the exact format for an escalation to the CEO Queue?
4. How does the COO decide which provider (Codex vs Claude Code vs Gemini) for which task type?
5. What does the COO output when it has nothing to propose? (should be explicit, not silence)

### Phase 3: Memory Seed + Brief

Once the system prompt is approved, create `artifacts/coo/memory_seed.md` and `artifacts/coo/brief.md`.

---

## Key Context (Don't Re-research)

**Autonomy model (3-level burn-in, from plan):**
- L0: Full autonomy — state updates, read operations, tracking
- L3: Propose and wait — anything involving dispatch, new tasks, backlog changes (burn-in default)
- L4: Escalate — protected paths, strategy changes, budget above threshold, ambiguous scope
- L1/L2 deferred until Early Trust phase (weeks 3-4)

**COO invocation path:** OpenClaw bridge (`runtime/agents/openclaw_bridge.py`), NOT CLIDispatch. CLIDispatch handles execution agents. The COO is the orchestrator above that layer.

**Backlog schema (from Step 1A — being built in parallel):**
TaskEntry fields: id, title, description, dod, priority (P0-P3), risk (low/med/high), scope_paths, status (pending/in_progress/completed/blocked), requires_approval, owner, evidence, task_type (build/content/hygiene), tags, objective_ref, created_at, completed_at

**Shadow-first rule:** COO generates BACKLOG.md, LIFEOS_STATE.md, etc. as derived views. Physical deletion of originals deferred until Step 6 (Live COO verified).

**Fail-closed principle:** If autonomy category not found in `delegation_envelope.yaml`, default to L4 (escalate). Don't guess.

---

## Files to Create

| File | What |
|------|------|
| `config/agent_roles/coo.md` | COO system prompt (CEO-approved) |
| `artifacts/coo/memory_seed.md` | COO persistent memory seed |
| `artifacts/coo/brief.md` | First session-start brief template |

No tests required for this step — the output is documents, not code. The system prompt gets validated in Step 5 (burn-in).

---

## Gotchas

- **Don't conflate roles:** The COO is NOT a builder. It proposes tasks and submits ExecutionOrders. It never edits code directly.
- **Burn-in is conservative by design.** The system prompt should be assertively cautious — the COO should prefer to escalate over acting autonomously during burn-in.
- **Output format schemas must be strict.** The parser in Step 3D will parse the COO's YAML output. The system prompt must define exact schemas that the parser can rely on.
- **The CEO sets objectives; the COO decomposes them.** The system prompt must not give the COO authority to create top-level objectives.
- **Parser failure mode (R1 from plan):** Retry up to 2x, then escalate to CEO Queue. The system prompt should be designed so well-structured YAML is the natural output, not a special case.

---

## Coordination Notes

The coordination session (this session) is handling:
- Step 1A: `runtime/orchestration/coo/backlog.py` + `config/tasks/backlog.yaml` + tests
- Step 1B: `config/governance/delegation_envelope.yaml`
- Step 1C: Hygiene (nul, test_budget_concurrency.db, stale worktrees)
- Steps 3D/3E/3F/4G: After Step 1 completes

Your work (Step 2) is NOT blocked by Step 1. Start immediately after the review branch merges.

When you're done, produce a standard handoff back to the coordination session so Step 3D can incorporate the TaskProposal schema from your COO prompt.
