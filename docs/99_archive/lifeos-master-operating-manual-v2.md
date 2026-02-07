# LifeOS Master Operating Manual v2.0
## Unified Strategic + Operational Roadmap

**Date:** 2026-02-07
**Purpose:** Single authoritative document for Week 1+ execution. Incorporates corrected repo analysis, GPT 5.2 cross-review, and all prior strategic work.
**How to use:** This is your navigation chart. Work through sequentially. Refer back to specific sections as needed.

---

# CORRECTION NOTICE

My initial red team assessment (lifeos-red-team.md) was based on incomplete information — the GitHub page showing 28 commits and the two uploaded PDFs. Having now read the full repo, I must correct several significant errors:

**What I got wrong:**
- "28 commits, near-zero functional agents" → **Wrong.** The runtime has ~19,500 lines of production code, ~23,000 lines of test code across 129 test files (415+ tests). Tiers 1-2 are COMPLETE. Tier 2.5 is ACTIVATED.
- "OpenClaw as agent framework" → **Wrong.** The agent infrastructure is Antigravity (primary builder, Gemini-based), OpenCode/Zen (doc steward), and Claude Code (sprint insertion). Models are Grok 4.1 Fast via OpenRouter with Claude Sonnet fallback.
- "Google Drive as state store is wrong" → **Partially wrong.** The repo already has `docs/11_admin/` with LIFEOS_STATE.md, BACKLOG.md, DECISIONS.md, INBOX.md — the state IS in git. Your architecture is already ahead of where I placed it.
- "No test infrastructure" → **Wrong.** 415+ tests, TDD compliance checking, BDD scenarios, policy tests, CI considerations.
- "Organizational churn" → **Partially wrong.** The three test directories (tests/, tests_doc/, tests_recursive/) serve distinct purposes: project-level, document compliance, and recursive kernel tests respectively.

**What I got right:**
- The governance-execution gap is real (confirmed by your own Feb 2 status report: "chain-grade loop controller is confirmed missing")
- Revenue strategy absent — still true
- The Phase 1.5 "scheduled tasks" trust ramp is genuinely missing from the architecture
- Cost model defaults need alignment
- The core thesis: "ship the first loop" — validated by your own roadmap inserting Phase 4A0

**What the repo reveals that neither I nor GPT 5.2 knew:**
- You have a working FSM engine with deterministic state transitions
- Mission types exist and some are implemented (build, build_with_validation, design, review, steward, echo, autonomous_build_cycle)
- A full governance framework with constitution v2.0, council protocol v1.3, 6+ active council rulings
- Policy engine with hash-level determinism, manifest verification, evidence capture
- Doc steward CLI for automated document governance
- Project builder with planner, sandbox, budget transactions, FSM, and routing
- Phase 1 Autonomy (nightly doc hygiene via GitHub Actions) is READY FOR ACTIVATION but apparently not yet merged to main
- The `human_burden` invariant in config/invariants.yaml (max 2 human actions, max 5 visible steps) is exactly the philosophy that should govern everything

---

# TABLE OF CONTENTS

1. System Invariants (The Non-Negotiables)
2. Corrected Architecture Assessment
3. The Critical Path: Phase 4A0 Loop Spine
4. Agent Infrastructure: What You Actually Have
5. Revenue Strategy (Unchanged but Recontextualized)
6. Project Naming
7. The Unified 90-Day Roadmap
8. Weekly Execution Protocol
9. Decision Framework
10. Open Questions for CEO Resolution

---

# 1. SYSTEM INVARIANTS

Per GPT 5.2's P0 recommendation: declare these at the top and enforce them everywhere.

These are drawn from your Constitution v2.0, the `config/invariants.yaml`, and operational reality. They should appear identically in all governing documents.

```
INVARIANT 1: CEO SUPREMACY
The human CEO is the sole source of strategic intent. 
No agent may override an explicit CEO decision.
No agent may silently infer CEO intent on strategic matters.

INVARIANT 2: CANONICAL STATE = GIT REPO
The LifeOS repo is the single source of truth for all system state.
docs/11_admin/LIFEOS_STATE.md is the current state file.
Google Drive is coordination-only (temporary, until inter-agent comms exist).
External agents never mutate canonical state directly.

INVARIANT 3: FAIL-CLOSED DEFAULT
When uncertain, halt and escalate rather than proceed.
Invalid state transitions → ERROR (terminal).
Unknown actions → ask, don't assume.

INVARIANT 4: ECONOMIC GOVERNOR
Model tiering: Grok 4.1 Fast (default) → Claude Sonnet (fallback).
Monthly spend caps enforced and tracked.
No model upgrade without demonstrated necessity.

INVARIANT 5: AUDIT COMPLETENESS
Every state transition logged. Every decision recorded with rationale.
Evidence packets for all mission completions.
Sufficient to reconstruct what happened and why.

INVARIANT 6: NO DESIGN WITHOUT IMPLEMENTATION
Every architecture document must have a corresponding implementation 
(PR, code, or working prototype) within 1 week.
Violation = the architecture was premature.
Compliance mechanism: COO tracks and flags.

INVARIANT 7: HUMAN BURDEN MINIMIZATION
(From config/invariants.yaml)
Max 5 visible steps. Max 2 human actions (intent/approve/veto only).
Agent-first execution. Zero donkey work for the human.
```

---

# 2. CORRECTED ARCHITECTURE ASSESSMENT

## What You Actually Have (Capability Matrix)

```
LAYER              STATUS        EVIDENCE
─────────────────────────────────────────────────────────
Constitution       ✅ COMPLETE   v2.0, 4 hard invariants, 5 principles
Governance         ✅ COMPLETE   Protocol v1.0, Council v1.3, 6+ rulings
Runtime FSM        ✅ COMPLETE   engine.py, 14 states, deterministic transitions
Orchestration      ✅ COMPLETE   7 mission types, ledger, budgets, policy
Policy Engine      ✅ COMPLETE   v1.2.5, hash verification, manifest integrity
Test Suite         ✅ COMPLETE   415+ tests, TDD compliance, BDD scenarios
Doc Steward        ✅ COMPLETE   CLI, DAP validator, index checker, link checker
Agent Guidance     ✅ COMPLETE   CLAUDE.md, GEMINI.md, AGENTS.md (3 agent types)
Tier 1             ✅ COMPLETE   Foundation, council-ratified
Tier 2             ✅ COMPLETE   Deterministic core, council-certified
Tier 2.5           ✅ ACTIVATED  Agent-driven maintenance with oversight
Phase 1 Autonomy   ⏳ READY      Nightly doc hygiene, not yet merged to main
─────────────────────────────────────────────────────────
Loop Spine (4A0)   ❌ MISSING    The autonomous build loop controller
CEO Queue (4A)     ❌ MISSING    Checkpoint pause/resume mechanism
Backlog Selection   ❌ MISSING    Automatic "what to do next"
OpenCode Envelope  ❌ MISSING    Full builder/steward via OpenCode
Revenue System     ❌ MISSING    No revenue experiments active
External Presence  ❌ MISSING    No content, no audience, no distribution
```

## The Real Gap (Refined)

My original assessment said "governance-execution inversion." That's still directionally true but imprecise. The more accurate diagnosis from your own Feb 2 status report:

**You have strong primitives but no loop spine.**

The orchestrator exists but runs predefined workflows. The mission types exist but aren't chained into an autonomous sequence. The policy engine works but isn't consulted by a loop controller. The ledger exists but nothing hydrates from it to resume work.

The gap is NOT "you built governance instead of code." You built a LOT of code. The gap is: **the code doesn't yet form a closed loop that runs without you initiating each step.**

Phase 4A0 (Loop Spine) is the bridge.

---

# 3. THE CRITICAL PATH: PHASE 4A0 LOOP SPINE

Your own Feb 2 roadmap correctly identifies this. Here's the operational spec with implementation detail.

## What the Loop Spine Must Do

```
AUTONOMOUS BUILD LOOP - MINIMUM VIABLE SPINE

Input:  A task from BACKLOG.md (or CEO directive)
Output: Either a completed deliverable with evidence packet,
        or a clean halt at a checkpoint awaiting CEO decision.

Pipeline:
  1. SELECT    → Pick task from backlog (or accept CEO directive)
  2. DESIGN    → DesignMission produces design artifact
  3. REVIEW    → ReviewMission evaluates design (M0_FAST for low-risk)
  4. PLAN      → Design → implementation plan
  5. REVIEW    → ReviewMission evaluates plan
  6. BUILD     → BuildMission / BuildWithValidationMission executes
  7. REVIEW    → ReviewMission evaluates build + evidence
  8. CLOSE     → Evidence packet, ledger update, backlog update

Checkpoint behavior:
  - At each REVIEW: if policy says ESCALATE → pause, write to CEO queue
  - On resume: hydrate from ledger, continue from checkpoint
  - On rejection: log reason, optionally retry with feedback (budget-bounded)

Budget enforcement:
  - Max N attempts per task (from ConfigurableLoopPolicy)
  - Max cost per task
  - Max wall-clock time per task
  - On budget exceeded → terminal ESCALATION
```

## Implementation Approach

You already have most of the pieces:

```
EXISTING PIECE                    → ROLE IN LOOP SPINE
───────────────────────────────────────────────────────
AutonomousBuildCycleMission      → Skeleton of the loop (needs wiring)
AttemptLedger                    → State persistence and resumability
ConfigurableLoopPolicy           → Decision engine (next action)
BudgetController                 → Budget enforcement
DesignMission                    → Step 2 (DESIGN)
ReviewMission                    → Steps 3, 5, 7 (REVIEW)
BuildMission                     → Step 6 (BUILD)
BuildWithValidationMission       → Step 6 alternative (BUILD + VALIDATE)
StewardMission                   → Post-build doc updates
run_controller.py                → Kill switch, run lock, dirty repo check
evidence_capture.py              → Evidence collection
```

**What's actually missing is the wiring** — the `loop_controller.py` that:
1. Reads the ledger to determine current state
2. Consults the policy to determine next action
3. Dispatches to the appropriate mission
4. Captures the result
5. Updates the ledger
6. Loops or halts based on outcome

This is a **bounded engineering task**, not a research problem. Estimated: 500-1000 lines of Python, 2-3 days of focused agent work with Claude Code.

## Suggested Implementation Order

```
Step 1: loop_controller.py — The spine itself
  - Hydrate from ledger
  - Implement state machine: SELECT→DESIGN→REVIEW→PLAN→REVIEW→BUILD→REVIEW→CLOSE
  - Checkpoint mechanism (write state, exit cleanly, resume on next invocation)
  - Budget checks at each transition

Step 2: Integration test — One dummy task through full pipeline
  - Simulated checkpoint (pause at REVIEW, resume)
  - Evidence packet emitted
  - Ledger correctly reflects all transitions
  - This is your "prove it works" gate

Step 3: CEO Queue — Simple file-based initially
  - Checkpoint writes to docs/11_admin/CEO_QUEUE.md
  - CEO reviews and approves/rejects
  - Loop controller reads queue on next invocation
  - (Can upgrade to something more sophisticated later)

Step 4: Backlog integration — Auto-select next task
  - Parse BACKLOG.md for "Now" items
  - Select highest priority non-blocked item
  - Mark as "In Progress"
  - On completion: mark as "Done"
```

---

# 4. AGENT INFRASTRUCTURE: WHAT YOU ACTUALLY HAVE

## Agent Landscape (Corrected)

```
AGENT           PLATFORM        ROLE                    STATUS
────────────────────────────────────────────────────────────────
Antigravity     Gemini-based    Primary builder         ACTIVE (Tier 2.5)
OpenCode/Zen    Zen API         Doc steward             ACTIVE (CT-2 Phase 2)
Claude Code     Anthropic CLI   Sprint insertion team   ACTIVE (ad hoc)
Claude (chat)   claude.ai       Strategic advisor       ACTIVE (this conversation)
GPT             OpenAI          Cross-review/analysis   AD HOC

MODEL CHAIN (from config/models.yaml):
  Primary:  Grok 4.1 Fast via OpenRouter
  Fallback: Claude Sonnet 4.5 via Anthropic
  Fallback: Minimax M2.1
```

## Key Correction: There Is No "OpenClaw"

My earlier documents repeatedly reference "OpenClaw." This appears to be wrong. Your actual agent infrastructure uses:
- **Antigravity**: The primary builder agent (Gemini-based), governed by GEMINI.md
- **OpenCode**: Doc steward agent, governed by AGENTS.md, uses Zen API
- **Claude Code**: Sprint insertion, governed by CLAUDE.md

If "OpenClaw" is something separate you're evaluating or planning to adopt, it's not in the current codebase. The revenue strategy and agent deployment specs from my earlier documents should be re-read with this correction in mind.

## Agent Infrastructure Gaps

```
WHAT'S WORKING:
- Antigravity can execute missions within governance bounds
- OpenCode handles doc stewardship
- Claude Code handles bounded sprints
- All three have constitutional guidance documents
- Protected areas (00_foundations, 01_governance) are enforced

WHAT'S MISSING:
- No "always-on" agent (all require human initiation)
- No inter-agent communication protocol (beyond shared filesystem)
- No scheduled execution (Phase 1 Autonomy nightly is ready but not merged)
- No external-facing agent (Employee from your Agent Architecture doc)
- No cost tracking dashboard across agents
```

## The Employee Question (From Your Agent Architecture Doc)

Your Agent Architecture doc describes an "Employee" agent as an exploration probe. This doesn't exist in the current codebase. The question is: do you need it now?

**Assessment:** Not for Phase 4A0. The loop spine is the priority. An Employee agent becomes valuable AFTER the loop spine works, because then you can route external research tasks through the same pipeline. For revenue experiments, you can use Claude Code or chat-based Claude sessions as a substitute Employee until the infrastructure justifies a dedicated deployment.

**When to build Employee:** After Phase 4A0 is working AND you have revenue experiments generating tasks that need always-on monitoring (e.g., the C2 curated digest, market monitoring).

---

# 5. REVENUE STRATEGY (UNCHANGED BUT RECONTEXTUALIZED)

The revenue analysis from my earlier documents stands. The portfolio of experiments (A1-A4 content, B1-B5 products, C1-C3 services) remains valid. What changes with the corrected repo assessment:

## Recontextualization

1. **Your products are MORE valuable than I initially assessed.** You don't have a vaporware governance doc — you have a battle-tested governance framework with 415+ tests, council rulings, and tier progression. B5 (Governance Framework Guide) is backed by real, working code.

2. **The "build in public" content is richer.** You have genuine war stories: policy engine debugging (v1.2.5 hash cycle elimination), council review processes, tier progression, deterministic artefact protocols. This is content nobody else has.

3. **The technical products (B1 Starter Kit, B2 Prompt Pack) can include real code.** Not just templates — actual working Python modules that demonstrate governance, mission types, and evidence capture.

4. **Revenue experiments can run IN PARALLEL with Phase 4A0.** The loop spine is engineering work (Claude Code sprints). Content creation is a different workstream. They don't compete for the same resource (your attention) if agent drafting handles the content.

## Adjusted Revenue Timeline

```
PARALLEL TRACK 1: System (Phase 4A0)     PARALLEL TRACK 2: Revenue
─────────────────────────────────────     ─────────────────────────
Week 1: Loop controller skeleton          Week 1: LinkedIn begins, B5 ships
Week 2: Integration test passing          Week 2: Substack #1, B2 ships  
Week 3: CEO Queue implementation          Week 3: C2 digest, Reddit/HN
Week 4: Backlog integration               Week 4: First revenue data review
Week 5-6: Harden + real tasks             Week 5-6: Double down on signal
Week 7-8: Phase 4A0 complete              Week 7-8: Kill/continue decisions
```

Your time split: ~60% system (Claude Code sprints on 4A0), ~30% revenue (review agent-drafted content + products), ~10% strategic direction.

---

# 6. PROJECT NAMING

You asked for renaming suggestions. Constraints:
- Must be ownable (not 5 other projects with same name)
- Must signal what it does without explanation
- Must work as both internal project name AND potential public brand
- Should not be cutesy or acronym-heavy

**Suggestions, ranked by my assessment of fit:**

```
1. AEGIS
   "AI-Enhanced Governance and Intent System"
   Strong, memorable, implies protection/governance.
   .com likely taken but "aegis-ops" or "aegis.ai" might work.
   Signals: authority, protection, autonomy-within-bounds.

2. HELM  
   "Human-Empowered Lifecycle Manager"
   Nautical metaphor — you steer, system executes.
   Short, strong, memorable. helmops.io or helmproject.dev.
   Signals: human at the wheel, operational control.
   Risk: Helm is also a Kubernetes tool. Differentiation needed.

3. PRINCIPAL
   Direct reference to the principal-agent model at the core.
   "Principal OS" or just "Principal."
   Signals: who's in charge (you), academic rigor.
   Risk: slightly corporate/cold.

4. SOVRA  
   From "sovereignty" + "operations."
   Unique, ownable, no collisions.
   sovra.dev or sovra.ai likely available.
   Signals: operational sovereignty (your stated goal).

5. AGENTURA
   "Agent" + Latin suffix.
   Signals: agent-managed operations.
   Unique, ownable.
   Risk: might sound too much like "adventure."

6. COMMANDANT
   The one who commands. Agents execute.
   Strong, clear hierarchy implied.
   Risk: militaristic connotation.

7. Keep "LifeOS" internally, brand products separately
   Products sell under a content brand (your name, or a 
   publication name like "Agent Operations Log").
   LifeOS stays as your private infrastructure name.
   Lowest friction option. No renaming needed.
```

**My recommendation: Option 7 for now, Option 4 (SOVRA) if you decide to open-source or build a public brand.** Renaming is a distraction at this stage. If you get traction on content/products, the brand emerges naturally from what resonates. If LifeOS becomes a public product, rebrand then.

---

# 7. THE UNIFIED 90-DAY ROADMAP

Incorporating: corrected codebase assessment, GPT 5.2 recommendations, revenue strategy, and actual Phase 4 requirements.

## Week 1: Activate What's Ready + First Shots

```
SYSTEM:
├── MERGE Phase 1 Autonomy branch to main (it's ready, just merge it)
│   → Nightly doc hygiene runs via GitHub Actions
│   → This is your first always-running autonomous capability
├── Claude Code sprint: Begin loop_controller.py skeleton
│   → Hydrate from AttemptLedger
│   → Implement SELECT→DESIGN→REVIEW state machine (stub handlers)
│   → Tests for state transitions
├── Add system invariants to docs/00_foundations/ as formal amendment
└── Update docs/11_admin/LIFEOS_STATE.md to reflect new focus

REVENUE:
├── LinkedIn daily posts begin (A1 — agent drafts, you review)
│   → Seed content: "What autonomous AI agents actually cost to run"
│   → Use your REAL cost data from OpenRouter/Anthropic usage
├── B5 Governance Guide: Agent generalizes your actual governance docs
│   → This is now backed by 19,500 lines of real code, not theory
│   → Ship to Gumroad by end of week
└── B2 Prompt Templates: Curate from your actual CLAUDE.md/GEMINI.md/AGENTS.md
    → These are real, production-tested agent constitutions

PROJECT MANAGEMENT:
├── Your existing docs/11_admin/ system IS the task management system
│   → LIFEOS_STATE.md = current focus
│   → BACKLOG.md = prioritized tasks  
│   → DECISIONS.md = decision log
│   → INBOX.md = capture scratchpad
├── Add GitHub Issues labels for revenue experiments
│   → revenue, content, product labels
└── Establish daily CEO ritual:
    → Morning: read LIFEOS_STATE.md (2 min)
    → During day: dump to INBOX.md
    → Evening: nothing (agent triages overnight if Phase 1 autonomy merged)
```

## Week 2: Loop Spine + Content Engine

```
SYSTEM:
├── Claude Code sprint: Wire loop_controller.py to real missions
│   → DesignMission → ReviewMission → BuildMission chain
│   → Checkpoint at REVIEW states
│   → Budget enforcement from BudgetController
├── Write integration test: one dummy task through full pipeline
│   → Simulated CEO approval at checkpoint
│   → Evidence packet emitted
│   → Ledger correctly reflects transitions
├── If integration test passes → Phase 4A0 skeleton is DONE
└── Begin CEO Queue implementation (file-based: CEO_QUEUE.md)

REVENUE:
├── First Substack post (A2)
│   → Topic: "Why I built a constitution for my AI agents"
│   → Include real code snippets from your Constitution v2.0
├── Twitter/X repurposing begins (A3 — agent reformats LinkedIn)
├── B3 Cost Calculator: agent builds from your actual API spend data
│   → Free lead magnet for email collection
└── Review first week's LinkedIn metrics — which pillars resonated?

GPT 5.2 P0 ITEMS:
├── Insert Phase 1.5 (Scheduled Tasks) into Agent Architecture doc
├── Codify agent↔repo contract (what agents can mutate, how)
└── Align model defaults across all docs (Grok Fast default, not Opus)
```

## Week 3-4: Loop Completion + Revenue Signal

```
SYSTEM:
├── CEO Queue working (pause/resume at checkpoints)
├── Backlog-driven selection (auto-pick from BACKLOG.md "Now" items)
├── Run first REAL task through autonomous loop
│   → Something small: "Add type hints to runtime/util/crypto.py"
│   → Full pipeline: select → design → review → build → review → close
│   → CEO approves at checkpoints
│   → EVIDENCE: this is the proof that Phase 4A0 works
├── If real task succeeds → Phase 4A0 is COMPLETE
│   → Update LIFEOS_STATE.md
│   → Council ruling to ratify
└── Begin Phase 4A: expand CEO Queue for multi-task management

REVENUE:
├── Launch C2 curated digest (agent monitors + summarizes)
├── Reddit/HN strategic posting (A4)
├── Build B1 Starter Kit (if B5 shows sales signal)
│   → Can now include REAL working code from your runtime
├── First revenue data: any sales? any engagement signals?
└── Adjust based on data

GPT 5.2 P1 ITEMS:
├── RACI table per phase (which COO "hat" dominates when)
├── Employee identity firewall red-team checklist
└── Failure-mode playbooks (spend cap hit → model downgrade → reduce frequency)
```

## Weeks 5-8: Compound + Harden

```
SYSTEM:
├── Phase 4A complete (CEO Queue + multi-task management)
├── Phase 4B in progress (backlog-driven execution)
├── Run increasingly complex tasks through the loop
│   → "Implement feature X" (real development work)
│   → "Review and refactor module Y"
│   → "Generate and publish weekly status report"
├── Track: how many tasks complete without CEO intervention?
│   → This is your autonomy metric
├── Begin OpenCode envelope expansion (Phase 4C) if loop is stable
└── Consider Employee agent deployment if revenue experiments generate
    monitoring tasks

REVENUE:
├── Week 8 major review (kill/continue on all experiments)
├── Products should have sales data by now
├── Content should have engagement data
├── Double down on what's working, kill what's not
└── If base case holds: ~$1K/month revenue trajectory

GPT 5.2 P2 ITEMS:
├── Tie Maximum Vision to measurable 90-day scoreboard
│   Suggested proxies:
│   1. Hours saved/week by autonomous operations
│   2. Tasks completed without CEO intervention (autonomy rate)
│   3. Monthly revenue from products/content
│   4. Escalation rate (lower = more trusted system)
│   5. Mean time from intent to deliverable
│   6. System uptime (nightly runs succeeding)
│   7. Audience size (LinkedIn followers, Substack subscribers)
└── Add these to METRICS.md and track weekly
```

## Weeks 9-12: Scale or Pivot

```
Based on data from Week 8 review:

IF SYSTEM IS WORKING (tasks completing autonomously):
├── Phase 4C/4D: expand what the loop can build
├── Consider open-sourcing governance framework (D1)
├── Employee agent deployment for monitoring/research
└── System IS the product — consider LifeOS-as-platform play

IF SYSTEM IS STALLED:
├── Identify the specific bottleneck
├── Is it the loop spine? → Claude Code sprint to fix
├── Is it agent reliability? → Model/prompt iteration
├── Is it governance overhead? → Simplify (M0_FAST for everything)
└── Is it motivation? → Revenue track should be providing energy

IF REVENUE IS WORKING:
├── Double down on winning channels
├── Build higher-value products (courses, consulting packages)
├── Audience tells you what to build next
└── Revenue buys more runway for system development

IF REVENUE IS STALLED:
├── Revisit Branch 4 (finance-specific angles)
├── Consider: is the audience wrong, or the product?
├── Try direct outreach to 10 people in target market
└── If still nothing by week 12 → fundamental strategy review
```

---

# 8. WEEKLY EXECUTION PROTOCOL

This replaces ad-hoc work sessions with a structured rhythm.

```
MONDAY — DIRECTION
├── Review LIFEOS_STATE.md (2 min)
├── Review BACKLOG.md, reprioritize if needed (5 min)
├── Set week's objectives (3 items max, write to LIFEOS_STATE.md)
├── Review weekend's LinkedIn metrics
└── Approve/reject any items in CEO Queue

TUESDAY-THURSDAY — EXECUTION
├── Morning: review agent-drafted content (LinkedIn post), approve/edit (10 min)
├── System work: Claude Code sprint sessions on Phase 4A0 (60-90 min)
├── Revenue work: review product drafts, Substack prep (30 min)
├── Dump thoughts to INBOX.md throughout the day
└── Approve/reject CEO Queue items as they arrive

FRIDAY — REVIEW + SHIP
├── Ship anything that's ready (product updates, content, code merges)
├── Update LIFEOS_STATE.md with week's outcomes
├── Review weekly metrics (agent prepares summary)
├── Identify blockers for next week
└── One LinkedIn post reflecting on the week's progress

WEEKEND — BUFFER
├── Review Substack draft, add judgment layer, publish
├── Light capture to INBOX.md if inspiration strikes
├── Rest. The nightly automation runs without you.
└── DO NOT design new architecture on weekends
    (this is your governance-retreat danger zone)
```

---

# 9. DECISION FRAMEWORK

For every decision, apply this filter:

```
1. DOES IT CLOSE A LOOP?
   If yes → high priority (loops generate value)
   If no → lower priority (preparation, not execution)

2. IS IT REVERSIBLE?
   If yes → act now, iterate later
   If no → deliberate, get a second opinion

3. WHAT'S THE COST OF DELAY?
   High (blocking other work) → do it today
   Low (nice to have) → put it on BACKLOG.md "Later"
   
4. CAN AN AGENT DO IT?
   If yes → delegate, review output
   If no → is this CEO-level judgment work or friction?
   If friction → find a way to make it agent-executable

5. DOES IT GENERATE REVENUE SIGNAL?
   If yes → prioritize (you need runway data)
   If no → is it system infrastructure that enables future revenue?
   If neither → seriously question why you're doing it
```

---

# 10. OPEN QUESTIONS FOR CEO RESOLUTION

These require your judgment. I can advise but not decide.

```
Q1: MERGE PHASE 1 AUTONOMY?
    The branch build/repo-cleanup-p0 is ready per your activation checklist.
    1006/1006 tests pass. All conditions resolved.
    Decision: merge to main and enable nightly runs? Y/N
    My recommendation: Yes, immediately. It's been ready since Jan 30.

Q2: PHASE 4A0 EXECUTION AGENT?
    Who builds the loop spine?
    a) Claude Code (bounded sprints, you direct)
    b) Antigravity (primary builder, within governance)
    c) Hybrid (Antigravity designs, Claude Code implements)
    My recommendation: (a) Claude Code for the loop spine itself.
    It's a bounded, high-stakes piece of infrastructure. 
    Once the spine works, Antigravity builds everything else THROUGH it.

Q3: REVENUE START DATE?
    You can start LinkedIn today with zero system dependencies.
    B5 can ship this week if you authorize agent generalization.
    Do you want to start revenue experiments this week? Y/N
    My recommendation: Yes. Revenue is parallel track, not sequential.

Q4: RENAME PROJECT?
    Options in Section 6. 
    My recommendation: Don't rename now. Brand products separately.
    Revisit at week 12 if you're going public.

Q5: EXTERNAL EMPLOYEE AGENT?
    Your Agent Architecture doc describes deploying one.
    Your current codebase doesn't have one.
    Timeline: when do you want to deploy?
    My recommendation: After Phase 4A0 is working (Week 5-6 earliest).
    Until then, Claude sessions substitute for Employee research tasks.

Q6: 22 KNOWN TEST FAILURES?
    Your activation checklist mentions "22 baseline failures preserved."
    Your Phase B sprint resolved some but left others.
    Decision: triage these as part of Phase 4A0 or accept as known debt?
    My recommendation: Accept as known debt for now. 
    Tag them in a GitHub Issue. Fix when they block real work.

Q7: TIME ALLOCATION?
    Suggested split: 60% system / 30% revenue / 10% strategic.
    Does this match your energy and priorities?
    Adjust the ratio and I'll rebalance the roadmap accordingly.

Q8: BUDGET CONSTRAINTS?
    What's your monthly budget for:
    a) API costs (OpenRouter + Anthropic + Gemini)?
    b) Infrastructure (GCP if deploying Employee)?
    c) Tools (Gumroad, Substack, scheduling tools)?
    This determines how aggressively to run experiments.
```

---

# APPENDIX A: DOCUMENT HIERARCHY (Updated)

```
SUPREME:
  LifeOS Constitution v2.0

GOVERNING:
  Governance Protocol v1.0
  Council Protocol v1.3

OPERATIONAL:
  COO Operating Contract v1.0
  COO Runtime Spec v1.0
  This Manual (Master Operating Manual v2.0)

SYSTEM INVARIANTS:
  config/invariants.yaml
  Section 1 of this document

EXECUTION:
  docs/11_admin/LIFEOS_STATE.md (current state)
  docs/11_admin/BACKLOG.md (task queue)
  docs/11_admin/DECISIONS.md (decision log)
  docs/11_admin/INBOX.md (capture)

AGENT GUIDANCE:
  CLAUDE.md (Claude Code)
  GEMINI.md (Antigravity)
  AGENTS.md (OpenCode)

REVENUE:
  week1-A1-linkedin-agent-spec.md
  week1-B5-governance-product-spec.md
  week1-B2-prompt-templates-spec.md

ARCHIVED/SUPERSEDED:
  lifeos-red-team.md (initial assessment — partially incorrect, see corrections)
  lifeos-operations-manual.md (v1 — superseded by this document)
```

---

# APPENDIX B: WHAT TO DO MONDAY MORNING

Not the 90-day plan. Not the architecture. Just Monday.

```
1. Merge Phase 1 Autonomy branch to main.                    [15 min]
   (You've been sitting on this since Jan 30.)

2. Update LIFEOS_STATE.md:                                     [5 min]
   Current Focus: Phase 4A0 Loop Spine + Revenue Track 1
   Active WIP: loop_controller.py skeleton
   
3. Claude Code session: begin loop_controller.py               [90 min]
   Goal: skeleton that hydrates from ledger and walks through 
   SELECT→DESIGN→REVIEW states (stub handlers, real state machine)
   Test: transitions work, ledger updates, checkpoint halts cleanly

4. Write and post first LinkedIn post                          [20 min]
   Topic: Pick from seed list in A1 spec.
   Suggested: "The real cost of running autonomous AI agents 24/7"
   (Use your actual OpenRouter spend data)

5. Dump any thoughts from this weekend into INBOX.md           [5 min]

Total: ~2.5 hours. That's Day 1. Everything else has a day.
```

---

**END OF MANUAL**

*This document supersedes lifeos-operations-manual.md (v1). It incorporates full repo analysis, GPT 5.2 cross-review, and corrected technical assessments. It should be treated as the authoritative operational guide for the next 90 days.*
