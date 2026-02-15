Tier-1 Hardening Work Plan v0.1.md

Execution Target: COO Runtime
Authority: Architecture & Ideation Project
Purpose: Convert Audit Findings into an executable, agent-driven plan with minimal human touchpoints.

0. Execution Model

Runtime executes all Fix Packs sequentially.

Antigrav performs code/doc edits only under Runtime-issued missions.

Human participates only at the following points:

Approve this Work Plan.

Veto specific Fix Packs (rare).

Approve Tier-1 Readiness after Stage 1 completes.

Everything else is agent-side action.

Stage 1 — Mandatory Fix Packs (Pre-BLOCKER)

Goal: Achieve deterministic, safe, human-minimal Tier-1 runtime suitable for Tier-2 Activation.

These five Fix Packs must complete before any Tier-2 work begins.

FP-3.1 — Determinism Suite & FSM Validation

Owner: Runtime
Contributor: Antigrav (code edits)

Deliverables:

Determinism test module (test_determinism.py) that runs missions 3 times and does byte-level comparison.

FSM transition tests (legal + illegal).

Removal or isolation of nondeterministic sources (time, random, OS entropy).

Acceptance Criteria:

All tests pass deterministically across 3+ consecutive harness runs.

Runtime produces a structured determinism report.

FP-3.2 — AMU₀ Discipline & State Lineage

Owner: Runtime
Contributor: Antigrav

Deliverables:

Implement create_amu0_baseline, restore_from_amu0, promote_run_to_amu0.

State lineage tests verifying byte-identical rollback.

Strict single-root state directory with no leakage.

Acceptance Criteria:

AMU₀ operations produce deterministic, repeatable state snapshots.

Rollback always restores the exact AMU₀ baseline (byte-level).

FP-3.3 — DAP Write Gateway & INDEX Coherence

Owner: Runtime
Contributor: Antigrav

Deliverables:

Central Write Gateway validating all write operations (path, name, version, boundary).

Antigrav forced to route all writes through this gateway.

Automatic INDEX reconciliation on all write operations.

Acceptance Criteria:

All artefacts follow deterministic naming.

No out-of-bound writes permitted.

INDEX files remain perfectly in sync.

FP-3.7 — Anti-Failure Workflow Validator

Owner: Runtime
Contributor: Antigrav

Deliverables:

Workflow Validator module enforcing:

≤5 steps total

≤2 human steps

No “routine human ops” allowed

Antigrav mission wrapper must pass through validator before execution.

Acceptance Criteria:

Runtime rejects any workflow violating Anti-Failure constraints.

Validator produces structured explanations and suggested automation.

FP-3.9 — Governance Protections & Autonomy Ceilings

Owner: Runtime
Contributor: Antigrav

Deliverables:

Protected Artefact Registry (specs, constitutional docs).

Hard write-blocking for protected files.

Autonomy ceilings enforced in Runtime; Antigrav missions carry scope metadata.

Acceptance Criteria:

Impossible for Runtime or Antigrav to modify protected artefacts.

Attempted violations fail deterministically with a governance error.

Autonomy ceilings prevent unsafe mission expansion.

End of Stage 1

Completion Condition:

All five Fix Packs implemented

All tests pass

Determinism suite clean

AMU₀ discipline validated

Human-minimisation enforced

Governance boundaries enforced

After this, Runtime is allowed to execute Tier-2 Activation.

Human Action Required at this point: “Approve Tier-1 Readiness”.

Stage 2 — Recommended but Not Required for Tier-2

These Fix Packs improve robustness, maintainability, and productisation but are not necessary for autonomy or orchestration.

FP-3.4 — Runtime–Kernel Contract Tests

Owner: Runtime
Adds integration tests across kernel and FSM boundaries.

FP-3.5 — Runtime Operation Contracts

Owner: Runtime
Creates the canonical operation contract document + tests tied to contracts.

FP-3.6 — Tier-1 Test Harness v1.0

Owner: Runtime
Creates deterministic command to run full Tier-1 suite.

FP-3.8 — Antigrav Mission & Pack Schema

Owner: Runtime + Antigrav
Defines strict schemas for Fix/Review Packs.

FP-3.10 — Productisation Pre-Work

Owner: Runtime
Stabilises CLI and install flow.

7. Work Gate Sequence (Deterministic Order)

G1: Initialise Work Plan

Freeze current repo state as PRE_HARDENING_AMU0.

G2: Execute Stage 1

Run Fix Packs in this exact order:

FP-3.1

FP-3.2

FP-3.3

FP-3.7

FP-3.9

After each Fix Pack, run determinism suite + AMU₀ rollback checks.

Abort if failures emerge; Runtime escalates to you only if needed.

G3: Stage-1 Completion Gate

Runtime generates Tier1_Hardening_Completion_Report_v0.1.md.

You approve or veto readiness to proceed to Tier-2.

G4: Execute Stage 2 (optional, parallelisable)

Runtime and Antigrav execute FP-3.4 → FP-3.10 in any order.

All results logged into Tier1_Enhancement_Log_v0.1.md.

8. Human Requirements Summary (Minimal)

You will perform only three actions:

Approve Work Plan v0.1 (now)

Receive Tier-1 Completion Report

Approve or veto Tier-1 readiness

No other human steps are in scope.

