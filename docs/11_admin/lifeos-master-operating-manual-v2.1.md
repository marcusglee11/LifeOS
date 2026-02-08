# LifeOS Master Operating Manual v2.1
## Post-Reconnaissance Update

**Date:** 2026-02-07
**Supersedes:** Master Operating Manual v2.0 (same date, pre-recon)
**Purpose:** Incorporate Claude Code reconnaissance findings, correct OpenClaw assessment, integrate CEO decisions on open questions, and revise roadmap accordingly.

---

# CORRECTION NOTICE (v2.1)

The v2.0 manual contained a significant error in Section 4:

**"Key Correction: There Is No OpenClaw" — WRONG.**

OpenClaw is the execution substrate for both the COO (local) and Employee (GCP hosted) agents described in the Agent Architecture doc. It is not a separate agent — it is the configurable runtime that provides eyes, ears, mouth, brain, and arms to any agent instance. References to OpenClaw workspace paths (`~/.openclaw/workspace-employee/`), hardened configs (Appendix A of Agent Architecture), and tool allowlists are all OpenClaw configuration.

This changes the roadmap: agent infrastructure is configured, not built from scratch.

---

# CORRECTION NOTICE (v2.1 Reconciliation — 2026-02-08)

Claude Code sprint verified repo state against this manual's claims. **Two of three gaps identified below are already closed:**

| Manual v2.1 Claim | Actual Status | Evidence |
|---|---|---|
| StewardMission git ops "STUBBED" | **FULLY IMPLEMENTED** | `runtime/orchestration/missions/steward.py` — 691 lines, real git add/commit/push, governance guards, 8 integration tests passing |
| LLM backend "NEEDS CONFIGURATION" | **FULLY CONFIGURED** | `config/models.yaml` — 5 agents, per-agent API keys via `.env`, fallback chains. Switched to free Zen models 2026-02-08. |
| OpenClaw COO "NEEDS CONFIGURATION" | **Correctly identified** | External tool install — requires CEO action |

Additional corrections applied this sprint:
- Test suite: 1,371 passing (up from 1,335; 36 re-enabled), 0 failures
- CRLF phantom diffs: root-cause fixed via `.gitattributes` hardening
- Model config: switched from paid Grok/MiniMax to free Zen tier (zero cost)
- Doc links: fixed in prior sprint (2026-02-08)

**The only genuine remaining gap blocking the autonomous build loop is OpenClaw COO installation.**

---

# RECONNAISSANCE FINDINGS SUMMARY (2026-02-07)

Claude Code executed a full investigation of the repo. Key findings:

## Phase 1 Autonomy: ALREADY MERGED

| Item | Detail |
|------|--------|
| Merged to main | 2026-02-02, PR #19 |
| Workflow | `.github/workflows/phase1_autonomy_nightly.yml` — 8 PM UTC daily |
| Status | Active. Nightly doc hygiene + test + rollback operational. |

No action required. Phase 1 Autonomy is live.

## Loop Spine: 90% Complete

The autonomous build cycle infrastructure is structurally complete. Every component except one is real and functional:

| Component | Status |
|-----------|--------|
| LoopSpine (chain controller) | REAL — 6-step chain: hydrate > policy > design > build > review > steward |
| AutonomousBuildCycleMission | REAL — full orchestrator with ledger-based resumability |
| DesignMission | REAL — wires to `call_agent(role="designer")` |
| BuildMission | REAL — wires to `call_agent(role="builder")` |
| ReviewMission | REAL — wires to `call_agent(role="reviewer_architect")` |
| BuildWithValidationMission | REAL |
| ConfigurableLoopPolicy | REAL — config-driven, deadlock/oscillation detection |
| BudgetController | REAL — max_attempts(5), max_tokens(100k), max_wall_clock(30m) |
| CEO Queue | REAL — SQLite-backed, escalation types, 24h timeout |
| AttemptLedger | REAL — append-only JSONL, crash/resume hydration |
| Checkpoint/Resume | REAL — YAML persistence, policy hash validation |
| StewardMission | **COMPLETE** — 691 lines, real git add/commit/push, governance guards, 8 integration tests |

Operations status:

| Operation | Status |
|-----------|--------|
| `llm_call` | REAL |
| `packet_route` | REAL |
| `gate_check` | REAL |
| `run_tests` | REAL |
| `tool_invoke` | STUBBED (unused by current chain) |

**~~The single production gap is StewardMission git operations.~~** RESOLVED 2026-02-08: StewardMission fully implemented with real git ops and governance guards (deletion-safety-hardening sprint).

## Test Suite: Healthy

| Metric | Count |
|--------|-------|
| Total | 1,440 |
| Passed | 1,436 (99.7%) |
| Failed | 1 (broken doc links — non-blocking) |
| Skipped | 2 |

The 22 baseline failures from January are resolved. The single failure is 3 broken internal links in a governance doc.

---

# CEO DECISIONS ON OPEN QUESTIONS

| Q# | Question | Decision |
|----|----------|----------|
| Q1 | Merge Phase 1 Autonomy | Moot — already merged |
| Q2 | Loop spine builder | Loop spine exists (90%). Investigate via Claude Code (done). |
| Q3 | Revenue start date | Sound recommendation but friction-gated. OpenClaw COO as PM reduces friction. |
| Q4 | Rename project | No. Brand products separately. |
| Q5 | External Employee agent | Yes — needs configuration, not construction. Many purposes. |
| Q6 | 22 test failures | Resolved to 1 non-blocking failure. |
| Q7 | Time allocation | Meaningful only once OpenClaw COO is managing workstreams. |
| Q8 | Budget | ~$100/month total with wriggle room. $100/month deficit tolerance pending revenue. |

---

# REVISED ARCHITECTURE ASSESSMENT

## What You Actually Have (Updated)

```
LAYER              STATUS        EVIDENCE
─────────────────────────────────────────────────────────
Constitution       ✅ COMPLETE   v2.0, 4 hard invariants, 5 principles
Governance         ✅ COMPLETE   Protocol v1.0, Council v1.3, 6+ rulings
Runtime FSM        ✅ COMPLETE   engine.py, 14 states, deterministic transitions
Orchestration      ✅ COMPLETE   7 mission types, ledger, budgets, policy
Policy Engine      ✅ COMPLETE   v1.2.5, hash verification, manifest integrity
Test Suite         ✅ COMPLETE   1,440 tests, 99.7% pass rate
Doc Steward        ✅ COMPLETE   CLI, DAP validator, index checker, link checker
Agent Guidance     ✅ COMPLETE   CLAUDE.md, GEMINI.md, AGENTS.md
Tier 1             ✅ COMPLETE   Foundation, council-ratified
Tier 2             ✅ COMPLETE   Deterministic core, council-certified
Tier 2.5           ✅ ACTIVATED  Agent-driven maintenance with oversight
Phase 1 Autonomy   ✅ MERGED     Nightly doc hygiene active since 2026-02-02
Loop Spine         ✅ COMPLETE   All components real including StewardMission git ops
CEO Queue          ✅ COMPLETE   SQLite-backed, approve/reject, timeout
Checkpoint/Resume  ✅ COMPLETE   YAML persistence, policy hash validation
─────────────────────────────────────────────────────────
Steward Git Ops    ✅ COMPLETE   691-line implementation, real git ops, governance guards (fixed 2026-02-08)
Agent API Backend  ✅ COMPLETE   config/models.yaml — free Zen models configured (fixed 2026-02-08)
OpenClaw COO       ⚙️  CONFIG     Local install needs workspace + charter setup
OpenClaw Employee  ⏳ PLANNED    GCP instance needs provisioning + config
Revenue System     ❌ MISSING    No revenue experiments active
External Presence  ❌ MISSING    No content, no audience, no distribution
```

## The Real Gap (Revised Again)

v2.0 said: "you have strong primitives but no loop spine."

v2.1 corrects: **the loop spine exists and is structurally complete.** What's missing:

1. **StewardMission git operations** — bounded engineering task, the only code gap
2. **LLM backend configuration** — `call_agent()` needs a real provider (Grok Fast via OpenRouter as default per invariants)
3. **OpenClaw COO instance** — the configured runtime that ties it together

The gap is no longer "build the loop." It's "wire the last stub, configure the backend, and stand up the runtime."

---

# REVISED AGENT INFRASTRUCTURE

## OpenClaw as Execution Substrate

OpenClaw is the platform, not an agent. Both COO and Employee are OpenClaw instances with different configurations:

```
OPENCLAW PLATFORM
├── COO Instance (Local WSL2)
│   ├── Workspace: ~/.openclaw/workspace-coo/
│   ├── Config: Development-permissive, can diverge from upstream
│   ├── Identity: IS LifeOS infrastructure
│   ├── Tools: Full dev toolset (exec, read, write, edit, git, browser)
│   ├── Memory: LifeOS-native state docs (LIFEOS_STATE.md, BACKLOG.md)
│   ├── Role Stack: COO + CSO + PM + Orchestrator + Advisor
│   └── Uptime: Development sessions → eventually always-on
│
├── Employee Instance (GCP)
│   ├── Workspace: ~/.openclaw/workspace-employee/
│   ├── Config: Hardened, sandboxed, tracks upstream
│   ├── Identity: Separate entity, does not represent CEO
│   ├── Tools: Restricted (no elevated, no internal hooks)
│   ├── Memory: Gemini embeddings, entity bank, daily logs
│   ├── Role: Exploration probe — research, drafting, monitoring, admin
│   └── Uptime: Always-on (systemd service)
│
└── Shared State: Google Drive (coordination until inter-agent comms exist)
```

## Agent Landscape (Corrected)

```
AGENT/PLATFORM      ROLE                     STATUS
────────────────────────────────────────────────────────────────
OpenClaw (local)    COO — LifeOS kernel      NEEDS CONFIGURATION
OpenClaw (GCP)      Employee — probe         NEEDS PROVISIONING
Antigravity         Primary builder (legacy)  ACTIVE (Tier 2.5)
Claude Code         Sprint insertion          ACTIVE (ad hoc)
Claude (chat)       Strategic advisor/tools   ACTIVE (this role)
GPT                 Thinking partner          ACTIVE (ongoing)
```

OpenClaw COO is the intended replacement for the current manual orchestration pattern (CEO routing between ChatGPT, Claude, Antigravity). Once configured, it manages backlog, tracks progress, dispatches tasks, and reports status — eliminating the "waterboy" problem.

---

# REVISED 90-DAY ROADMAP

The reconnaissance findings compress the timeline significantly. The loop spine doesn't need building — it needs finishing (1 stub) and configuring (LLM backend + OpenClaw).

## Phase 0: Ground Truth + Quick Wins (Days 1-3)

```
SYSTEM:
├── 0a. Update Phase 1 nightly workflow                          [30 min]
│   Remove 9 of 10 test exclusions (all passing now)
│   Keep tests_doc/test_links.py excluded until links fixed
│   → Increases nightly coverage by 116 tests
│
├── 0b. Fix broken doc links                                     [15 min]
│   3 missing artifact files in Council_Ruling_Trusted_Builder_Mode_v1.1.md
│   Either create stubs or update links
│   → Clears the only test failure
│
├── 0c. Get local OpenClaw COO instance operational              [2-4 hours]
│   Install/verify OpenClaw on WSL2
│   Configure workspace per Agent Architecture doc section 4.5
│   Load SOUL.md, AGENTS.md, CONTEXT.md, CHARTER.md
│   Point at LifeOS repo
│   Verify basic operations: can read repo, can update state docs
│
└── 0d. Update LIFEOS_STATE.md                                   [5 min]
    Current Focus: OpenClaw COO operational + Steward git ops
    Status: Phase 1 merged, loop spine 90%, 1,436/1,440 tests passing
```

## Phase 1: Close the Loop (Days 3-7)

```
SYSTEM:
├── 1a. Implement StewardMission git operations                  [Claude Code sprint]
│   The single code gap blocking autonomous builds
│   Shell exists at runtime/orchestration/missions/steward.py
│   Needs: git add, git commit, git push with governance guards
│   Guards: protected path checks, diff size limits, clean repo verify
│   Tests: steward test structure already exists
│
├── 1b. Configure LLM backend for call_agent()                   [1-2 hours]
│   Wire to Grok 4.1 Fast via OpenRouter (per INVARIANT 4)
│   Claude Sonnet fallback
│   Verify design/build/review missions execute with real LLM
│
├── 1c. End-to-end test: one real task through the loop          [2-3 hours]
│   Something small: "Add type hints to runtime/util/crypto.py"
│   Full pipeline: select → design → review → build → review → steward
│   CEO approves at checkpoints
│   EVIDENCE: proof the loop closes
│
└── 1d. Use OpenClaw COO to manage this phase                    [ongoing]
    COO tracks progress, logs decisions, updates BACKLOG.md
    First proof of COO operational value
```

## Phase 2: Revenue Track + Employee (Weeks 2-3)

```
REVENUE (managed by OpenClaw COO):
├── 2a. LinkedIn daily posts begin                               [COO drafts, CEO reviews]
│   Seed: "What autonomous AI agents actually cost to run"
│   Use real OpenRouter spend data
│   COO manages pipeline: draft → CEO queue → approve → publish
│
├── 2b. B5 Governance Guide ships                                [COO + Claude session]
│   Now backed by 19,500 lines of real code + 1,440 tests
│   Agent generalizes governance docs → Gumroad
│
├── 2c. B2 Prompt Templates from CLAUDE.md/GEMINI.md/AGENTS.md  [COO + Claude session]
│   Real production-tested agent constitutions
│
└── 2d. First Substack post                                      [CEO writes, COO edits]
    "Why I built a constitution for my AI agents"

SYSTEM:
├── 2e. Configure GCP Employee instance                          [2-4 hours]
│   Hardened config from Agent Architecture Appendix A
│   Dedicated accounts (email, API keys, browser profile)
│   Tailscale for secure access
│
├── 2f. First Employee task: bounded research                    [1 hour setup]
│   Verify memory writes, daily summary generation
│   Prove the pipeline before expanding scope
│
└── 2g. Run 3+ real tasks through autonomous loop                [ongoing]
    Increasing complexity
    Track: autonomy rate (tasks completing without CEO intervention)
```

## Phase 3: Compound + Harden (Weeks 4-8)

```
SYSTEM:
├── Expand autonomous loop to handle increasingly complex tasks
├── COO reaches Phase 2 (manages backlog, tracks progress)
├── Employee handles: market monitoring, content research, admin
├── Track autonomy metrics weekly
├── Consider: remove more human touchpoints as trust builds
└── COO orchestrates Employee (Phase 3 transition)

REVENUE:
├── Week 4 data review: which channels show signal?
├── Double down on what works, kill what doesn't
├── C2 curated digest if monitoring Employee proves capable
├── B1 Starter Kit if B5 shows sales
└── Target: revenue trajectory visible by week 8
```

## Phase 4: Scale or Pivot (Weeks 9-12)

Unchanged from v2.0. Data-driven decision at week 8 review determines direction.

---

# BUDGET MODEL

Monthly target: ~$100 with wriggle room. $100 deficit tolerance pending revenue.

```
ITEM                           EST. MONTHLY    NOTES
──────────────────────────────────────────────────────────
OpenRouter API (Grok Fast)     $30-50          Primary model for all agents
Anthropic API (Sonnet fallback) $10-20         Fallback only, not default
GCP Employee instance          $15-30          Smallest viable (e2-micro or similar)
OpenClaw                       $0              Open source
Revenue tools                  $0              Gumroad free, Substack free, LinkedIn free
GitHub                         $0              Free tier sufficient
Google Drive                   $0              Included in Google account
──────────────────────────────────────────────────────────
TOTAL ESTIMATE                 $55-100/month
HARD CAP                       $200/month      (including $100 deficit tolerance)
```

Economic governor (INVARIANT 4) enforced: Grok Fast default, Sonnet fallback only on demonstrated necessity, no model upgrades without justification.

---

# UPDATED WEEKLY EXECUTION PROTOCOL

Same structure as v2.0 but with OpenClaw COO managing the pipeline:

```
MONDAY — DIRECTION
├── COO presents: state summary, weekend nightly results, CEO Queue items
├── CEO: reviews, approves/rejects queue items, sets week objectives (3 max)
├── COO: updates LIFEOS_STATE.md, distributes tasks
└── Total CEO time: ~15 min

TUESDAY-THURSDAY — EXECUTION
├── COO: manages agent work (autonomous loop, Employee tasks, content pipeline)
├── CEO: reviews LinkedIn draft (10 min), Claude Code sprint if needed (60-90 min)
├── CEO: approve/reject CEO Queue items as they arrive
├── CEO: dump thoughts to INBOX.md throughout day
└── Total CEO time: ~90 min/day (trending down as autonomy increases)

FRIDAY — REVIEW + SHIP
├── COO: prepares weekly summary with metrics
├── CEO: ships anything ready, reviews metrics, identifies blockers
├── One LinkedIn post reflecting on the week
└── Total CEO time: ~45 min

WEEKEND — BUFFER
├── Nightly automation runs without CEO
├── COO manages Employee tasks
├── CEO: rest, light INBOX.md capture if inspired
└── DO NOT design new architecture on weekends
```

---

# OPEN QUESTIONS (REVISED)

Previous 8 questions are resolved. New questions arising from recon:

```
Q1: OPENCLAW INSTALL STATUS?
    Is OpenClaw currently installed on WSL2?
    If so: version, workspace path, any known issues?
    If not: install is first action item.

Q2: OPENCLAW MODEL CONFIGURATION?
    The Agent Architecture doc defaults to claude-opus-4.5.
    INVARIANT 4 says Grok Fast default.
    Decision: which model for the COO instance?
    Recommendation: Grok Fast for routine, Sonnet for code generation,
    configurable per-task.

Q3: GCP ACCOUNT READY?
    Is the GCP project provisioned for Employee deployment?
    Budget alerts configured?
    Tailscale set up?

Q4: NIGHTLY WORKFLOW VERIFICATION
    Phase 1 Autonomy workflow is active — has it actually run successfully?
    Check GitHub Actions history for nightly run results.
    If it hasn't run: troubleshoot.

Q5: STEWARD GIT OPS SCOPE
    What governance guards should the steward enforce?
    Minimum: protected path checks, diff size limits, clean repo verify.
    Maximum: full DAP compliance, council approval for protected areas.
    Recommendation: minimum viable first, harden later.
```

---

# APPENDIX: DOCUMENT HIERARCHY (Updated)

```
SUPREME:
  LifeOS Constitution v2.0

GOVERNING:
  Governance Protocol v1.0
  Council Protocol v1.3

OPERATIONAL:
  COO Operating Contract v1.0
  COO Runtime Spec v1.0
  This Manual (Master Operating Manual v2.1)
  Agent Architecture v0.1 (OpenClaw COO + Employee spec)

SYSTEM INVARIANTS:
  config/invariants.yaml
  Section 1 of v2.0 (unchanged)

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
  lifeos-operations-manual.md (v1)
  lifeos-master-operating-manual-v2.md (v2.0 — superseded by this document)
  lifeos-red-team.md (initial assessment — partially incorrect)
```

---

**END OF MANUAL v2.1**

*This document supersedes v2.0. It incorporates Claude Code reconnaissance findings from 2026-02-07, corrects the OpenClaw assessment, integrates CEO decisions on all 8 open questions, and provides a compressed roadmap reflecting that the loop spine is 90% complete rather than missing.*
