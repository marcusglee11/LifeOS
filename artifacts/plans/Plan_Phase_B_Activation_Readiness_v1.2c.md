# Phase B Activation Readiness Implementation Plan v1.2c

## Objective
Reach a **GO** decision for **Phase B activation** by closing the three activation blockers:

1) **B.2**: PPV/POFV checklist unit tests are blocked by a circular import.
2) **B.3/B.4**: Waiver approval/rejection acceptance paths are skipped/failing because budget exhaustion prevents waiver artifact emission.
3) **B.4**: Governance escalation acceptance tests are currently relaxed; they must be deterministic and strict.

This plan is **pass-by-construction**: it removes the two most common failure modes from prior iterations:
- accidental terminal mapping rewrites,
- brittle hardcoded governance targets / missing governance config in tmp repos.

---

## Executive Summary (what will change)
- **Circular import fix (B.2):** break the import cycle so `runtime/tests/orchestration/loop/test_checklists.py` imports and runs.
- **Waiver reachability fix (B.3/B.4):** adjust loop control flow so **budget gates RETRY only**, while **policy TERMINATE outcomes** (including WAIVER_REQUESTED / ESCALATION_REQUESTED) still emit artifacts even when budget is exhausted.
- **Governance determinism (B.4):** remove relaxed assertions; require strict `ESCALATION_REQUESTED`, deriving protected targets from the same protected-surface source the runtime uses, and ensuring that source exists in tmp repos used by tests.

---

## Critical Files (read-only discovery, then minimal edits)
### Primary code
- `runtime/orchestration/missions/autonomous_build_cycle.py` (loop controller mission)
- `runtime/orchestration/loop/checklists.py` (PPV/POFV validators; import cycle currently blocks tests)

### Primary tests
- `runtime/tests/orchestration/loop/test_checklists.py` (must run and pass)
- `runtime/tests/orchestration/missions/test_loop_acceptance.py` (Phase A + Phase B acceptance tests; governance + waiver assertions)
- `runtime/tests/orchestration/missions/test_loop_waiver_workflow.py` (waiver workflow patterns / invariants)

### Config / governance sources (must match runtime reality)
- Policy config used by the loop (discover exact path + filename in repo; commonly under `config/loop/`)
- Protected-surface source used by runtime governance checks (discover exact path; commonly under `config/governance/`)

---

## P0.1 — Circular Import Resolution (B.2)
### Problem
`runtime/tests/orchestration/loop/test_checklists.py` cannot run because importing `runtime/orchestration/loop/checklists.py` triggers an import cycle involving mission-layer types.

### Required end-state invariant
`runtime/orchestration/loop/checklists.py` MUST have **zero runtime imports** from `runtime/orchestration/missions/*`.

(TYPE_CHECKING imports are allowed.)

### Implementation (minimal, deterministic)
1) Reproduce and document the exact import chain causing the cycle.
2) Apply the smallest fix that achieves the end-state invariant:
   - Preferred: define a loop-local minimal context type (e.g., `Protocol`) expressing only what checklists use (repo_root/artifacts_root/run_id/etc.), and annotate against that.
   - Acceptable (only if safe): `from __future__ import annotations` + `TYPE_CHECKING` import of mission context, PROVIDED there is no runtime evaluation of the type (no `isinstance`, no `get_type_hints`, no reflection-driven evaluation).

### Verification
- `pytest -q runtime/tests/orchestration/loop/test_checklists.py`
- Confirm: test module imports cleanly; tests execute; no ImportError.

---

## P0.2 — Waiver Workflow Reachability Under Budgets (B.3/B.4)
### Problem
Budget exhaustion currently prevents waiver artifact emission even when policy decides termination (WAIVER_REQUESTED) is warranted after retry exhaustion.

### Required semantic invariant (activation-grade)
- **Policy TERMINATE outcomes must still emit their terminal artifacts even if the budget is exhausted.**
  - This includes **WAIVER_REQUESTED** and **ESCALATION_REQUESTED**.
- **Budget exhaustion must remain a hard ceiling on RETRY only.**
  - Budget may convert RETRY → BLOCKED (budget reason).
  - Budget must NOT prevent TERMINATE handling and emission.

### Implementation (PASS-BY-CONSTRUCTION; MINIMAL DIFF ONLY)
In `runtime/orchestration/missions/autonomous_build_cycle.py`:

1) Identify the existing loop block that:
   - evaluates policy decision,
   - checks budget,
   - emits terminal / waiver / escalation artifacts.

2) Apply ONLY this structural change:
   - **Evaluate policy decision first.**
   - **If policy says TERMINATE:** run the existing TERMINATE-handling path **unchanged** and return.
   - **Else (policy says RETRY):** perform budget check.
     - If over budget: emit budget BLOCKED terminal and return.
     - If not: continue retry loop.

3) Do NOT rewrite or simplify terminal outcome/reason mapping.
   - The termination handler must remain identical to prior behavior (Phase A semantics, Phase B semantics, success/error mapping, return structure).
   - Do NOT introduce a new mapping table, "default BLOCKED" logic, or reduced outcome set.

### Verification
- Ensure previously skipped waiver approval/rejection acceptance tests are no longer skipped and now pass:
  - `pytest -q runtime/tests/orchestration/missions/test_loop_acceptance.py`
  - `pytest -q runtime/tests/orchestration/missions/test_loop_waiver_workflow.py`

- Add one safety confirmation (may already exist as a test):
  - Verify there is still **no code path** where RETRY proceeds after budget exhaustion.

---

## P0.3 — Governance Escalation Tightening (B.4)
### Problem
Governance acceptance tests currently allow multiple outcomes (e.g., BLOCKED or ESCALATION_REQUESTED), which is incompatible with activation-grade determinism.

### Requirements
1) Governance escalation acceptance tests MUST assert:
   - `terminal_data["outcome"] == "ESCALATION_REQUESTED"` (or the canonical enum serialization)
2) Governance targets MUST NOT be hardcoded guessed literals.
   - The test must derive protected targets from the **same protected-surface source the runtime uses**.
3) The protected-surface source MUST exist in tmp repos used by tests.
   - If tests execute against a tmp repo_root, the fixture must plant/copy the protected-surface source into the tmp repo at the exact relative path the runtime expects.

### Implementation
1) Locate the governance protected-surface source actually used by runtime (path + loader).
2) Update the relevant acceptance tests to:
   - Load protected targets from that source (not hardcoded constants).
   - Select a representative protected path deterministically.
3) Ensure the test fixture (or test setup) makes the source available under tmp repo_root:
   - Copy the repo's protected-surface config file into the tmp repo at the runtime-expected relative path, OR
   - Use an existing supported config mechanism that points the runtime to the same source.

### Assertion strategy (non-brittle)
- Prefer structured reason keys/codes if present (e.g., serialized enum, `reason_code`).
- Avoid substring matching on English phrases unless there is no structured alternative.

### Verification
- `pytest -q runtime/tests/orchestration/missions/test_loop_acceptance.py`
- Confirm governance tests assert strict escalation and pass.

---

## Evidence Collection (verbatim, audit-friendly)
Create the return directory up front:
- `mkdir -p artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/`

Capture environment stamps:
- `python -V`
- `pytest --version`
- `git rev-parse HEAD` (if available)
- `git status --porcelain`

Capture diffs:
- `git diff > artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/git_diff.patch`

Capture verbatim test logs (no truncation):
- `pytest -q runtime/tests/orchestration/loop/test_checklists.py | tee .../pytest_test_checklists.log.txt`
- `pytest -q runtime/tests/orchestration/missions/test_loop_waiver_workflow.py | tee .../pytest_test_loop_waiver_workflow.log.txt`
- `pytest -q runtime/tests/orchestration/missions/test_loop_acceptance.py | tee .../pytest_test_loop_acceptance.log.txt`

Determinism check (no plugins):
- Run acceptance suite 3x (same command), capture all outputs:
  - `pytest -q runtime/tests/orchestration/missions/test_loop_acceptance.py` (x3)
- Record pass/fail/skip counts; expectation: identical across runs; **0 skipped**.

---

## Verification Strategy
### Baseline (before changes; confirm current failure modes)
- `pytest -q runtime/tests/orchestration/loop/test_checklists.py`
  - Expected: ImportError (circular import) OR tests unrunnable
- `pytest -q runtime/tests/orchestration/missions/test_loop_acceptance.py`
  - Expected: waiver tests skipped and/or governance assertions relaxed

### Post-implementation (after changes; activation bar)
1) **Checklist suite runnable and passing:**
   - `pytest -q runtime/tests/orchestration/loop/test_checklists.py`
2) **Waiver workflow suite passing:**
   - `pytest -q runtime/tests/orchestration/missions/test_loop_waiver_workflow.py`
3) **Acceptance suite passing with strict governance + no skips:**
   - `pytest -q runtime/tests/orchestration/missions/test_loop_acceptance.py`
   - Repeat x3: identical counts; 0 skipped

Optional regression (only if repo norms require):
- `pytest -q runtime/tests/orchestration/` (or the repo's standard minimal CI subset)

---

## Success Criteria (Phase B activation GO gate)
### Quantitative
- `runtime/tests/orchestration/loop/test_checklists.py` runs and passes (no ImportError).
- `runtime/tests/orchestration/missions/test_loop_waiver_workflow.py` passes.
- `runtime/tests/orchestration/missions/test_loop_acceptance.py` passes with **0 skipped**.
- Acceptance suite repeated 3x produces identical pass/fail/skip counts (no flake).

### Qualitative (invariants proven by tests)
- **Import boundary:** loop/checklists has no runtime dependency on mission package.
- **Budget invariant:** budget exhaustion blocks further RETRY, but does not prevent emission of policy TERMINATE artifacts.
- **Governance invariant:** protected-surface violation deterministically results in ESCALATION_REQUESTED with non-brittle reason validation.
- **Backward compatibility:** Phase A acceptance behavior remains unchanged (same tests passing).

---

## Risk Mitigation
### Highest-risk area: waiver/budget ordering
Mitigation: enforce "minimal diff only" and explicitly forbid terminal mapping rewrites.

### Governance configuration risk (missing source in tmp repo)
Mitigation: explicitly plant/copy protected-surface source into tmp repo in fixtures or use runtime-supported config pointing to the same source.

### Rollback
- Keep diffs small and localized:
  - checklists.py import boundary fix
  - autonomous_build_cycle.py budget gate placement
  - test assertions + fixture planting for governance config
- If regressions occur, revert to prior commit and attach minimal repro + diff.

---

## Implementation Sequence (recommended)
1) P0.1 circular import fix + verify `test_checklists.py`
2) P0.2 waiver reachability fix (budget gate on RETRY only) + verify waiver acceptance tests unskipped
3) P0.3 governance tightening + ensure protected-surface source exists in tmp repo + strict assertions
4) Full verification runs + 3x determinism run + evidence pack + update review packet

---

## Return Package (required)
Write the following files under:
`artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/`

- `FIX_RETURN.md` (map P0.1–P0.3 + Success Criteria → evidence filenames)
- `git_diff.patch`
- `git_status.txt`
- `pytest_test_checklists.log.txt`
- `pytest_test_loop_waiver_workflow.log.txt`
- `pytest_test_loop_acceptance.log.txt`
- `repeat_runs_test_loop_acceptance.log.txt`
- Updated `Review_Packet_Phase_B_Loop_Controller_v1.2.md` reflecting suite-based results and activation recommendation (GO/NO-GO) consistent with evidence.
