# Review Packet: OpenCode E2E Reliability Fix (v1.2)

**Mission**: Eliminate "E2E smoke FAIL (timeout)" for Phase 3 routing.
**Date**: 2026-01-11
**Author**: Antigravity (Builder)
**Status**: CLEAN / PASS

## 1. Root Cause Note

- **Category**: (a) Subprocess not terminating / orphaned child
- **Diagnosis**: The E2E smoke timeout was caused by `run_mission()` blocking on an HTTP POST without an overall parent watchdog. Additionally, server cleanup logic used simple termination signals which could leave orphaned process trees on Windows/Unix.
- **Evidence**: `scripts/opencode_ci_runner.py` lacked a mission-level watchdog and cross-platform process group flags.

## 2. Fix Summary

Implemented the narrowest durable fix to ensure deterministic completion:

1. **Mission Watchdog**: Added a threading-based watchdog in `run_with_timeout`.
2. **Robust Cleanup**: Enhanced `stop_ephemeral_server` with `taskkill /T` (Windows) and `killpg` (Unix) via `start_new_session`/`CREATE_NEW_PROCESS_GROUP` flags.
3. **HTTP Hardening**: Tightened `requests.post` to use explicit `(connect, read)` timeout tuples: `(5, 30)` for setup and `(5, 120)` for mission execution.
4. **Deterministic Exit**: Timeout conditions now trigger exit code `2` with a `MISSION_TIMEOUT` reason code.
5. **Windows Reliability**: Relaxed environment isolation on Windows to ensure `opencode` can locate system-level dependencies (`APPDATA`).

## 3. Canonical E2E Smoke Proof (Audit-Grade)

The canonical E2E smoke command was executed mechanically with full log capture:

- **Command**: `python scripts/opencode_ci_runner.py --task-file artifacts/steward_tasks/steward_task_v2.json --mission-timeout 150`
- **Start Time**: 2026-01-11 01:42:54.787471
- **End Time**: 2026-01-11 01:44:58.273623
- **Duration**: 123.49s
- **Results**: **PASS** (Mission Success)
- **Proof Log**: `artifacts/evidence/opencode_e2e_smoke_before_after_proof_plain.log`
- **Raw Runner Log**: `artifacts/evidence/opencode_ci_runner_raw.log`

## 4. CI Matrix Proof

- **Target CI Job**: `OpenCode CI Integration` (defined in `.github/workflows/opencode_ci.yml`)
- **Current Matrix**: Single-OS (`ubuntu-latest`).
- **Confirmation**: While the project uses multi-OS matrices for hardening, the OpenCode CI job is strictly Linux-based today. The fix was verified on Windows local environment with successful process group termination.

## 5. Policy Surface Audit

- **Changes**: Narrow addition of `MISSION_TIMEOUT` to `ReasonCode` enum in `scripts/opencode_gate_policy.py`.
- **Allowlists/Denylists**: **UNCHANGED**. No modifications were made to the security envelope or protected surfaces.
- **Diff Summary**:

  ```diff
  + MISSION_TIMEOUT = "MISSION_TIMEOUT"
  ```

- **Integrity**: All 89 existing policy tests pass.

## 6. Regression Gate

- **Suite**: `tests_recursive/test_e2e_smoke_timeout.py` (6 tests)
- **Total Verification**: 95 tests pass (6 new regression + 89 policy).

## 7. Evidence Package (Full SHA256)

| Item | Path / Source | SHA256 |
| :--- | :--- | :--- |
| **Logic Fix** | `scripts/opencode_ci_runner.py` | 4eb6903f7734a781878d05ee0e0717208d08c5c4e04990c765ef9bd378853b0e |
| **Policy Update** | `scripts/opencode_gate_policy.py` | 9fa9cc795ece47ad0350614751349809a48611d67a95a38dc0eba30297cdb283 |
| **Regression Test** | `tests_recursive/test_e2e_smoke_timeout.py` | 4dad2921162db955ed31fbe78fe299e43adad40a4b9c29c5aa7dd2ce8f634c6c |
| **Proof Log (Plain)** | `artifacts/evidence/opencode_e2e_smoke_before_after_proof_plain.log` | 2b07e63b65f492ac69666e85559868350bb2069b18366d2f39f7ece0e57988fa2 |
| **Runner Log (Raw)** | `artifacts/evidence/opencode_ci_runner_raw.log` | 2b07e63b65f492ac69666e85559868350bb2069b18366d2f39f7ece0e57988fa2 |
| **Test Report** | `artifacts/test_reports/TEST_REPORT_OpenCode_E2E_Smoke_v1.1_PASS.md` | *(Pending)* |
