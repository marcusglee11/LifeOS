# Implementation Plan: Phase B.4 Loop Controller Acceptance Tests

## Objective

Add 12+ acceptance tests to `runtime/tests/orchestration/missions/test_loop_acceptance.py` to validate Phase B.4 Self-Building Loop Controller components (waiver workflow, governance escalation, PPV/POFV validation, canonical hashing).

## Context

**Current State:**
- Phase B.3 (Waiver Workflow) complete with 108 tests passing
- 6 existing Phase A acceptance tests in `test_loop_acceptance.py`
- Phase B components implemented: ConfigurableLoopPolicy, PreflightValidator (PPV), PostflightValidator (POFV), waiver workflow

**Requirements from Review Packet:**
- Add 12+ Phase B acceptance tests covering waiver workflows, governance escalation, PPV/POFV fail-closed behavior, and canonical hashing
- Maintain backward compatibility with all Phase A tests
- Follow existing test patterns and TDD principles

## Critical Files

**Primary Target:**
- `runtime/tests/orchestration/missions/test_loop_acceptance.py` - Add 14 new tests

**Dependencies (Read-only exploration):**
- `runtime/orchestration/missions/autonomous_build_cycle.py` - Loop controller mission
- `runtime/orchestration/loop/configurable_policy.py` - Config-driven policy engine
- `runtime/orchestration/loop/checklists.py` - PPV/POFV validators
- `runtime/orchestration/loop/config_loader.py` - Policy config loader
- `config/loop/policy_v1.0.yaml` - Policy configuration structure
- `scripts/loop/approve_waiver.py` - Waiver approval CLI

**Test References (for patterns):**
- `runtime/tests/orchestration/loop/test_configurable_policy.py` - Policy routing patterns
- `runtime/tests/orchestration/loop/test_checklists.py` - Checklist validation patterns
- `runtime/tests/orchestration/missions/test_loop_waiver_workflow.py` - Waiver workflow patterns

## Implementation Approach

### 1. Test Organization (14 tests total)

```
class TestPhaseB_WaiverWorkflow:
    1. test_phaseb_waiver_approval_pass_via_waiver_approved
    2. test_phaseb_waiver_rejection_blocked_via_waiver_rejected
    3. test_phaseb_waiver_ineligible_failure_blocked

class TestPhaseB_GovernanceEscalation:
    4. test_phaseb_governance_surface_touched_escalation_override
    5. test_phaseb_protected_path_escalation
    6. test_phaseb_governance_violation_immediate_escalation

class TestPhaseB_PreflightValidation:
    7. test_phaseb_ppv_blocks_invalid_packet_emission
    8. test_phaseb_ppv_determinism_anchors_missing
    9. test_phaseb_ppv_governance_surface_scan_detected

class TestPhaseB_PostflightValidation:
    10. test_phaseb_pofv_invalid_terminal_outcome_blocks
    11. test_phaseb_pofv_missing_next_actions_fails
    12. test_phaseb_pofv_debt_registration_validated

class TestPhaseB_CanonicalHashing:
    13. test_phaseb_policy_hash_canonical_crlf_lf_stability
    14. test_phaseb_policy_hash_bytes_differs_from_canonical
```

### 2. New Fixtures Required

**Fixture: `phaseb_context`**
- Creates MissionContext with Phase B policy config
- Plants valid `policy_v1.0.yaml` in `config/loop/`
- Initializes BACKLOG.md for debt registration
- Creates full repo structure (artifacts/, docs/, config/)

**Fixture: `mock_subs_phaseb`**
- Extends existing `mock_subs` fixture with Phase B-aware behavior
- Build returns `diff_summary` and `changed_files` for PPV validation
- Review returns `council_decision` with `synthesis`
- All missions include token accounting in evidence

### 3. Test Specifications Summary

#### Waiver Workflow Tests (3 tests)

**Test 1: Waiver Approval → PASS**
- Setup: TEST_FAILURE with retry_limit=3
- Execution: Exhaust retries → emit WAIVER_REQUEST → approve via CLI → resume
- Assertions: result.success=True, outputs["status"]="waived", debt_id in BACKLOG.md

**Test 2: Waiver Rejection → BLOCKED**
- Setup: Same as Test 1
- Execution: Exhaust retries → emit WAIVER_REQUEST → reject via CLI → resume
- Assertions: result.success=False, outcome="BLOCKED", reason="waiver_rejected", NO debt entry

**Test 3: Ineligible Failure → BLOCKED (no waiver)**
- Setup: SYNTAX_ERROR (ineligible)
- Execution: Single failure → immediate BLOCKED
- Assertions: NO waiver request emitted, outcome="BLOCKED"

#### Governance Escalation Tests (3 tests)

**Test 4: Governance Surface Touched**
- Setup: Modify `docs/00_foundations/Constitution.md`
- Execution: Exhaust retries with governance surface touched
- Assertions: outcome="ESCALATION_REQUESTED", NO waiver request (escalation overrides)

**Test 5: Protected Path Escalation**
- Setup: Modify `config/governance/protected_artefacts.json`
- Execution: Exhaust retries
- Assertions: outcome="ESCALATION_REQUESTED"

**Test 6: GOVERNANCE_VIOLATION Immediate**
- Setup: GOVERNANCE_VIOLATION failure class (retry_limit=0)
- Execution: Single attempt → immediate escalation
- Assertions: outcome="ESCALATION_REQUESTED", only 1 attempt

#### Preflight Validation Tests (3 tests)

**Test 7: PPV Blocks Invalid Packet**
- Setup: Force PPV PF-7 failure (budget state mismatch)
- Execution: Mission attempts to emit Review Packet
- Assertions: outcome="BLOCKED", reason="preflight_checklist_failed", NO Review Packet emitted

**Test 8: PPV Determinism Anchors Missing**
- Setup: Ledger header missing policy_hash
- Execution: Run mission
- Assertions: PPV PF-3 fails, outcome="BLOCKED"

**Test 9: PPV Governance Surface Scan**
- Setup: Build with governance path in diff
- Execution: Run mission
- Assertions: PPV PF-6 passes with evidence showing governance surface detected

#### Postflight Validation Tests (3 tests)

**Test 10: POFV Invalid Terminal Outcome**
- Setup: Force invalid outcome in terminal packet (e.g., "INVALID_OUTCOME")
- Execution: Mission attempts to emit terminal packet
- Assertions: POFV POF-1 fails, outcome="BLOCKED", reason="postflight_checklist_failed"

**Test 11: POFV Missing Next Actions**
- Setup: Terminal packet data without `next_actions` field
- Execution: Run to terminal state
- Assertions: POFV POF-6 fails, outcome="BLOCKED"

**Test 12: POFV Debt Registration Validation**
- Setup: Approve waiver with invalid debt_id format (contains line number)
- Execution: Resume after approval
- Assertions: POFV POF-4 fails, note about invalid debt ID format

#### Canonical Hashing Tests (2 tests)

**Test 13: CRLF vs LF Stability**
- Setup: Create two policy configs (one CRLF, one LF)
- Execution: Load both configs, compute canonical hashes
- Assertions: policy_hash_canonical identical for both, policy_hash_bytes differs

**Test 14: Canonical vs Bytes Hash**
- Setup: Load single config with CRLF
- Execution: Extract both hashes
- Assertions: policy_hash_canonical != policy_hash_bytes, both stored in ledger header

### 4. Testing Patterns

**Mock Strategy:**
- Use real PPV/POFV for positive tests (verify they work correctly)
- Mock PPV/POFV for negative tests (force specific check failures)
- Mock missions using `side_effect` for dynamic behavior
- Patch individual methods when testing fail-closed behavior

**Verification Pattern:**
```python
# 1. Terminal Packet
terminal_path = context.repo_root / "artifacts/CEO_Terminal_Packet.md"
assert terminal_path.exists()
# Parse JSON payload from markdown wrapper
# Verify outcome, reason, run_id, next_actions

# 2. Attempt Ledger
ledger_path = context.repo_root / "artifacts/loop_state/attempt_ledger.jsonl"
# Verify header, attempt records, failure_class

# 3. Checklist Artifacts
ppv_path = context.repo_root / "artifacts/loop_state" / f"PREFLIGHT_CHECK_{run_id}_attempt_0001.json"
# Verify status, individual check results, evidence

# 4. Waiver Decision
decision_path = context.repo_root / "artifacts/loop_state" / f"WAIVER_DECISION_{run_id}.json"
# Verify decision, debt_id format (no line numbers!)
```

### 5. Implementation Sequence

**Step 1: Infrastructure (Est. 1 hour)**
1. Create `phaseb_context` fixture with full repo structure
2. Create `mock_subs_phaseb` fixture with Phase B behaviors
3. Create helper functions (extract_json_payload, etc.)

**Step 2: Waiver Workflow Tests (Est. 2 hours)**
1. Implement Test 1 (waiver approval)
2. Implement Test 2 (waiver rejection)
3. Implement Test 3 (ineligible failure)

**Step 3: Governance Escalation Tests (Est. 1.5 hours)**
1. Implement Test 4 (governance surface)
2. Implement Test 5 (protected path)
3. Implement Test 6 (immediate escalation)

**Step 4: Validation Tests (Est. 2 hours)**
1. Implement Tests 7-9 (PPV tests)
2. Implement Tests 10-12 (POFV tests)

**Step 5: Canonical Hashing Tests (Est. 1 hour)**
1. Implement Test 13 (CRLF/LF stability)
2. Implement Test 14 (bytes vs canonical)

**Step 6: Integration & Verification (Est. 1 hour)**
1. Run all tests together
2. Verify Phase A tests still pass (backward compatibility)
3. Run with random order to verify independence

**Total Time: ~8.5 hours**

### 6. Critical Considerations

1. **Backward Compatibility**: Phase A tests use hardcoded policy (2-tuple return), Phase B uses config (3-tuple return)
2. **Test Isolation**: Use tmp_path for each test, reset mocks between tests
3. **Determinism**: Mock time/filesystem, use fixed timestamps, no race conditions
4. **Waiver Workflow**: Verify stable debt ID format (no line numbers: `DEBT-{run_id}`)
5. **Fail-Closed Validation**: PPV/POFV failures must block emission and override outcomes
6. **Evidence Artifacts**: Verify ledger, packets, checklists are created correctly
7. **Mock Complexity**: Use helper functions for common mock behaviors

## Verification Plan

### Test Execution
```bash
# Run all Phase B.4 tests
pytest runtime/tests/orchestration/missions/test_loop_acceptance.py::TestPhaseB_WaiverWorkflow -v
pytest runtime/tests/orchestration/missions/test_loop_acceptance.py::TestPhaseB_GovernanceEscalation -v
pytest runtime/tests/orchestration/missions/test_loop_acceptance.py::TestPhaseB_PreflightValidation -v
pytest runtime/tests/orchestration/missions/test_loop_acceptance.py::TestPhaseB_PostflightValidation -v
pytest runtime/tests/orchestration/missions/test_loop_acceptance.py::TestPhaseB_CanonicalHashing -v

# Run all acceptance tests (Phase A + Phase B)
pytest runtime/tests/orchestration/missions/test_loop_acceptance.py -v

# Verify backward compatibility (only Phase A)
pytest runtime/tests/orchestration/missions/test_loop_acceptance.py::test_crash_and_resume -v

# Verify test independence (random order)
pytest runtime/tests/orchestration/missions/test_loop_acceptance.py --random-order -v
```

### Success Criteria
- All 14 new Phase B.4 tests pass
- All 6 existing Phase A tests still pass
- Total: 20 acceptance tests passing
- No flaky tests (100% pass rate across 10 runs)
- Test execution time: <5 seconds per test
- Phase B components covered: waiver workflow (100%), governance escalation (100%), PPV/POFV (100%), canonical hashing (100%)

### Expected Test Output
```
test_loop_acceptance.py::test_crash_and_resume PASSED                    [  5%]
test_loop_acceptance.py::test_acceptance_oscillation PASSED              [ 10%]
test_loop_acceptance.py::test_verify_terminal_packet_structure PASSED    [ 15%]
test_loop_acceptance.py::test_diff_budget_exceeded PASSED                [ 20%]
test_loop_acceptance.py::test_policy_changed_mid_run PASSED              [ 25%]
test_loop_acceptance.py::test_workspace_reset_unavailable PASSED         [ 30%]
test_loop_acceptance.py::TestPhaseB_WaiverWorkflow::test_phaseb_waiver_approval_pass_via_waiver_approved PASSED [ 35%]
test_loop_acceptance.py::TestPhaseB_WaiverWorkflow::test_phaseb_waiver_rejection_blocked_via_waiver_rejected PASSED [ 40%]
test_loop_acceptance.py::TestPhaseB_WaiverWorkflow::test_phaseb_waiver_ineligible_failure_blocked PASSED [ 45%]
test_loop_acceptance.py::TestPhaseB_GovernanceEscalation::test_phaseb_governance_surface_touched_escalation_override PASSED [ 50%]
test_loop_acceptance.py::TestPhaseB_GovernanceEscalation::test_phaseb_protected_path_escalation PASSED [ 55%]
test_loop_acceptance.py::TestPhaseB_GovernanceEscalation::test_phaseb_governance_violation_immediate_escalation PASSED [ 60%]
test_loop_acceptance.py::TestPhaseB_PreflightValidation::test_phaseb_ppv_blocks_invalid_packet_emission PASSED [ 65%]
test_loop_acceptance.py::TestPhaseB_PreflightValidation::test_phaseb_ppv_determinism_anchors_missing PASSED [ 70%]
test_loop_acceptance.py::TestPhaseB_PreflightValidation::test_phaseb_ppv_governance_surface_scan_detected PASSED [ 75%]
test_loop_acceptance.py::TestPhaseB_PostflightValidation::test_phaseb_pofv_invalid_terminal_outcome_blocks PASSED [ 80%]
test_loop_acceptance.py::TestPhaseB_PostflightValidation::test_phaseb_pofv_missing_next_actions_fails PASSED [ 85%]
test_loop_acceptance.py::TestPhaseB_PostflightValidation::test_phaseb_pofv_debt_registration_validated PASSED [ 90%]
test_loop_acceptance.py::TestPhaseB_CanonicalHashing::test_phaseb_policy_hash_canonical_crlf_lf_stability PASSED [ 95%]
test_loop_acceptance.py::TestPhaseB_CanonicalHashing::test_phaseb_policy_hash_bytes_differs_from_canonical PASSED [100%]

======================== 20 passed in 45.23s ========================
```

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking Phase A tests | Maintain backward compatibility with 2-tuple vs 3-tuple return handling |
| Flaky tests | Use deterministic mocks, fixed timestamps, tmp_path isolation |
| Mock complexity | Extract helper functions, use fixtures for common patterns |
| Test execution time | Keep test data minimal, mock external dependencies |
| Waiver workflow race conditions | Atomic file writes, proper file existence checks |

## Next Steps After Implementation

1. **Create migration script** `migrate_phase_a_to_phase_b.py` (Phase B.4 task 2)
2. **Write documentation** `Loop_Policy_Configuration_Guide_v1.0.md` (Phase B.4 task 3)
3. **Generate CEO evidence package** with full pytest output, diffstat, committed config (Phase B.4 task 4)
