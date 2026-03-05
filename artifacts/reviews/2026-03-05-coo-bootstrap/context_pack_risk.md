# Context Pack: Risk/Pragmatism Lens (Gemini)
# Reviewer: Gemini | Seat: Risk/Pragmatism | Date: 2026-03-05

You are reviewing a plan for bootstrapping the LifeOS COO agent. Your role is the Risk/Pragmatism lens — evaluate whether this plan is realistic, identify failure modes, and flag over-engineering.

## Context
LifeOS is a multi-agent orchestrator. The CEO is currently the bottleneck. The plan proposes standing up an OpenClaw COO agent to handle project management autonomously. Current infrastructure: working build loop, dispatch engine (Phase 1, 56 tests), council review system, evidence chain. The COO (OpenClaw) is already installed and passed acceptance probe.

## Your Checklist
- [ ] The bootstrap campaign has realistic scope for the proposed timeline
- [ ] CEO decision points are correctly identified (not too many, not too few)
- [ ] Failure modes are identified and have recovery paths
- [ ] The plan doesn't build more than is needed for the immediate goal
- [ ] The trust growth model is practical (not just theoretical)
- [ ] The "proxy COO" burn-in period is well-defined
- [ ] Deferred items are correctly deferred (not hidden dependencies)

## Red Flags to Call Out
- Scope creep disguised as "foundation work"
- Assumptions about OpenClaw capabilities that aren't validated
- Missing risk: what if the COO prompt doesn't produce useful proposals?
- Missing risk: what if the structured backlog migration breaks existing workflows?
- Timeline assumptions that aren't grounded

## Key Questions
1. Is the surgical seed procedure (Step 2) a bottleneck? What if the first prompt draft is poor?
2. The plan deprecates BACKLOG.md, LIFEOS_STATE.md, INBOX.md, and .context/project_state.md — is this too aggressive? What's the rollback plan?
3. Is the 5-level autonomy model necessary for v1, or should we start with 2 levels (ask/don't ask)?
4. The plan proposes 15+ new files. Is there a smaller MVP that proves the concept first?
5. What's the actual failure mode if OpenClaw can't produce well-structured YAML proposals?

## Output Format
Produce a structured YAML review packet with the following fields:
```yaml
verdict_recommendation: APPROVE | APPROVE_WITH_CONDITIONS | REJECT
summary: "<1-2 sentence summary>"
claims:
  - id: R1
    category: scope | timeline | failure_mode | over_engineering | missing_dependency | assumption
    severity: blocker | major | minor | observation
    description: "<what is the issue>"
    evidence: "<specific reference to plan text>"
    recommendation: "<what to do>"
complexity_budget:
  new_files_count: <number>
  new_files_justified: true | false
  rationale: "<why>"
conditions:
  - "<condition if APPROVE_WITH_CONDITIONS>"
```

---

## Plan Document

(Full plan at: artifacts/plans/2026-03-05-coo-bootstrap-plan.md)

### The Core Claim
Standing up the COO eliminates the CEO bottleneck. Every future build cycle runs autonomously. Revenue content gets produced. The system proves its own value externally.

### Bootstrap Campaign Structure
```
Step 1: Foundation (parallel) — backlog schema, delegation config, hygiene
Step 2: COO Brain (sequential, CEO collaboration required) — system prompt
Step 3: Wiring (parallel) — context builder, templates, CLI commands
Step 4: Integration — post-execution state updater + E2E test
Step 5: Burn-in (sequential) — proxy COO validates, CEO observes
Step 6: Live COO — first real invocation, shadow mode, then promote
Revenue Content (parallel with 2-6) — LinkedIn posts, B5 outline
```

### New Files Proposed (15+ across 3 tracks)
**COO Foundation track:**
- `runtime/orchestration/coo/__init__.py`
- `runtime/orchestration/coo/backlog.py`
- `runtime/orchestration/coo/context.py`
- `runtime/orchestration/coo/parser.py`
- `runtime/orchestration/coo/templates.py`
- `runtime/orchestration/coo/commands.py`
- `config/governance/delegation_envelope.yaml`
- `config/tasks/backlog.yaml`
- `config/tasks/order_templates/build.yaml`
- `config/tasks/order_templates/content.yaml`
- `config/tasks/order_templates/hygiene.yaml`
- `config/agent_roles/coo.md` (COO system prompt)
- Tests for each module

**Deprecation planned (aggressive):**
- `docs/11_admin/BACKLOG.md` → structured backlog
- `docs/11_admin/LIFEOS_STATE.md` → COO-generated view
- `docs/11_admin/INBOX.md` → COO signal processing
- `.context/project_state.md` → COO memory
- `docs/11_admin/AUTONOMY_STATUS.md` → deprecated outright

### Trust Growth Model
```
Burn-in (Weeks 1-2): Almost everything at L3 (propose and wait)
Early trust (Weeks 3-4): Low-risk dispatch → L1, state updates → L0
Established (Month 2+): Medium-risk builds → L2, sub-objectives → L1
Mature (Month 3+): Full operational cycle autonomously
```
Promotion requires: N successful cycles + zero unhandled failures (mechanism not specified)

### 5-Level Delegation Envelope
```
L0: Full autonomy — state updates, reads
L1: Act then notify — dispatch low-risk tasks, reprioritize within tier
L2: Auto-execute after timeout — medium-risk builds, provider changes
L3: Propose and wait — cross-tier promotion, new objectives
L4: Escalate — protected paths, strategy changes, external commitments
```

### CEO Decision Points (Irreducible per plan)
1. Review + approve COO system prompt (Step 2)
2. Set top-level objectives (Step 2)
3. Approve delegation envelope boundaries (Step 1B)
4. B5 Guide scope decision (Revenue track)
5. Observe burn-in, give feedback (Step 5)
6. Sign off on COO going live (Step 6)

### What's Already Validated
- OpenClaw installed and P1 acceptance probe passed (2026-02-11)
- DispatchEngine Phase 1 complete (56 tests passing)
- CLIDispatch supports CODEX, GEMINI, CLAUDE_CODE providers
- CEOQueue escalation flow working
- Worktree-first build isolation working (mandatory since 2026-02-28)

### Existing Files That Would Be Migrated/Deprecated
- `docs/11_admin/BACKLOG.md` — current task list (manual markdown)
- `docs/11_admin/LIFEOS_STATE.md` — current project state (last updated 2026-02-28)
- `docs/11_admin/INBOX.md` — CEO inbound signals (has current uncommitted changes)
- `recursive_kernel/backlog_parser.py` — existing backlog parser (may contain reusable logic)
- `artifacts/dispatch/nightly_queue.yaml` — existing YAML dispatch queue (pattern reference)
