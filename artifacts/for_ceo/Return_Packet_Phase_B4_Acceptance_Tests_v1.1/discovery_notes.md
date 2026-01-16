# Discovery Notes: Phase B.4 Acceptance Tests Implementation

**Date:** 2026-01-14
**Task:** Implement 14 Phase B.4 acceptance tests for loop controller
**Branch:** gov/repoint-canon
**Commit:** 869d1580a5aad934beae88a82bf81299c6dba5e4

---

## Summary

Implemented 14 Phase B.4 acceptance tests in `runtime/tests/orchestration/missions/test_loop_acceptance.py`:
- **11 tests PASSING** (6 Phase A + 5 Phase B.4)
- **9 tests FAILING** (deeper integration issues with Phase B activation)

**Key Achievement**: Fixed config validation issues - canonical hashing tests now passing.

---

## Stable Checklist IDs (Discovered P0.1)

### PPV (PreflightValidator) - 8 checks
Discovered in `runtime/orchestration/loop/checklists.py`:
- **PF-1**: Schema pass
- **PF-2**: Evidence pointers
- **PF-3**: Determinism anchors (policy_hash in ledger)
- **PF-4**: Repro steps
- **PF-5**: Taxonomy
- **PF-6**: Governance surface scan
- **PF-7**: Budget state (token accounting)
- **PF-8**: Delta summary

### POFV (PostflightValidator) - 6 checks
- **POF-1**: Terminal outcome unambiguous
- **POF-2**: (Not documented in initial scan)
- **POF-3**: (Not documented in initial scan)
- **POF-4**: Debt registration validated (stable ID format)
- **POF-5**: (Not documented in initial scan)
- **POF-6**: No dangling state (next_actions present)

---

## Protected Paths (Discovered P0.1)

Source: `config/governance/protected_artefacts.json`

```json
{
  "protected_paths": [
    "docs/00_foundations",
    "docs/01_governance",
    "config/governance/protected_artefacts.json"
  ]
}
```

---

## Waiver Decision Format (Discovered P0.1)

**Path**: `artifacts/loop_state/WAIVER_DECISION_{run_id}.json`

**Stable Debt ID Format**: `DEBT-{run_id}` (no line numbers, no colons)

Example from `runtime/orchestration/missions/autonomous_build_cycle.py:184`:
```python
decision_path = context.repo_root / "artifacts/loop_state" / f"WAIVER_DECISION_{run_id}.json"
```

---

## Policy Config Validation Requirements (Discovered P0.2-P0.3)

### Required Sections (PolicyConfigLoader.REQUIRED_SECTIONS)
From `runtime/orchestration/loop/config_loader.py:44-52`:
1. `schema_version`
2. `policy_metadata`
3. `budgets`
4. `failure_routing`
5. `waiver_rules`
6. `progress_detection`
7. `determinism`

### Required Policy Metadata (line 62-67)
1. `version`
2. `effective_date`
3. `author` (CRITICAL - was missing, caused failures)
4. `description` (CRITICAL - was missing, caused failures)

### Required Budgets (line 54-60)
1. `max_attempts`
2. `max_tokens`
3. `max_wall_clock_minutes`
4. `max_diff_lines_per_attempt`
5. `retry_limits` (dict with all 11 failure classes)

### Failure Routing Constraints
- Must include ALL 11 FailureClass enum members:
  - TEST_FAILURE, SYNTAX_ERROR, TIMEOUT, VALIDATION_ERROR, REVIEW_REJECTION,
  - DEPENDENCY_ERROR, ENVIRONMENT_ERROR, TOOL_INVOCATION_ERROR, CONFIG_ERROR,
  - GOVERNANCE_VIOLATION, UNKNOWN
- `terminal_reason` must be valid TerminalReason enum member (e.g., CRITICAL_FAILURE, MAX_RETRIES_EXCEEDED, not "FAIL" or "F")
- `terminal_outcome` must be valid TerminalOutcome enum member (PASS, BLOCKED, ESCALATION_REQUESTED)

### Progress Detection Constraints
- `oscillation_lookback` must be >= 2 (not 1!)
- `no_progress_lookback` must be >= 1

---

## Tests Implemented

### Group 1: Waiver Workflow (3 tests) - ALL FAILING
**Status**: Mock exhaustion (StopIteration) and "not enough values to unpack"

1. `test_phaseb_waiver_approval_pass_via_waiver_approved` - FAILED
2. `test_phaseb_waiver_rejection_blocked_via_waiver_rejected` - FAILED
3. `test_phaseb_waiver_ineligible_failure_blocked` - FAILED

**Root Cause**: Loop not activating Phase B mode (ConfigurableLoopPolicy), still using hardcoded Phase A policy which returns 2-tuple instead of 3-tuple.

### Group 2: Governance Escalation (3 tests) - ALL FAILING
**Status**: Same root cause as waiver tests

1. `test_phaseb_governance_surface_touched_escalation_override` - FAILED
2. `test_phaseb_protected_path_escalation` - FAILED
3. `test_phaseb_governance_violation_immediate_escalation` - FAILED

**Root Cause**: Getting BLOCKED instead of ESCALATION_REQUESTED, likely because Phase B policy not activated.

### Group 3: Preflight Validation (3 tests) - 2 PASSING, 1 FAILING

1. `test_phaseb_ppv_blocks_invalid_packet_emission` - PASSED ✓
2. `test_phaseb_ppv_determinism_anchors_missing` - FAILED (KeyError: 'policy_hash' in ledger)
3. `test_phaseb_ppv_governance_surface_scan_detected` - PASSED ✓

**Fix for Test 1**: Config now includes all required fields (author, description)

### Group 4: Postflight Validation (3 tests) - 1 PASSING, 2 FAILING

1. `test_phaseb_pofv_invalid_terminal_outcome_blocks` - FAILED (budget exhaustion before POFV runs)
2. `test_phaseb_pofv_missing_next_actions_fails` - PASSED ✓
3. `test_phaseb_pofv_debt_registration_validated` - FAILED (StopIteration - mock exhaustion)

### Group 5: Canonical Hashing (2 tests) - ALL PASSING ✓

1. `test_phaseb_policy_hash_canonical_crlf_lf_stability` - PASSED ✓
2. `test_phaseb_policy_hash_bytes_differs_from_canonical` - PASSED ✓

**Fix**: Created complete minimal configs with all required sections and valid enum values.

---

## Fixes Applied

### Fix 1: Add Missing Author/Description to phaseb_context Fixture
**File**: `runtime/tests/orchestration/missions/test_loop_acceptance.py:246-251`

Before:
```yaml
policy_metadata:
  version: "phase_b_test_v1.0"
  effective_date: "2026-01-14"
```

After:
```yaml
policy_metadata:
  version: "phase_b_test_v1.0"
  effective_date: "2026-01-14"
  author: "Test Harness"
  description: "Phase B.4 acceptance test policy configuration"
```

### Fix 2: Complete Minimal Config for Canonical Hashing Tests
**File**: `runtime/tests/orchestration/missions/test_loop_acceptance.py:990-1051`

Added all required sections:
- Complete `budgets` with all fields
- Complete `failure_routing` with all 11 failure classes
- Valid `terminal_reason` enum values (CRITICAL_FAILURE, MAX_RETRIES_EXCEEDED, etc.)
- Fixed `oscillation_lookback: 2` (was 1, must be >= 2)
- Valid `policy_change_reason: POLICY_CHANGED_MID_RUN` (not "POLICY_CHANGED")

---

## Blockers

### BLOCKER-1: Phase B Policy Activation Not Triggered
**Severity**: P0 - Blocks 9/14 tests

**Symptom**: Loop controller using hardcoded Phase A policy instead of ConfigurableLoopPolicy

**Evidence**:
- Tests expect waiver request emission → not emitted
- Tests expect governance escalation → get BLOCKED instead
- ValueError: "not enough values to unpack (expected 2, got 0)" → Phase B returns 3-tuple, Phase A returns 2-tuple

**Investigation Required**:
- How does `autonomous_build_cycle.py` detect Phase B mode?
- Does it check for `config/loop/policy_v1.0.yaml` existence?
- Need to trace `_get_policy_decision()` or equivalent method

### BLOCKER-2: Ledger Header Structure Mismatch
**Severity**: P1 - Blocks 1 test

**Symptom**: KeyError: 'policy_hash' when reading ledger header

**Evidence**: Test `test_phaseb_ppv_determinism_anchors_missing` expects to read `policy_hash` from ledger but key doesn't exist

**Investigation Required**:
- What is correct ledger header format for Phase B?
- Does Phase B ledger require `policy_hash_canonical` and `policy_hash_bytes`?

### BLOCKER-3: Mock Exhaustion (StopIteration)
**Severity**: P2 - Blocks 4 tests

**Symptom**: Mock side_effect exhausted - loop making more calls than mocked

**Root Cause**: Phase B loop may have different control flow than Phase A (more retries, different routing)

**Fix**: Need to provide more mock responses matching actual Phase B flow

---

## Fixtures Created

### phaseb_context
**Path**: `runtime/tests/orchestration/missions/test_loop_acceptance.py:224-370`

Creates complete Phase B repo structure:
- `artifacts/loop_state/` (ledger, waiver files, checklists)
- `config/loop/policy_v1.0.yaml` (valid Phase B policy)
- `config/governance/protected_artefacts.json`
- `docs/11_admin/BACKLOG.md` (debt registration)
- `docs/00_foundations/` (governance paths)
- `docs/01_governance/` (governance paths)

### mock_subs_phaseb
**Path**: `runtime/tests/orchestration/missions/test_loop_acceptance.py:372-422`

Phase B-aware mocking:
- Build returns `diff_summary` and `changed_files` (for PPV validation)
- Review returns `council_decision` with `synthesis`
- All missions include token accounting in evidence

---

## Test Metrics

### Before This Work
- 6 Phase A tests: ALL PASSING
- 0 Phase B.4 tests

### After This Work
- **Total**: 20 tests (6 Phase A + 14 Phase B.4)
- **Passing**: 11 (6 Phase A + 5 Phase B.4)
- **Failing**: 9 (all Phase B.4)
- **Pass Rate**: 55%

### Phase B.4 Breakdown by Group
- Waiver Workflow: 0/3 passing (0%)
- Governance Escalation: 0/3 passing (0%)
- Preflight Validation: 2/3 passing (67%)
- Postflight Validation: 1/3 passing (33%)
- Canonical Hashing: 2/2 passing (100%) ✓

---

## Code Artifacts

### Lines Added
- **Total**: ~700 lines
- **Fixtures**: ~150 lines
- **Helper Functions**: ~50 lines
- **Tests**: ~500 lines

### Files Modified
1. `runtime/tests/orchestration/missions/test_loop_acceptance.py` (+700 lines)

---

## Next Steps (For Follow-up)

1. **Investigate Phase B Activation** (BLOCKER-1)
   - Read `autonomous_build_cycle.py` policy selection logic
   - Determine how to trigger ConfigurableLoopPolicy in tests
   - May need to mock or patch policy loader

2. **Fix Ledger Header Format** (BLOCKER-2)
   - Document correct Phase B ledger header schema
   - Update test fixtures to plant correct headers

3. **Extend Mock Coverage** (BLOCKER-3)
   - Profile actual Phase B loop flow
   - Provide sufficient mock responses for retry cycles

4. **Run Repeat Stability Check** (P0.6)
   - Execute test_loop_acceptance.py 5 times sequentially
   - Verify no flaky tests (100% consistency)

---

## Artifact References

### Test Logs
- `/tmp/pytest_test_loop_acceptance.log` - Initial run (9 failures)
- `/tmp/pytest_test_loop_acceptance_v2.log` - After config fixes (9 failures, 2 canonical hashing now pass)
- `/tmp/pytest_canonical_hashing.log` - Canonical hashing isolated run (2 failures due to invalid enums)
- `/tmp/pytest_canonical_hashing_final.log` - Canonical hashing final (2 PASSING)
- `/tmp/pytest_test_loop_waiver_workflow.log` - Waiver workflow suite (4/4 pass, 4/4 fail - different subset)
- `/tmp/pytest_test_checklists.log` - Checklists suite (circular import error - pre-existing)

### Environment
- Python: 3.14.2
- Pytest: 9.0.2
- Git Commit: 869d1580a5aad934beae88a82bf81299c6dba5e4
- Branch: gov/repoint-canon

### Diff
- `/tmp/git_diff.patch` - 1434 lines changed in test_loop_acceptance.py
