# Phase B Activation Readiness Implementation Plan v1.2b

**Date**: 2026-01-15
**Target**: Unblock Phase B.2, fix waiver workflow, tighten governance assertions
**Expected Outcome**: Review_Packet_Phase_B_Loop_Controller_v1.2.md with suite-based status and evidence

---

## Executive Summary

Three critical blockers prevent Phase B activation readiness:

1. **P0.1 Circular Import (B.2)**: `test_checklists.py` cannot run due to runtime import cycle through `MissionContext`
2. **P0.2 Waiver Workflow Reachability**: Budget exhaustion prevents waiver artifact emission even when policy decides to terminate
3. **P0.3 Governance Escalation**: Three tests have relaxed assertions accepting both BLOCKED and ESCALATION_REQUESTED

**Solution Approach**:
- Break circular import by defining minimal Protocol in loop layer (zero runtime import from missions/*)
- Make policy decision first; emit terminal artifacts (waiver/escalation) EVEN if budget exhausted; budget only hard-stops RETRY
- Tighten governance assertions to deterministic ESCALATION_REQUESTED with structured reason validation

**Impact**: Unblock test_checklists.py, unskip 2 waiver tests, enforce governance determinism

---

## Critical Files

| File | Purpose | Lines |
|------|---------|-------|
| `runtime/orchestration/loop/checklists.py` | Break circular import (TYPE_CHECKING) | 12-23 |
| `runtime/orchestration/missions/autonomous_build_cycle.py` | Reorder checks (policy before budget) | 252-310 |
| `runtime/tests/orchestration/missions/test_loop_acceptance.py` | Tighten governance assertions | 743-747, 778-780, 808-813 |

---

## P0.1: Circular Import Resolution

### Problem
Runtime import cycle prevents `test_checklists.py` from running.

**Confirmed chain** (verify actual imports before implementing):
`test_checklists.py` → `checklists.py` → imports `MissionContext` from `missions/base.py` → `missions/__init__.py` eagerly imports mission types → `autonomous_build_cycle.py` → imports validators from `checklists.py` → cycle

Root cause: Loop layer (`checklists.py`) has runtime dependency on mission layer (`MissionContext`).

### Solution
Define minimal Protocol in loop layer to eliminate mission-layer runtime import.

**Minimal attempt (first)**: TYPE_CHECKING import for MissionContext.

**Why TYPE_CHECKING first**: Simplest change, standard Python idiom. Only switch to Protocol if runtime evaluation exists.

### Implementation

**Step 1: Reproduce ImportError**

Run and capture exact error:
```bash
pytest runtime/tests/orchestration/loop/test_checklists.py -v 2>&1 | head -50
```

**Step 2: Apply TYPE_CHECKING fix**

**File**: `runtime/orchestration/loop/checklists.py`

Locate MissionContext import (around line 21, verify actual line):
```python
from runtime.orchestration.missions.base import MissionContext
```

Replace with TYPE_CHECKING guard:
```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from runtime.orchestration.missions.base import MissionContext
```

**Step 3: Verify no runtime evaluation**

Search `checklists.py` for runtime uses of MissionContext:
```bash
grep -n "isinstance.*MissionContext\|get_type_hints\|__annotations__" runtime/orchestration/loop/checklists.py
```

**If ANY runtime evaluation found** → TYPE_CHECKING won't work, switch to Protocol:
```python
from typing import Protocol
from pathlib import Path

class ChecklistContext(Protocol):
    """Minimal interface for checklist validation (loop-layer only)."""
    repo_root: Path
    artifacts_root: Path
    run_id: str
```

Replace `MissionContext` type annotations with `ChecklistContext`, remove mission-layer import entirely.

**Step 4: Test fix**

```bash
pytest -q runtime/tests/orchestration/loop/test_checklists.py
```

**Expected**: No ImportError, tests run and pass.

**End state**: `checklists.py` has zero runtime imports from `runtime/orchestration/missions/*` (either via TYPE_CHECKING or Protocol)

### Verification

```bash
pytest runtime/tests/orchestration/loop/test_checklists.py -v
```

**Expected**: All ~40 tests pass (was 0 due to import error)

---

## P0.2: Waiver Workflow Reachability Under Budgets

### Problem
Budget exhaustion prevents waiver artifact emission even when policy decides retry exhaustion warrants waiver.

**Current behavior**:
- Policy says TERMINATE with WAIVER_REQUESTED after retry exhaustion
- Budget check runs BEFORE termination handling
- Budget exhausted → emit BLOCKED terminal, exit
- Waiver request artifact never emitted → tests skip

**Root cause**: Budget check gates ALL outcomes, but should only gate RETRY (not TERMINATE decisions).

### Solution
Evaluate policy decision FIRST. If policy says TERMINATE (with WAIVER_REQUESTED or ESCALATION_REQUESTED), emit those artifacts EVEN if budget exhausted. Budget only hard-stops RETRY.

### Implementation

**File**: `runtime/orchestration/missions/autonomous_build_cycle.py`

**Lines 252-310 (RESTRUCTURE)**:

Current flow:
1. Determine attempt ID
2. Budget check → exit if exhausted
3. Policy check → TERMINATE or RETRY
4. Handle termination
5. Continue loop

New flow:
1. Determine attempt ID
2. **Policy check → TERMINATE or RETRY** (moved earlier)
3. **Handle termination (including waiver emission)** (moved earlier)
4. **Budget check → exit if exhausted** (moved later)
5. Continue loop

**Specific Changes**:

1. **Move policy check** from line 267 → line 259 (before budget check)
2. **Move termination handling** from lines 276-299 → lines 267-293 (after policy check)
3. **Move budget check** from line 260 → line 295 (after policy check)
4. **Add comment** explaining policy-first semantics

**Detailed Changes**:

**Locate existing code** (confirm actual line numbers):
- Policy check: currently around line 267
- Budget check: currently around line 260
- Terminal outcome mapping: currently around lines 276-299

**Reorder logic** (policy before budget):
```python
# Inside while loop_active:

    attempt_id = ...  # Existing code

    # POLICY CHECK FIRST
    # Policy decides TERMINATE vs RETRY based on semantic rules (retry limits, escalation triggers)
    result = policy.decide_next_action(ledger)

    # Handle 2-tuple (Phase A) vs 3-tuple (Phase B) returns
    if len(result) == 2:
        action, reason = result
        terminal_override = None
    else:
        action, reason, terminal_override = result

    # If policy says TERMINATE, emit artifacts and exit (regardless of budget)
    if action == LoopAction.TERMINATE.value:
        # REUSE EXISTING TERMINAL OUTCOME MAPPING LOGIC
        # Do NOT simplify - preserve exact Phase A/B outcome/reason/success mapping
        outcome = TerminalOutcome.BLOCKED  # Default

        # Phase B: Check terminal_override
        if terminal_override == "WAIVER_REQUESTED":
            outcome = TerminalOutcome.WAIVER_REQUESTED
        elif terminal_override == "ESCALATION_REQUESTED":
            outcome = TerminalOutcome.ESCALATION_REQUESTED
        elif terminal_override == "BLOCKED":
            outcome = TerminalOutcome.BLOCKED
        elif terminal_override == "PASS":
            outcome = TerminalOutcome.PASS
        # Phase A: Fallback to reason-based mapping
        elif reason == TerminalReason.PASS.value:
            outcome = TerminalOutcome.PASS
        elif reason == TerminalReason.OSCILLATION_DETECTED.value:
            outcome = TerminalOutcome.ESCALATION_REQUESTED
        # ... (preserve all existing mapping logic)

        # Phase B.3: Emit waiver request if outcome is WAIVER_REQUESTED
        if outcome == TerminalOutcome.WAIVER_REQUESTED:
            self._emit_waiver_request(context, ledger, reason, total_tokens)

        # Emit terminal packet
        self._emit_terminal(outcome, reason, context, total_tokens, ledger=ledger)

        # IMPORTANT: Reuse existing success logic from Phase A
        # Do NOT change return value structure or success semantics
        return self._make_result(
            success=(outcome == TerminalOutcome.PASS),
            error=reason if outcome != TerminalOutcome.PASS else None
        )

    # BUDGET CHECK SECOND - only applies to RETRY (not TERMINATE)
    # Budget exhaustion blocks further retries but doesn't prevent policy-driven termination
    is_over, budget_reason = budget.check_budget(attempt_id, total_tokens)
    if is_over:
        self._emit_terminal(TerminalOutcome.BLOCKED, budget_reason, context, total_tokens, ledger=ledger)
        return self._make_result(success=False, error=budget_reason)

    # Policy said RETRY and budget allows it - continue loop execution...
```

**Critical Constraints**:
- **MUST reuse existing terminal outcome/reason mapping** (do not create simplified version)
- **MUST preserve Phase A return value semantics** (success flag must match existing logic)
- **MUST preserve Phase A/B compatibility** (2-tuple vs 3-tuple handling unchanged)
- Budget still prevents runaway loops (hard-stops RETRY, not TERMINATE)

**Key Semantic Change**:
- **Before**: Budget gates everything → BLOCKED if exhausted → policy unreachable
- **After**: Policy gates termination → waiver/escalation emitted → budget only gates retry

### Verification

```bash
pytest runtime/tests/orchestration/missions/test_loop_acceptance.py::TestPhaseB_WaiverWorkflow -v
```

**Expected**:
- `test_phaseb_waiver_approval_pass_via_waiver_approved`: **PASS** (was skipped)
- `test_phaseb_waiver_rejection_blocked_via_waiver_rejected`: **PASS** (was skipped)

---

## P0.3: Governance Escalation Tightening

### Problem
Three tests accept `outcome in ["BLOCKED", "ESCALATION_REQUESTED"]` but policy mandates deterministic `ESCALATION_REQUESTED` for governance violations.

**Governance Sources**:
- Protected paths: `config/governance/protected_artefacts.json`
- Failure routing: `config/loop/policy_v1.0.yaml` (GOVERNANCE_VIOLATION → ESCALATION_REQUESTED)
- Detection logic: `runtime/orchestration/loop/configurable_policy.py:_check_escalation_triggers()`

**Issue**: Tests use defensive `in [...]` assertions with comments like "may vary in test env" but governance escalation MUST be deterministic.

### Solution
Replace relaxed assertions with strict `== "ESCALATION_REQUESTED"`. Prefer structured reason validation (enum value) over substring matching.

### Implementation

**File**: `runtime/tests/orchestration/missions/test_loop_acceptance.py`

**Three Locations to Tighten**:

#### Location 1: Lines 743-747
**Test**: `test_phaseb_governance_surface_touched_escalation_override`

**BEFORE**:
```python
assert terminal_data["outcome"] in ["BLOCKED", "ESCALATION_REQUESTED"]
# Note: governance detection may vary in test env
```

**AFTER** (check if terminal_data has structured reason field):
```python
assert terminal_data["outcome"] == "ESCALATION_REQUESTED", \
    f"Expected ESCALATION_REQUESTED for governance surface, got {terminal_data['outcome']}"

# Prefer structured reason validation if available (e.g., terminal_data["reason_code"])
# Otherwise fallback to substring match
if "reason_code" in terminal_data or "terminal_reason" in terminal_data:
    reason_field = terminal_data.get("reason_code") or terminal_data.get("terminal_reason")
    assert "GOVERNANCE" in reason_field.upper() or "ESCALATION" in reason_field.upper(), \
        f"Expected governance reason code, got {reason_field}"
else:
    # Fallback: substring match on reason text
    assert "governance" in terminal_data["reason"].lower(), \
        f"Expected governance in reason, got {terminal_data['reason']}"
```

#### Location 2: Lines 778-780
**Test**: `test_phaseb_protected_path_escalation`

**BEFORE**:
```python
assert terminal_data["outcome"] in ["BLOCKED", "ESCALATION_REQUESTED"]
```

**AFTER** (check for structured reason):
```python
assert terminal_data["outcome"] == "ESCALATION_REQUESTED", \
    f"Expected ESCALATION_REQUESTED for protected path, got {terminal_data['outcome']}"

# Prefer structured reason validation
if "reason_code" in terminal_data or "terminal_reason" in terminal_data:
    reason_field = terminal_data.get("reason_code") or terminal_data.get("terminal_reason")
    assert "GOVERNANCE" in reason_field.upper() or "PROTECTED" in reason_field.upper(), \
        f"Expected governance/protected reason code, got {reason_field}"
else:
    # Fallback: substring match
    assert any(kw in terminal_data["reason"].lower() for kw in ["governance", "protected"]), \
        f"Expected governance/protected in reason, got {terminal_data['reason']}"
```

#### Location 3: Lines 808-813
**Test**: `test_phaseb_governance_violation_immediate_escalation`

**BEFORE**:
```python
assert terminal_data["outcome"] in ["ESCALATION_REQUESTED", "BLOCKED"]
```

**AFTER** (check for structured reason):
```python
assert terminal_data["outcome"] == "ESCALATION_REQUESTED", \
    f"Expected ESCALATION_REQUESTED for governance violation, got {terminal_data['outcome']}"

# Prefer structured reason validation
if "reason_code" in terminal_data or "terminal_reason" in terminal_data:
    reason_field = terminal_data.get("reason_code") or terminal_data.get("terminal_reason")
    assert "GOVERNANCE" in reason_field.upper(), \
        f"Expected governance reason code, got {reason_field}"
else:
    # Fallback: substring match
    assert "governance" in terminal_data["reason"].lower(), \
        f"Expected governance in reason, got {terminal_data['reason']}"
```

**Changes Per Location**:
1. Replace `in [...]` with `== "ESCALATION_REQUESTED"`
2. Add descriptive f-string assertion message showing actual value
3. Check for structured reason field (reason_code/terminal_reason) before substring matching
4. Remove defensive comments about test environment variance

**Governance Target Selection**:
Tests should load protected paths from `config/governance/protected_artefacts.json` (same source runtime uses), not hardcode literals.

### Verification

```bash
pytest runtime/tests/orchestration/missions/test_loop_acceptance.py::TestPhaseB_GovernanceEscalation -v
```

**Expected**: All 3 governance tests pass with strict assertions

**If Tests Fail**: Governance detection is broken (production bug), do NOT relax assertions.

---

## P0.4: Evidence + Review Packet

### Evidence Collection

**Commands**:
```bash
# Create return package directory
mkdir -p artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0

# 1. Git evidence
git diff > artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/git_diff.patch
git status --porcelain > artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/git_status.txt
git rev-parse HEAD > artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/git_commit.txt 2>&1 || echo "not in git repo" > artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/git_commit.txt

# 2. Test evidence (verbatim logs, no truncation, -q for quieter output)
pytest -q runtime/tests/orchestration/loop/test_checklists.py \
  > artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/pytest_test_checklists.log.txt 2>&1

pytest -q runtime/tests/orchestration/missions/test_loop_waiver_workflow.py \
  > artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/pytest_test_loop_waiver_workflow.log.txt 2>&1

pytest -q runtime/tests/orchestration/missions/test_loop_acceptance.py \
  > artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/pytest_test_loop_acceptance.log.txt 2>&1

# 3. Determinism check (run acceptance tests 3x, capture all)
(for i in 1 2 3; do
  echo "=== Run $i ==="
  pytest -q runtime/tests/orchestration/missions/test_loop_acceptance.py --tb=no
  echo ""
done) > artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/repeat_runs_test_loop_acceptance.log.txt 2>&1
```

**Expected**: All 3 runs show identical pass/skip counts (no flaky tests, no pytest plugins affecting determinism).

### Review Packet v1.2

**File**: `artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/Review_Packet_Phase_B_Loop_Controller_v1.2.md`

**Required Sections**:

1. **Executive Summary**: Suite-based status (avoid brittle N/N claims unless truly stable in this repo)
   - Phase B.2: test_checklists.py runnable (was blocked)
   - Phase B.3/B.4: waiver acceptance tests pass without skips (was 2 skipped)
   - Governance escalation: deterministic ESCALATION_REQUESTED (was relaxed)

2. **Test Results** (report actual counts from evidence logs):
   - Phase B.0 (config loader): X/X passing
   - Phase B.1 (policy engine): X/X passing
   - Phase B.2 (checklists): X/X passing (was blocked by import)
   - Phase B.3 (waiver workflow): X/X passing, 0 skipped (was Y/X, 2 skipped)
   - Phase B.4 (acceptance): X/X passing (was Y/X, 2 skipped)

3. **Issue Resolutions**:
   - P0.1: Circular import broken (Protocol-based interface, zero runtime import from missions/*)
   - P0.2: Waiver reachability fixed (policy-first, terminal artifacts emitted even if budget exhausted)
   - P0.3: Governance assertions tightened (structured reason validation, deterministic ESCALATION_REQUESTED)

4. **Determinism Evidence**: 3 repeated acceptance runs with identical pass/skip counts

5. **Evidence Manifest**: List all evidence files with SHA256 hashes

6. **Activation Recommendation**: GO/NO-GO with specific gates passed/remaining

### Return Package Structure

```
artifacts/for_ceo/Return_Packet_Phase_B_Activation_Readiness_v1.0/
├── FIX_RETURN.md (map P0.1-P0.4 → evidence refs)
├── git_diff.patch
├── git_status.txt
├── pytest_test_checklists.log.txt
├── pytest_test_loop_waiver_workflow.log.txt
├── pytest_test_loop_acceptance.log.txt
├── repeat_runs_test_loop_acceptance.log.txt (3 runs, determinism proof)
└── Review_Packet_Phase_B_Loop_Controller_v1.2.md
```

---

## Verification Strategy

### Baseline (Before Changes)

```bash
pytest runtime/tests/orchestration/loop/test_checklists.py -v 2>&1 | tee baseline_checklists.txt
# Expected: ImportError (circular import)

pytest runtime/tests/orchestration/missions/test_loop_acceptance.py -v 2>&1 | tee baseline_acceptance.txt
# Expected: 18/20 passing, 2 skipped (waiver tests)
```

### Post-Implementation (After Changes)

```bash
# 1. Checklist tests (Issue 1)
pytest runtime/tests/orchestration/loop/test_checklists.py -v
# Expected: N/N passing (all tests runnable)

# 2. Acceptance tests (Issues 2 & 3)
pytest runtime/tests/orchestration/missions/test_loop_acceptance.py -v
# Expected: 20/20 passing, 0 skipped

# 3. Full orchestration suite (regression check)
pytest runtime/tests/orchestration/ -v
# Expected: All passing, Phase A tests unchanged
```

### Determinism Check

```bash
# Run acceptance tests 3 times, capture pass/skip counts
for i in 1 2 3; do
  echo "=== Run $i ==="
  pytest -q runtime/tests/orchestration/missions/test_loop_acceptance.py --tb=no
done
# Expected: Identical pass/fail/skip counts across all runs (no flaky tests)
# Verify no pytest plugins affecting outcome (e.g., pytest-randomly)
```

---

## Success Criteria

### Quantitative
- ✅ test_checklists.py: Runnable (was blocked by import error)
- ✅ Waiver acceptance tests: 0 skipped (was 2 skipped)
- ✅ Governance tests: Strict assertions passing (was relaxed)
- ✅ Files Modified: 2-3 (checklists.py, autonomous_build_cycle.py, test_loop_acceptance.py)
- ✅ Lines Changed: ~40-60 (minimal change surface)

### Qualitative
- ✅ Determinism: 3/3 test runs produce identical results
- ✅ Governance Invariants: Protected path violations → ESCALATION_REQUESTED (not BLOCKED)
- ✅ Waiver Workflow: Retry exhaustion triggers waiver before budget ceiling
- ✅ Backward Compatibility: Phase A tests remain 6/6 passing
- ✅ No Mocking: All fixes use real implementations

---

## Risk Mitigation

### Fail-Closed Approach

**If ambiguity arises**:
1. STOP implementation immediately
2. Create `BLOCKED.md` in return folder with:
   - Observed behavior + minimal reproduction
   - 2-3 options with implications
   - Recommended default (fail-closed)
3. Do NOT guess or improvise
4. Do NOT relax assertions to force tests to pass
5. Do NOT add mocking to bypass failures

### Rollback Plan

All changes are surgical and easily reversible:
- **Issue 1**: Protocol definition + type annotation changes (revert to MissionContext import)
- **Issue 2**: ~30-40 lines reordered (revert check ordering in autonomous_build_cycle.py)
- **Issue 3**: 9-15 assertion lines (revert to `in [...]` pattern, remove reason validation)

### Risk Assessment

| Change | Risk | Mitigation |
|--------|------|------------|
| Protocol-based interface | LOW-MEDIUM | Protocol is duck-typed; autonomous_build_cycle already passes compatible context |
| Check reordering | MEDIUM | Extensive test coverage, must preserve Phase A/B outcome/success semantics |
| Assertion tightening | LOW | Test-only changes, reveals governance bugs if any (fail-closed) |

**Highest Risk**: P0.2 check reordering. Must verify Phase A tests remain passing (no regressions in 2-tuple path, success flag logic).

---

## Implementation Sequence

1. **P0.1 (Circular Import)** - Lowest risk, unblocks test file
2. **P0.3 (Governance Assertions)** - Test-only, reveals bugs if present
3. **P0.2 (Waiver Timing)** - Highest complexity, benefits from P0.1 test coverage
4. **Evidence Collection** - After all tests passing
5. **Review Packet v1.2** - Final synthesis and readiness assessment
