# LifeOS Build Loop: Production Readiness Plan v2.1

**Status:** FINAL  
**Supersedes:** Master Execution Plan v1.1 (complete), W6 Codemoot spike (deprecated → Council V2), Governed Multi-Provider Agent Dispatch plan (deferred, constraints preserved)  
**Date:** 2026-02-26  
**Authority:** CEO  
**Review inputs:** Gemini (structural/infrastructure), GPT (execution-grade specificity), Claude (plan author)

---

## What This Plan Is

The build loop exists. Governance exists. The E2E spine is proven. Council V2 is under construction. This plan does not build new governance architecture. It adds minimal operational glue (run-lock, evidence emission, shadow-mode wiring, supervision scaffolding) to put the existing system into production: real work, real governance, real stress — with agent-layer supervision that distills operational findings into CEO-level decisions only.

The CEO's role is not to watch logs or debug test failures. It is to receive distilled recommendations ("swap this model," "tighten this envelope," "this task type isn't ready for autonomy yet") and make directional decisions. Everything below that threshold is handled by agents operating within their governed envelopes.

---

## The Operating Model

```
CEO
 │
 │  receives: distilled findings, envelope change proposals, escalations
 │  decides:  approve/reject/modify recommendations
 │  does NOT: route packets, debug failures, select tasks, review code
 │
 ├── Supervisor Agent (Council V2 in shadow → blocking)
 │    ├── reviews every build cycle
 │    ├── detects patterns across cycles (correlated failures, envelope gaps)
 │    ├── produces cycle summaries using shadow comparison rubric
 │    └── escalates only: envelope changes, model swaps, new failure classes
 │
 ├── Task Curator Agent
 │    ├── selects work from backlog per criteria (see below)
 │    ├── ensures workflow coverage and dogfood value
 │    └── escalates only: backlog exhaustion, tasks requiring CEO-level scope decisions
 │
 ├── Builder Agent (Antigravity / spine)
 │    ├── executes: design → build → test → review → steward
 │    ├── operates within existing governance envelopes
 │    └── escalates only: governance surface violations, unrecoverable failures
 │
 └── Shadow Agent (Claude Code or Codex) [observational]
      ├── receives same task payloads as builder
      ├── produces independent output stored as evidence artifact
      └── does NOT gate or modify the primary pipeline
```

---

## Invariants (non-negotiable, enforced mechanically)

1. **Repo-clean:** Every cycle ends with working directory clean. No uncommitted state.
2. **No orphans:** No orphan processes after any cycle. Process-group cleanup on timeout.
3. **Receipts:** Every invocation (LLM call, tool execution, review dispatch) emits a receipt per the Evidence Contract below.
4. **Fail-closed:** If any gate cannot determine pass/fail, the run BLOCKs. No silent best-effort.
5. **Envelope integrity:** Policy hash recorded per cycle. Violations recorded as structured events (timestamp, agent, violation type, affected path, cycle ID). Envelope change proposals use a standard diff-like format (current constraint → proposed change → rationale → risk assessment).

---

## Definitions

**Cycle:** A complete mission execution ending in SUCCESS (all gates passed, terminal packet with evidence) or CLEAN_FAIL (failure reason recorded, repo-clean invariant holds, receipt chain complete). Both are valid outcomes.

**Intervention:** Any human action during a cycle other than triggering the initial run. Includes: editing files, rerouting packets, approving mid-run prompts, restarting failed stages. Triggering and post-cycle review are not intervention.

**Envelope:** The set of constraints bounding an agent's autonomous operation. Defined by existing governance framework (protected paths, tier gates, escalation triggers, policy hash). Envelopes are discovered and refined through usage, not specified comprehensively upfront.

**CEO-level decision:** A choice that changes the system's operating parameters: envelope modifications, model/provider swaps, new task categories, governance framework changes, resource allocation. Everything else is operational and handled by agents.

---

## Mechanical Evidence Contract

### Terminal Packet

Each cycle produces exactly one terminal packet stored at `artifacts/terminal/TP_<run_id>.yaml`. Contents:

```yaml
run_id: <unique run identifier>
status: SUCCESS | CLEAN_FAIL
start_ts: <ISO 8601 UTC>
end_ts: <ISO 8601 UTC>
task_ref: <backlog task ID>
policy_hash: <governance policy hash at cycle start>
phase_outcomes:
  design: {status: pass|fail|skipped, receipt_ref: <path>}
  build: {status: pass|fail|skipped, receipt_ref: <path>}
  test: {status: pass|fail|skipped, receipt_ref: <path>}
  review: {status: pass|fail|skipped, receipt_ref: <path>}
  steward: {status: pass|fail|skipped, receipt_ref: <path>}
gate_results: [<list of gate pass/fail with reason>]
receipt_index: <path to cycle receipt index>
clean_fail_reason: <null if SUCCESS, reason code if CLEAN_FAIL>
repo_clean_verified: true|false
orphan_check_passed: true|false
packet_hash: <SHA-256 of this file>
```

### Receipt Schema

Each invocation emits a receipt to `artifacts/receipts/<run_id>/<seq>_<provider>.json`. Fields:

```yaml
seq: <integer, monotonic within run>
run_id: <parent run>
provider_id: <model or CLI agent identifier>
mode: api | cli
seat_id: <council lens, builder, steward, etc.>
start_ts: <ISO 8601 UTC>
end_ts: <ISO 8601 UTC>
exit_status: <HTTP status or process exit code>
output_hash: <SHA-256 of response body>
schema_validation: pass | fail | n/a
token_usage: {prompt: <int>, completion: <int>}  # best-effort, informational
truncation: {stdout_capped: false, stderr_capped: false}  # CLI only
error: <null or error message>
```

### Receipt Index

One canonical index per cycle at `artifacts/receipts/<run_id>/index.json`: a stable-ordered array of receipt paths with their seq numbers and provider IDs. Terminal packet references this index.

### Storage Policy

- **During burn-in (manual trigger):** Committed to repo in `artifacts/` directory. Retained indefinitely.
- **During unattended operation (GitHub Actions):** Terminal packet + receipt index uploaded as GitHub Actions artifacts (90-day retention). Live run summaries may be appended to `artifacts/manifests/run_log.jsonl` as runtime operational state, but canonical run truth remains in terminal/checkpoint/ledger/receipt surfaces rather than a repo-tracked JSONL log.
- **GitHub Issue** links to the Actions artifact URL for the terminal packet.

---

## Shadow Comparison Rubric

When the shadow agent produces output for the same task, the supervisor evaluates:

| Dimension | Measurement | Source |
|-----------|-------------|--------|
| **Correctness** | Tests pass on shadow output? Validators pass? | Mechanical: pytest, schema gates |
| **Governance compliance** | Shadow output respects protected paths, policy hash, envelope? | Mechanical: policy engine check |
| **Patch minimality** | Lines changed, files touched (fewer = better, all else equal) | Mechanical: diff stats |
| **Defect detection** | If reviewing: did shadow catch defects primary missed? | Supervisor verdict comparison |
| **Intervention avoidance** | Would shadow output have completed without intervention? | Counterfactual assessment |

Shadow outputs stored at `artifacts/shadow/<run_id>/`. Never merged. Never gating. Compared post-cycle only.

---

## Execution

### Prerequisites (Week 1, before any burn-in cycles)

All must be complete before Batch 1:

1. **Run-lock:** Single-flight enforcement. Concurrent triggers blocked. Stale lock detection. Tested.
2. **Terminal packet emission:** Verified for SUCCESS and CLEAN_FAIL. Schema matches Evidence Contract.
3. **Receipt emission:** Dry-run cycle producing receipts per schema with receipt index.
4. **Council V2 shadow wiring:** Receives review payloads in parallel. Verdicts logged. Does not gate. Legacy reviewer is sole gate.
5. **Shadow agent capture:** Dispatches payload, stores output as evidence. Stub acceptable if CLI agent unavailable.
6. **Task curation:** Agent-proposed task list approved by CEO.

---

### 1. Task Curation

An agent selects work from the backlog. CEO approves the initial batch, then the agent operates autonomously within these criteria:

**Selection criteria:**

1. **Productive:** Task produces an artifact LifeOS actually needs. No synthetic busywork.
2. **Full workflow coverage:** Selected set collectively exercises all mission phases (design, build, test, review, steward). No phase left untested.
3. **Right complexity:** Completable in a single autonomous cycle. Bounded inputs, verifiable outputs, clear done criteria. No multi-session dependencies.
4. **Breadth:** The task set covers at least 3 of: file creation, file modification, test generation, doc stewardship, code refactoring.
5. **Safe scope:** No modifications to governance core (`docs/00_foundations/`, `docs/01_governance/`). Other paths allowed if the task is productive and changes are reversible within 5 minutes.
6. **Dogfood value:** Tasks that improve LifeOS's own test coverage, documentation, or code hygiene are preferred.

---

### 2. Stress Testing (the burn-in)

**Batch 1: 5 cycles**

- Tasks from curated list, priority order
- Full pipeline: hydrate → policy → design → build → test → review → steward
- **Legacy reviewer is sole gate.** Council V2 shadow only.
- Shadow agent produces evidence only
- Terminal packet per Evidence Contract
- Run-lock enforced
- No manual intervention

**After Batch 1: Supervisor burn-in report**

- Cycle outcomes (pass / clean_fail / intervention count)
- Failure modes ranked by severity × frequency (not frequency alone)
- Shadow quality delta per rubric
- Council V2 vs. legacy verdict deltas
- Envelope observations (too tight / too loose / calibrated)
- Recommendations: each tagged CEO-level or operational, using envelope delta format

**CEO review point.** Approve, reject, or modify.

**Batch 2: 5 cycles (post-adjustment)**

- Top 3 fixes applied
- Second summary with delta from Batch 1
- If satisfactory: proceed to Council V2 promotion and unattended operation

---

### 3. Council V2 Promotion

**Promotion criteria (from burn-in data):**

- Shadow verdicts consistent with or better than legacy
- Challenger rework loop triggered at least once (real or fixture)
- Synthesis and advisory produce coherent verdicts
- No false-positive blocks

**Deterministic fixture:** One intentionally-deficient artifact in burn-in batch.

**Promotion is a CEO-level decision.**

---

### 4. Unattended Operation

**Prerequisites:**

- Run-lock operational (proven during burn-in)
- Backlog auto-selection operational
- GitHub Actions cron with: concurrency group (single run), permissions model (PAT or GitHub App), secret management, artifact retention (90 days)
- Completion notification via GitHub Issue linking to terminal packet artifact

**Validation:** 3 consecutive overnight runs. CEO wakes to results without triggering or intervening.

**Notification routing:** GitHub Issues interim. Migrates to COO layer when available. Issues remain as audit trail.

---

### 5. Multi-Provider Dispatch (conditional)

Infrastructure merged to main (c71e2a6, 98 tests, all providers disabled). Activation gated on trigger conditions:

1. Provider limitation failures evidenced by shadow comparison data
2. Review quality plateau from correlated model weaknesses
3. Seat requires capabilities unavailable via API-only path

**If triggered:** Enable providers, start with one reviewer seat read-only, configure per-lens overrides, wire convergence detection, harden process lifecycle.

**Constraints (non-negotiable):** Fail-closed, receipts for every call, sanitized env, process-group kill on timeout.

**If not triggered:** Deferred indefinitely. Infrastructure stays dormant.

---

## What Surfaces to the CEO

**Routine (no action needed):**
- Cycle terminal packets
- GitHub Issue notifications
- Operational metrics

**CEO-level (requires decision):**
- Envelope change proposals (current → proposed → rationale → risk)
- Model/provider swap recommendations (backed by shadow data)
- New failure class identification
- Backlog exhaustion
- Governance framework modifications
- Council V2 promotion

---

## Dispositions

**Master Execution Plan v1.1:** Complete.

**W6 Codemoot:** Superseded by Council V2. Mark in LIFEOS_STATE.md and BACKLOG.md.

**Governed Multi-Provider Agent Dispatch plan:** Sections 3.2-3.5 → `docs/11_admin/Dispatch_Constraints.md`. Remainder → `docs/99_archive/`.

**Multi-provider CLI dispatch code (c71e2a6):** Merged to main, all providers disabled. Activation gated on Section 5.

---

## Immediate Actions

1. Update LIFEOS_STATE.md — W6 Codemoot SUPERSEDED; dispatch code merged but dormant
2. Update BACKLOG.md — deprecate W6, add production readiness tasks
3. Extract dispatch plan 3.2-3.5 → `docs/11_admin/Dispatch_Constraints.md`
4. Archive dispatch plan → `docs/99_archive/`
5. Merge `build/multi-provider-dispatch` to main
6. Execute Claude Code instruction block (below)
7. CEO approves task curation output before Batch 1

---

## Sequencing

```
Week 1      Prerequisites (Claude Code instruction block):
              Run-lock, evidence emission, shadow wiring, task curation,
              GitHub Actions feasibility report

Week 2-3    Batch 1: 5 burn-in cycles
              Legacy gates, Council V2 shadow, shadow agent comparison
              Burn-in report → CEO review

Week 3-4    Batch 2: 5 post-adjustment cycles
              Council V2 promotion decision
              Backlog auto-selection wiring

Week 4-5    Unattended operation:
              GitHub Actions cron, overnight runs, morning summaries

Week 5+     Production. CEO = directional decisions only.
              Multi-provider dispatch if triggered.
              COO layer construction (separate workstream).
```

---

## Claude Code Instruction Block

```
CONTEXT:
You are working on LifeOS, an autonomous AI operating system. The Build Loop
Production Readiness Plan v2.1 is approved. Your job is to prepare the
prerequisites for Batch 1 burn-in. The multi-provider dispatch branch
(build/multi-provider-dispatch, c71e2a6) should be merged to main first if
not already merged — all CLI providers are disabled, zero behavior change.

TASKS (execute in order):

1. MERGE MULTI-PROVIDER BRANCH
   - Merge build/multi-provider-dispatch to main if not already merged
   - Verify: all 98 new tests pass, no regressions against baseline
   - Clean up worktree at .worktrees/cli-dispatch after merge

2. RUN-LOCK IMPLEMENTATION
   - Implement single-flight run-lock for the build loop
   - Stale lock detection with configurable timeout (default: 6 hours)
   - If lock exists and is stale: log warning, acquire
   - If lock exists and is live: BLOCK with clear message
   - Store lock at: artifacts/locks/run.lock
     (contains PID, start timestamp, run_id)
   - Prove with tests:
     (a) concurrent acquisition → mutual exclusion
     (b) stale lock → detected and recovered

3. TERMINAL PACKET + RECEIPT EMISSION
   - Verify existing terminal packet emission matches this schema:
       run_id, status (SUCCESS|CLEAN_FAIL), start_ts, end_ts, task_ref,
       policy_hash, phase_outcomes (design/build/test/review/steward each
       with status + receipt_ref), gate_results, receipt_index path,
       clean_fail_reason, repo_clean_verified, orphan_check_passed,
       packet_hash (SHA-256 of file)
   - If existing emission differs: align it. If absent: implement it.
   - Verify receipt emission per invocation:
       seq, run_id, provider_id, mode (api|cli), seat_id, start_ts,
       end_ts, exit_status, output_hash, schema_validation, token_usage,
       truncation, error
   - Implement receipt index generation: stable-ordered JSON array at
     artifacts/receipts/<run_id>/index.json
   - Prove: one manual dry-run cycle producing valid terminal packet +
     receipt index matching schema

4. COUNCIL V2 SHADOW-MODE WIRING
   - Wire Council V2 to receive review payloads in parallel with legacy
   - Council V2 logs verdicts to artifacts/shadow_council/<run_id>/
   - Council V2 does NOT gate the pipeline
   - Legacy reviewer remains sole gate
   - Prove: one manual cycle with shadow verdict files on disk;
     pipeline outcome determined by legacy reviewer only

5. SHADOW AGENT CAPTURE MECHANISM
   - Dispatch same task payload to shadow agent (Claude Code / Codex CLI)
   - Output stored at artifacts/shadow/<run_id>/ as evidence
   - Never merged, never gating
   - If no CLI agent available: stub that logs "shadow agent not
     configured" and produces placeholder evidence file
   - Prove: mechanism produces output without affecting primary pipeline

6. GITHUB ACTIONS FEASIBILITY (INVESTIGATION ONLY — DO NOT IMPLEMENT)
   - Examine: existing workflows, missing secrets/tokens, Actions
     minutes/billing, runtime dependency feasibility, cron blockers,
     concurrency group needs, permissions model (PAT vs GitHub App),
     secret management, artifact retention
   - Output report to: artifacts/reports/github_actions_feasibility.md

7. TASK CURATION
   - Read BACKLOG.md and test suite structure
   - Propose 5-7 tasks per selection criteria:
     (a) Productive: artifact LifeOS needs
     (b) Full workflow: set covers design/build/test/review/steward
     (c) Right complexity: single-cycle, bounded, verifiable
     (d) Breadth: 3+ of file create/modify/test gen/doc steward/refactor
     (e) Safe scope: no governance core (docs/00_foundations/,
         docs/01_governance/). Other paths OK if productive + reversible.
     (f) Dogfood value: improves LifeOS tests/docs/hygiene
   - Include one intentionally-deficient artifact to test challenger loop
   - For each: description, criteria, phases, done criterion, effort, risks
   - Rank by execution order
   - Output to: artifacts/reports/burn_in_task_proposal.md
   - REQUIRES CEO APPROVAL before execution

CONSTRAINTS:
- No changes to governance core semantics
- No changes to protected paths policy or tier definitions
- No new routing logic
- All new code must have tests
- Fail-closed: if you cannot determine existing conventions for receipts,
  terminal packets, or other artifacts from the repo, STOP and emit a
  BLOCKED report. Do not guess or invent conventions.

EVIDENCE REQUIRED:
- Each task: files changed/added, commands run, test results
- Run-lock: concurrent test + stale lock test
- Terminal packet: one dry-run with valid packet + receipt index
- Shadow wiring: one cycle with shadow verdicts on disk
- Shadow agent: mechanism output without pipeline impact

HANDOFF:
Return a handoff pack: branch name, commit list, test results,
what was done, what remains, gotchas.
```
