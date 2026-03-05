# Plan: COO Bootstrap — Standing Up the LifeOS Project Manager

**Status:** APPROVED — Council review complete (Codex + Gemini, 2026-03-05)
**Date:** 2026-03-05

## Context

The CEO is the bottleneck. LifeOS has a working build loop, dispatch engine, council, and evidence infrastructure — but every cycle starts with CEO task selection, scope definition, and monitoring. The system produces nothing external because ideation and project management live in the CEO's head.

**The unlock:** Stand up the COO agent (OpenClaw instance) as an autonomous project manager. The CEO sets objectives and makes approval decisions. The COO handles everything else: task decomposition, prioritization, dispatch, monitoring, state tracking, course-correction, and escalation.

**Architecture:** LifeOS is a framework where multiple execution agents (various models, various harnesses) are coordinated by an OpenClaw COO-orchestrating agent. Claude Code and Codex act as COO construction agents during bootstrap, then become execution agents under COO coordination.

---

## Part 1: COO Design (Agreed in CEO Discussion)

### 1.1 COO-Agent Interaction

The existing dispatch/spine/cli_dispatch infrastructure handles most agent coordination. The COO doesn't need new plumbing — it needs a **reasoning layer**.

- **Pre-execution:** COO configures agents via ExecutionOrders (provider selection, constraints, scope)
- **Post-execution:** COO evaluates results via terminal packets, council verdicts, receipts
- **Decision:** COO decides next action (retry, rework, new task, escalate)
- **All communication is file-based.** No mid-execution agent communication (deferred — unnecessary complexity at this stage)
- **Campaign tracking:** COO plans multi-order campaigns, tracks progress across them

**What's missing (not plumbing — reasoning):**
- Agent routing intelligence (which provider for which task) → COO prompt + persistent memory
- Cross-cycle learning (provider X failed on task type Y) → COO persistent memory
- Multi-order strategy (objective → ordered steps → current position) → campaign tracker
- Current brief for interactive agents → COO generates `brief.md` each invocation

**COO invocation path (A2 fix):** The COO is an OpenClaw instance invoked via the existing **OpenClaw bridge** (`runtime/agents/openclaw_bridge.py`), not via `CLIDispatch`. `CLIDispatch` handles execution agents (Codex, Gemini, Claude Code) that run builds. The COO is the orchestrator above that layer and uses a separate invocation path already present in the codebase.

### 1.2 CEO-COO Interface

**Primary: Conversational OpenClaw session.** CEO opens a session, COO presents current state and recommendations, CEO directs/approves/redirects through natural conversation. Key decisions from conversation get persisted to COO memory.

**Secondary: Automated invocations.** Cron-triggered or event-triggered (post-build hooks). Same COO prompt + context, no human in the loop. Produces reports, updates state, dispatches within delegation envelope.

**Claude Code's role:** Execution agent, not project manager. Loads COO's latest brief at session start to stay aligned. CEO may still interact directly for complex, judgment-heavy builds.

**Graphical UI:** Deferred. CLI-first, graphical later.

### 1.3 Autonomy Boundaries (3-Level Delegation Envelope — v1 Burn-in)

**v1 uses 3 levels only.** L1 and L2 are defined here for completeness but are NOT active during burn-in. They will be added to `delegation_envelope.yaml` after Early Trust phase is established with evidence.

| Level | Pattern | v1 Status | Examples |
|-------|---------|-----------|----------|
| **L0: Full autonomy** | Act, report in next status | **Active** | Update tracking state, record agent patterns, read operations |
| **L1: Act then notify** | Act, immediately surface | *Deferred — Early Trust phase* | Dispatch low-risk tasks, reprioritize within same tier |
| **L2: Auto-execute after timeout** | Propose, wait N hours, execute | *Deferred — Established phase* | Medium-risk builds, provider changes based on health |
| **L3: Propose and wait** | Propose, wait for explicit approval | **Active (default)** | Any dispatch, cross-tier promotion, new objectives, new work branches |
| **L4: Escalate** | Flag decision, provide options | **Active** | Protected paths, strategy changes, external commitments, budget above threshold, ambiguous scope |

**Burn-in default:** Everything not explicitly L0 goes to L3. No exceptions.

**Sub-objective authority:** CEO sets objectives. COO decomposes into sub-objectives at L3 (propose and wait) during burn-in. COO cannot change top-level objectives, create unlinked objectives, or commit to external deliverables.

**Mechanical enforcement:** `delegation_envelope.yaml` maps action categories to autonomy levels. The autonomy gate in `runtime/orchestration/coo/commands.py` reads this config before emitting any order and writes an audit artifact. Fail-closed: if category not found in envelope, default to L4 (escalate). Tests must cover the fail-closed path.

**Delegation envelope config:** `config/governance/delegation_envelope.yaml` — action categories mapped to autonomy levels, escalation thresholds, protected paths, current trust tier.

### 1.4 Trust Growth Model

| Phase | Timeline | COO Autonomy |
|-------|----------|-------------|
| **Burn-in** | Weeks 1-2 | Almost everything at L3 (propose and wait). Claude Code acts as proxy COO. CEO observes every decision. |
| **Early trust** | Weeks 3-4 | Low-risk dispatch → L1. State updates → L0. CEO reviews less frequently. |
| **Established** | Month 2+ | Medium-risk builds → L2. Sub-objectives → L1. CEO focuses on strategy only. |
| **Mature** | Month 3+ | Full operational cycle autonomously. CEO: directives + weekly review. |

Each promotion requires evidence: N successful cycles at current level, zero unhandled failures.

### 1.5 Continuous Tracking

**COO persistent memory is the canonical project state.** Everything else is input or derived view.

| Data Structure | Purpose | COO Access |
|---|---|---|
| Structured backlog | All tasks with status, priority, risk | Read + write |
| Objectives register | CEO-set objectives + COO sub-objectives | Read + write (sub-objectives) |
| Campaign state | Multi-order plans with progress tracking | Read + write |
| Agent performance log | Provider success/failure patterns | Read + write |
| Decision log | Key decisions with rationale | Read + write |
| Current brief | Session-start context for all agents | Write (regenerated per invocation) |

**Deprecation plan (shadow-first — R3 fix):**

Manual files are NOT deleted during burn-in. Instead, the COO auto-generates them as derived views from the structured backlog. Physical deletion only happens after Step 6 (Live COO) is verified stable.

| Current File | Burn-in Fate | After Step 6 |
|---|---|---|
| `docs/11_admin/BACKLOG.md` | Auto-regenerated from `config/tasks/backlog.yaml` each COO invocation | Delete original |
| `docs/11_admin/LIFEOS_STATE.md` | Auto-regenerated as COO-derived view | Delete original |
| `docs/11_admin/INBOX.md` | Auto-regenerated as COO signal queue view | Delete original |
| `.context/project_state.md` | Auto-regenerated from COO memory | Delete original |
| `docs/11_admin/AUTONOMY_STATUS.md` | Deleted immediately — stale since Feb 14, no shadow needed | Already gone |

**Shadow generation:** Step 4G (post-execution state updater) also regenerates shadow markdown. If COO fails, markdown files remain as last-known-good state — no "blind flight".

---

## Part 2: Meta-Plan — Project Managing the Project Manager

### The Bootstrap Problem

Who manages the project of building the project manager? Answer: **Claude Code acts as proxy COO during bootstrap.** This means:

1. **Day 1:** Create structured backlog immediately. Start using it for all tracking — not after the COO is built, but now.
2. **Throughout bootstrap:** I (Claude Code) maintain the structured backlog, produce briefs at session start, track campaign progress, update state after each build.
3. **Handoff:** When the COO goes live, it inherits populated, current data structures — not empty schemas.

### Bootstrap Campaign (Managed by Proxy COO)

```
Campaign: COO-BOOTSTRAP
Objective: Stand up operational COO
Status: PLANNING

Step 1: Foundation (parallel builds)
  ├─ Build A: Structured backlog + seed data (Claude Code or Codex)
  ├─ Build B: Delegation envelope config (Claude Code)
  └─ Build C: Hygiene sprint (Codex — independent)

Step 2: COO Brain (Claude Code — surgical procedure)
  ├─ Study full codebase: Operating Contract, architecture, dispatch, spine, agents, governance
  ├─ Draft COO system prompt + persistent memory seed
  └─ CEO reviews and iterates

Step 3: Wiring (parallel builds)
  ├─ Build D: Context builder + parser (Claude Code or Codex)
  ├─ Build E: Templates + template loader (Codex)
  └─ Build F: CLI commands (Claude Code)

Step 4: Integration
  ├─ Build G: Post-execution state updater hooks
  └─ E2E test: propose → approve → dispatch → close → verify state updated

Step 5: Burn-in
  ├─ Proxy COO validates reasoning patterns (Claude Code acts as COO, CEO observes)
  ├─ Adjust prompt/memory based on what works
  └─ CEO approves COO prompt for live use

Step 6: Live COO
  ├─ First real COO invocation (OpenClaw with approved prompt)
  ├─ Run in shadow mode (COO proposes, proxy COO validates, CEO approves)
  └─ Promote to operational when shadow matches expectations

Revenue Content (parallel with Steps 2-6):
  ├─ C1: LinkedIn posts from burn-in reports
  └─ C2: B5 Governance Guide outline
```

### What Must the CEO Do (Irreducible)

| Decision | When | Format |
|----------|------|--------|
| Review + approve COO system prompt | Step 2 | Read draft, approve/adjust |
| Set top-level objectives | Step 2 | Tell the COO what matters |
| Approve delegation envelope boundaries | Step 1B | Review config, approve/adjust |
| B5 Guide scope decision | Track C2 | Book? Series? Whitepaper? |
| Observe burn-in, give feedback | Step 5 | "That recommendation was wrong because..." |
| Sign off on COO going live | Step 6 | Approve promotion from shadow to operational |

**Everything else is buildable by agents.**

---

## Part 3: Implementation Details

### Step 1A: Structured Backlog + Seed Data

**New files:**
- `runtime/orchestration/coo/__init__.py` — package marker
- `runtime/orchestration/coo/backlog.py` — `TaskEntry` dataclass, `load_backlog()`, `save_backlog()`, `filter_actionable()`, `mark_completed()`
- `config/tasks/backlog.yaml` — seed with current open items from BACKLOG.md
- `runtime/tests/orchestration/coo/test_backlog.py`

**Pattern:** Follow `runtime/orchestration/dispatch/order.py` (dataclass + YAML validation)

**TaskEntry fields:** id, title, description, dod, priority (P0-P3), risk (low/med/high), scope_paths, status (pending/in_progress/completed/blocked), requires_approval, owner, evidence, task_type (build/content/hygiene), tags, objective_ref, created_at, completed_at

**objective_ref bootstrapping (R4 fix):** Tasks created in Step 1 before objectives are formally defined in Step 2 use `objective_ref: bootstrap`. This is a valid sentinel value — the COO will re-link tasks to proper objectives during the Step 2 seed procedure.

**Backlog migration plan (A4 fix):** Three task sources currently exist — `docs/11_admin/BACKLOG.md` (parsed by `recursive_kernel/backlog_parser.py`), `config/backlog.yaml` (used by `run-mission`), and `artifacts/dispatch/nightly_queue.yaml` (FIFO queue). Migration:
1. `config/tasks/backlog.yaml` becomes the single canonical source (new schema)
2. `recursive_kernel/backlog_parser.py` is updated to read from `config/tasks/backlog.yaml` (or kept as a read-only adapter during burn-in)
3. `config/backlog.yaml` is migrated to `config/tasks/backlog.yaml` in Step 1A seed data
4. `nightly_queue.yaml` tasks are migrated into `config/tasks/backlog.yaml` as pending items
5. All readers (run-mission CLI, backlog_parser) updated to point at new canonical source before old files are removed

### Step 1B: Delegation Envelope Config

**New files:**
- `config/governance/delegation_envelope.yaml` — action categories × autonomy levels, escalation thresholds, protected paths, trust tier

### Step 1C: Hygiene Sprint (Independent, Codex)

- Delete `nul`, `test_budget_concurrency.db` from repo root
- `git worktree prune` + remove stale `.worktrees/` entries
- Update `.gitignore` if needed

### Step 2: COO Brain — Surgical Seed Procedure

**This is the highest-value single artifact in the entire plan.**

Claude Code (me) performs:
1. Deep study of: COO Operating Contract, COO Architecture doc, dispatch engine, spine, council FSM, agent roles, governance framework, delegation envelope
2. Draft `config/agent_roles/coo.md` — comprehensive system prompt encoding: role definition, input/output contracts, reasoning patterns, escalation rules, delegation rules, re-prioritization protocol, sub-objective authority, output format schemas
3. Draft COO persistent memory seed — project history, current state, known patterns, agent performance baselines
4. CEO reviews and iterates until satisfied

**New files:**
- `config/agent_roles/coo.md` — COO system prompt
- COO persistent memory seed (format TBD — depends on OpenClaw memory mechanism)

### Step 3D: Context Builder + Parser

**New files:**
- `runtime/orchestration/coo/context.py` — `build_propose_context()`, `build_status_context()`, `build_report_context()`
- `runtime/orchestration/coo/parser.py` — `parse_proposal_response()`, `parse_execution_order()`, `TaskProposal` dataclass
- `runtime/tests/orchestration/coo/test_context.py`
- `runtime/tests/orchestration/coo/test_parser.py`

**Parser fail-safe contract (R1 fix):** `parse_proposal_response()` and `parse_execution_order()` must never raise silently. On invalid or malformed LLM output:
1. Retry up to 2 times (re-invoke COO with error feedback appended to context)
2. If still invalid after retries, write escalation to `CEOQueue` with `EscalationType.AMBIGUOUS_TASK` and the raw invalid output as context
3. Return `None` — caller (commands.py) must handle `None` as "escalated, pending CEO resolution"

Tests must cover: valid YAML, invalid YAML (syntax error), structurally invalid YAML (missing required fields), and the retry path.

### Step 3E: Templates

**New files:**
- `config/tasks/order_templates/build.yaml` — 6-phase chain, worktree=true
- `config/tasks/order_templates/content.yaml` — 3-phase chain, relaxed scope
- `config/tasks/order_templates/hygiene.yaml` — 4-phase chain, tight scope
- `runtime/orchestration/coo/templates.py` — `load_template()`, `instantiate_order()`

### Step 3F: CLI Commands

**New files:**
- `runtime/orchestration/coo/commands.py` — handler implementations

**Modified:**
- `runtime/cli.py` — add `coo` subparser group:
  - `lifeos coo propose` — produce ranked task proposals
  - `lifeos coo approve T-001 [T-003 ...]` — generate ExecutionOrders → dispatch inbox, then trigger execution
  - `lifeos coo status` — operational status
  - `lifeos coo report` — synthesis report
  - `lifeos coo direct "<intent>"` — inject CEO directive
- `runtime/tests/orchestration/coo/test_commands.py`

**Dispatch execution loop (A1 fix):** `lifeos coo approve` follows this sequence:
1. Parse approved task IDs from arguments
2. Check autonomy gate against `delegation_envelope.yaml` — escalate if not permitted
3. Generate `ExecutionOrder` YAML → write to `artifacts/dispatch/inbox/<order_id>.yaml`
4. **Immediately call `DispatchEngine.execute_from_path(order_path)`** to drain the order inline
5. On completion, read terminal packet → call `update_structured_backlog()` (Step 4G)
6. Print result summary to stdout

This is the "run-once inline" model — no daemon, no polling. CEO runs `lifeos coo approve` which is synchronous and blocking. This matches the existing CLI contract (`lifeos dispatch submit` → `lifeos dispatch run` are already separate but the COO wires them together). If a different trigger model is preferred (cron/daemon), that is a Step 5+ enhancement.

**Verification (end of Step 3F):** `lifeos coo approve T-001` must produce a terminal packet in `artifacts/terminal/` and a completed order in `artifacts/dispatch/completed/`.

### Step 4G: Post-Execution State Updater

**Modified:**
- `runtime/tools/workflow_pack.py` — add `update_structured_backlog()`
- `scripts/workflow/closure_pack.py` — wire structured backlog update after merge

### Objectives Register + Campaign Tracker (Deferred to Step 5+)

These can be simple YAML files that the COO reads/writes. Structure defined during the surgical seed procedure based on what the COO's prompt needs.
- `config/tasks/objectives.yaml`
- `artifacts/coo/campaigns/`
- `artifacts/coo/decisions/`
- `artifacts/coo/brief.md`

---

## Part 4: What Existing Infrastructure Is Reused

| Component | Location | Status | How COO Uses It |
|---|---|---|---|
| Dispatch Engine | `runtime/orchestration/dispatch/engine.py` | Phase 1 complete, 56 tests ✓ | COO submits ExecutionOrders to inbox |
| ExecutionOrder schema | `runtime/orchestration/dispatch/order.py` | Stable v1 ✓ | COO generates orders matching this schema |
| SupervisorPort/CuratorPort | `runtime/orchestration/dispatch/ports.py` | Protocol definitions ✓ | COO implements these via files |
| CEO Queue | `runtime/orchestration/ceo_queue.py` | SQLite, typed escalations ✓ | COO writes escalations, CEO resolves via CLI |
| CLI surface | `runtime/cli.py` | dispatch/spine/queue wired ✓ | Extend with `coo` subparser |
| CLI agent dispatch | `runtime/agents/cli_dispatch.py` | Multi-provider ✓ | Execution agents (Codex/Gemini/Claude Code) dispatched via this module |
| OpenClaw bridge | `runtime/agents/openclaw_bridge.py` | Wired ✓ | COO (OpenClaw) invoked via this bridge — separate from CLIDispatch |
| LoopSpine | `runtime/orchestration/loop/spine.py` | E2E proven ✓ | Dispatch engine uses spine to execute orders |
| Run Controller | `runtime/orchestration/run_controller.py` | Fail-closed ✓ | Safety gates remain unchanged |
| Agent roles | `config/agent_roles/*.md` | 6 roles defined ✓ | COO role added alongside existing ones |
| COO Operating Contract | `docs/01_governance/COO_Operating_Contract_v1.0.md` | Ratified ✓ | Foundation for COO system prompt |
| Backlog parser | `recursive_kernel/backlog_parser.py` | Exists ✓ | Reference for migration, may reuse parsing logic |
| Nightly queue | `artifacts/dispatch/nightly_queue.yaml` | YAML format ✓ | Pattern reference for structured backlog |

---

## Part 5: Priority Reordering

**OLD priorities (from LIFEOS_STATE):**
1. 3 consecutive overnight GH Actions runs
2. P1: Bypass Monitoring
3. P1: Semantic Guardrails
4. P1: Fix test_steward_runner.py

**NEW priorities:**
1. **COO Bootstrap** — highest leverage, unblocks all future work
2. **Revenue Content** — first external output, proves system value
3. **Hygiene** — mechanical cleanup
4. *Deferred → COO manages:* GH Actions runs, Bypass Monitoring, Semantic Guardrails, CI Hardening, Dispatch Phase 2+

---

## Part 6: Parallel Execution Plan

**3 tracks running simultaneously:**

| Track | Agent | Supervision Level |
|---|---|---|
| **COO Foundation** (Steps 1A, 1B, 3D, 3E, 3F, 4G) | Claude Code + Codex | Medium — proxy COO tracks |
| **Hygiene** (Step 1C) | Codex (bounded) | Low — well-defined DoD |
| **Revenue Content** (C1 + C2) | Claude Code | Medium — CEO reviews output |

**Step 2 (Surgical Seed) is sequential** — requires interactive Claude Code + CEO collaboration. Cannot be parallelized.

**Step 5 (Burn-in) is sequential** — requires observation and iteration.

---

## Part 7: Verification

### Per-Step
- Each build: `pytest runtime/tests -q` (zero regressions) + targeted test commands

### COO Operational (End of Step 4)
1. `pytest runtime/tests/orchestration/coo/ -q` — all COO module tests pass
2. `lifeos coo propose` → valid proposal YAML
3. `lifeos coo approve T-001` → ExecutionOrder in dispatch inbox
4. `lifeos dispatch status` → order pending

### COO E2E (End of Step 5)
5. Full loop: propose → approve → dispatch → spine executes → close_build → backlog.yaml updated → LIFEOS_STATE updated
6. Proxy COO reasoning matches CEO expectations
7. CEO approves COO prompt for live use

### Revenue Content
8. `artifacts/content/linkedin_drafts/batch_001.md` — 5 posts, CEO-reviewed
9. `artifacts/content/b5_governance_guide_outline.md` — chapter structure, CEO-reviewed

### Full Suite
- `pytest runtime/tests -q` — zero regressions across all tracks

---

## Part 8: Council Review Process (Pre-Execution Gate)

**Purpose:** Multi-model review of this plan before any implementation begins. Real model diversity (not self-review).

### Review Topology

| Seat | Model | Lens | Focus |
|------|-------|------|-------|
| **Architecture** | Codex (via MCP) | Structural coherence | Does the COO design fit existing LifeOS architecture? Are the right pieces reused? Missing dependencies? Component decomposition sound? |
| **Risk/Pragmatism** | Gemini (via CLI) | Failure modes & realism | Is the bootstrap campaign realistic? CEO decision points correct? Trust growth model sound? What could go wrong? Over-engineering? |

**Why these models:** The strategic audit identified that using the same model for all council seats is 12x cost for 1x diversity. This review dogfoods real diversity — Codex and Gemini bring genuinely different perspectives than Claude.

**My role:** Process manager only. I do NOT review the plan myself. I:
1. Prepare the Context Pack (inputs) for each reviewer
2. Dispatch to Codex and Gemini in parallel
3. Collect their structured findings
4. Compile the raw findings into a report (no filtering — CEO sees everything)
5. Present the full report to the CEO

### Review Outputs Directory
```
artifacts/reviews/2026-03-05-coo-bootstrap/
├── context_pack_architecture.md    # Exact input sent to Codex
├── context_pack_risk.md            # Exact input sent to Gemini
├── codex_architecture_review.yaml  # Raw Codex output
├── gemini_risk_review.yaml         # Raw Gemini output
└── review_report.md                # Compiled report with synthesis
```

---

## Part 9: What This Plan Does NOT Cover (Explicit Deferrals)

- Graphical UI for CEO-COO interaction
- Mid-execution agent communication
- Dispatch Engine Phase 2+ (parallel instances, full ProviderPool health monitoring)
- Council V2 promotion from shadow to blocking
- External distribution (LinkedIn API, email)
- COO self-improvement / recursive capability growth

These are future work that the operational COO will propose and manage.

---

## Execution Sequence

1. ~~Save plan → Run council review (Codex + Gemini) → Present findings to CEO~~ ✓ **DONE** (2026-03-05, commit 7e8f1f7f)
2. ~~Incorporate review feedback → Approve adjusted plan~~ ✓ **DONE** (this commit)
3. **Execute:** Three parallel tracks per Part 6, managed by proxy COO (me), tracked in structured backlog from day 1

**Ready to execute.**
