# Plan: Self-Building LifeOS — “CEO Out of the Execution Loop” Milestone
**Status:** Draft v2.2 (amended for execution)  
**Date:** 2026-01-14 (Australia/Sydney)  
**Purpose:** Preserve current progress quality while removing the CEO from routine execution loops (first: waterboy work; later: micro decisions).  
**Interim target workflow:** CEO/COO converge on design+plan for one build → **handoff** → autonomous loop until terminal → CEO receives a single decision packet.

---

## 0. Executive Summary

### 0.1 What this delivers
A deterministic, resumable, budget-bounded build loop that executes a planned build without CEO shepherding and produces one of four explicit terminal outcomes with audit-grade artefacts:
- **PASS**
- **WAIVER_REQUESTED** (explicit CEO approval required)
- **ESCALATION_REQUESTED** (explicit CEO/COO decision required)
- **BLOCKED** (fail-closed)

### 0.2 Why now
The bottleneck is CEO friction (copy/paste, doc hunting, babysitting). This plan mechanizes execution via a deterministic artefact chain:
**Handoff Packet → Attempt Ledger → Review Packets → CEO Terminal Packet → Closure Bundle**.

### 0.3 Anti-zombie safeguards
- **Resumability:** Attempt Ledger is source of truth; controller resumes after crash.
- **No blind retry:** minimal failure taxonomy + hardcoded policy ship with the loop (atomic).
- **Budgets:** max attempts + max wall-clock + max tokens; exceed → terminal.
- **Deadlock prevention:** identical-hash/no-delta → terminal NO_PROGRESS.
- **Oscillation detection:** A→B→A loops terminate to prevent budget burn.
- **CI babysitting avoided:** PR gate verify-only; full loops nightly/on-demand.

### 0.4 What is deferred
- Mission synthesis / self-selection (Tier-4 autonomy) is Phase E and council-gated.
- Automated council runtime is not introduced in Phases A–D; governance-sensitive surfaces produce **ESCALATION_REQUESTED** with “Council recommended”.

---

## 1. Full Context

### 1.1 The problem
Progress quality is acceptable, but execution requires CEO involvement in:
- copy/paste, assembling context, shepherding loops (“waterboy work”)
- frequent small technical decisions (later target)

### 1.2 Target workflows

#### End state (north star)
CEO intent → COO convergence on design (optional council) → design review until pass → plan review until pass → builder executes and emits review packet → designer reviews until pass → optional council review until pass → validation/testing as needed → loop until complete → final signoff → CEO.

#### Interim state (near-term milestone)
CEO/COO converge on design+plan for one build → handoff → autonomous loop until terminal → CEO packet.

### 1.3 Priority order
- **P0:** Remove waterboy work first.
- **P1:** Remove small/highly technical decisions once loop reliability + escalation packets are good.

---

## 2. Binding Invariants

### 2.1 Human Burden Invariant
- The loop must not require the CEO to hand-construct complex schemas or hashes.
- One minimal “handoff” step must be sufficient to start execution.

### 2.2 Determinism & auditability
- Decisions must be explainable from recorded evidence.
- Attempt Ledger is the **Source of Truth**.
- No placeholders: every artefact must contain minimal, real, useful content.

### 2.3 Fail-closed posture
- If ambiguity cannot be resolved from canonical artefacts, stop safely with a terminal packet.
- Initial posture: **no auto-waive**. Waivers require explicit CEO approval.

### 2.4 No-babysitting CI
- PR CI must be verify-only and deterministic.
- Full loops run nightly/on-demand with strict budgets, never as a PR gate.

### 2.5 Definitions (hashes)
- **All hashes are SHA-256** unless explicitly stated otherwise.

---

## 3. Terminal Model

### 3.1 Terminal states
- **PASS** — build complete; acceptance criteria satisfied
- **WAIVER_REQUESTED** — non-critical deviation requires explicit waiver decision
- **ESCALATION_REQUESTED** — human decision required (ambiguity / governance surface / repeated non-convergence)
- **BLOCKED** — cannot proceed safely/deterministically within budgets or progress constraints

(Optional later)
- **WAIVED** — post-approval terminalization
- **CANCELLED** — operator stop

### 3.2 PASS criteria (explicit)
**PASS =**
1) required steps exit cleanly (exit_code == 0), AND  
2) required validators pass (schema/policy gates), AND  
3) forbidden token/secret scan passes (scope-bounded), AND  
4) evidence capture + hashes verify, AND  
5) **CEO terminal packet + closure bundle + ledger digest** are generated successfully.

### 3.3 WAIVER_REQUESTED vs BLOCKED
- **WAIVER_REQUESTED:** retry cap exhausted on **non-critical** defect(s) or acceptable deviation category, but policy disallows automatic acceptance. Produces a waiver packet for CEO approval.
- **BLOCKED:** deterministic failure not resolvable within mechanisms/budgets OR deadlock/no-progress OR critical failures persist. Produces a blocked packet.

---

## 4. Artefacts (minimum viable chain)

### 4.1 Attempt Ledger (Source of Truth; resumability)
**Format:** append-only **JSON Lines (`.jsonl`)**, one record per attempt; schema-validated before append.

Each attempt record includes:
- attempt_id, timestamps, run_id
- policy_version/hash
- input refs/hashes (handoff hash, plan hash)
- actions taken (commands; regen path)
- evidence pointers + evidence hashes
- diff hash + changed file list
- failure classification + terminal reason (if terminal)
- next action decision + rationale

**Resumability protocol (hard requirement):**
- On startup, Loop Controller hydrates from ledger.
- If non-terminal ledger exists, **resume from last_attempt + 1**, never restart from attempt 1.
- If `policy_hash(current) != policy_hash(recorded_in_ledger)` on resume → **ESCALATION_REQUESTED** reason `POLICY_CHANGED_MID_RUN`.

**Ledger integrity rule (hard requirement):**
- On startup, validate the ledger stream. If corrupt/truncated/invalid → **BLOCKED** reason `LEDGER_CORRUPT`. No recovery attempts.

### 4.2 Handoff Packet v0 (anti-waterboy input)
Single canonical artefact starting the loop.

**Versioning:**
- Includes `schema_version`.
- Controller validates compatibility; mismatch → **BLOCKED** reason `HANDOFF_VERSION_MISMATCH`.

**Avoiding CEO data entry: Handoff Scaffolder (thin CLI)**
- `lifeos handoff --intent "..." --plan <path> [--design <path>] ...`
- Validates paths, computes hashes, emits a deterministic Handoff Packet.

**Phasing:**
- **A0 (POC):** allow a test handoff fixture to prove the loop.
- **A1 (MVP):** ship scaffolder to eliminate waterboy work (P0 priority).

### 4.3 Review Packet (per attempt; no placeholders)
After each attempt and at terminal:
- diff summary + hashes
- what passed/failed (tests/validators/review)
- why policy chose next action
- next attempt plan (if any)
- evidence refs

### 4.4 CEO Terminal Packet (single skimmable artefact)
At terminal:
- outcome + short reason
- decision requested (if WAIVER/ESCALATION)
- evidence highlights (top 5)
- recommended next action (bounded)
- budgets consumed (attempts/tokens/wall-clock)
- refs to closure bundle + ledger digest

### 4.5 Closure Bundle (all terminal states)
Generated for PASS / WAIVER_REQUESTED / ESCALATION_REQUESTED / BLOCKED.
Includes: ledger digest, policy/config hashes, audit evidence set.

---

## 5. Default Budget Configuration (Phase A)
```yaml
budgets:
  max_attempts: 5
  max_tokens: 100000
  max_wall_clock_minutes: 30
  max_diff_lines_per_attempt: 300

6. Phases
Phase A (Atomic): Convergent Builder Loop + Basic Failure Classification + Hardcoded Policy

Objective: Prove the loop converges or terminates safely with resumability, budgets, deadlock prevention, and minimal classification.

P0 deliverables (ship together):
A1) Loop Controller state machine: Next_Action = f(Ledger) (stateful on disk)
A2) Attempt Ledger v0 + resumability + integrity rules
A3) Minimal failure taxonomy (at least):

TEST_FAILURE

SYNTAX_ERROR (parse/compile)

TIMEOUT

VALIDATION_ERROR

REVIEW_REJECTION (if review exists in-loop)

UNKNOWN (fail-closed)

terminal reasons: BUDGET_EXHAUSTED, NO_PROGRESS, OSCILLATION_DETECTED
A4) Hardcoded minimal policy (deterministic)
A5) Modification mechanism (selected): Option 1 — LLM regeneration with structured feedback + diff budget

If proposed diff exceeds max_diff_lines_per_attempt, do not apply; terminate ESCALATION_REQUESTED reason DIFF_BUDGET_EXCEEDED with candidate diff attached as evidence.
A6) Budgets enforced: max attempts OR max tokens OR max wall-clock (whichever first)
A7) Deadlock + oscillation prevention:

If hash(N) == hash(N-1) or diff delta == 0 → terminal BLOCKED reason NO_PROGRESS

If hash(N) == hash(N-2) → terminal ESCALATION_REQUESTED reason OSCILLATION_DETECTED
A8) Workspace semantics: prefer clean checkout per attempt (ledger/evidence persist only)
A9) Review packet per attempt + CEO terminal packet at end (no placeholders)

Phase A DoD:

Given a handoff, loop runs, classifies outcomes, respects budgets, resumes after crash, and terminates in PASS/WAIVER_REQUESTED/ESCALATION_REQUESTED/BLOCKED with complete packets + closure bundle.

Phase B: Configurable Policy Engine + Expanded Taxonomy + Waiver Workflow Wiring

Objective: Replace hardcoded policy with validated config; enrich taxonomy; formalize waiver approvals.

Phase C: Closure Automation (G-CBS + scans) for all terminal outcomes

Objective: Audit-grade terminalization is automatic.

Phase D: Continuous Dogfooding (CI + nightly/on-demand)

Objective: Run continuously without babysitting.

Phase E: Mission Synthesis (Tier-4 autonomy; council-gated)

Objective: Work selection + design/plan generation + iterative review until ready for handoff.

7. Council stance (reconciled)

No automated council runtime in A–D.

In A–D governance-sensitive work → ESCALATION_REQUESTED with “Council recommended” flag.

Council triggers become first-class only in Phase E.

8. CI Strategy

PR pipeline: validators + unit tests (+ optional verify-only micro-run). No full retries.

Nightly/on-demand: full bounded loop runs + closures.

External flake-prone dependencies are quarantined from PR gates.

9. Success Metrics (interim milestone)

CEO no longer performs copy/paste/doc hunting to run a build loop.

Loop resumes after crash without restarting.

Terminal packets are one-glance actionable.

PR CI is stable; nightlies carry iteration load.

Appendix — Phase A Implementation Checklist (updated)
B1. State machine + resumability

ledger hydration on start

resume from last attempt + 1

policy-hash mismatch on resume → ESCALATION_REQUESTED POLICY_CHANGED_MID_RUN

B2. Ledger schema + integrity

JSONL, schema-validated before append

startup validation; corruption → BLOCKED LEDGER_CORRUPT

B3. Minimal taxonomy + hardcoded policy

explicit mapping; deterministic outcomes

B4. Modification mechanism (locked)

LLM regen w/ structured feedback

enforce diff budget; exceed → ESCALATION_REQUESTED DIFF_BUDGET_EXCEEDED

B5. Budgets + termination rules

enforce attempts/tokens/wall-clock; exceed → terminal BUDGET_EXHAUSTED

B6. Deadlock + oscillation prevention (required)

hash(N)==hash(N-1) or delta==0 → BLOCKED NO_PROGRESS

hash(N)==hash(N-2) → ESCALATION_REQUESTED OSCILLATION_DETECTED

B7. Workspace semantics

clean checkout per attempt (preferred) with deterministic evidence capture

B8. Packets + closure (no placeholders)

review packet each attempt

CEO terminal packet + closure bundle + ledger digest for all terminal states

B9. Acceptance tests

crash/resume

budget exhaustion

no-progress

oscillation

deterministic replay
