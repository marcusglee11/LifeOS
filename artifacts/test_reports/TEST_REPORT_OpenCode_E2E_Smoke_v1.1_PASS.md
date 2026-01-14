# Test Report: OpenCode E2E Smoke Reliability (v1.1)

**Date**: 2026-01-11
**Status**: PASS
**Target**: OpenCode CI Runner Reliability Fixes (Timeout)

## Summary

The OpenCode E2E smoke reliability mission successfully addressed the timeout/hang issue. Canonical E2E smoke run passed with deterministic watchdog enforcement. No truncation or elisions present in evidence.

## Canonical Proof Run (Mechanically Captured)

- **Command**: `python scripts/opencode_ci_runner.py --task-file artifacts/steward_tasks/steward_task_v2.json --mission-timeout 150`
- **Start Time**: 2026-01-11 01:42:54.787471
- **End Time**: 2026-01-11 01:44:58.273623
- **Wall Time**: 123.49s
- **Status**: **PASS** (Mission Success)
- **Log**: `artifacts/evidence/opencode_e2e_smoke_before_after_proof_plain.log`

## Test Results

| Test ID | Name | Outcome | Notes |
| :--- | :--- | :--- | :--- |
| **E2E-SMOKE** | Canonical proof run | **PASS** | Verified on Windows local machine |
| **TH-001/004**| Watchdog Suite | **PASS** | 4 tests covering timeout/propagation |
| **PG-001** | Process Group Cleanup | **PASS** | Validated cross-platform termination |
| **POL-REG** | Policy Regression | **PASS** | 89 existing tests pass |

## Verification Command

```bash
pytest tests_recursive/test_e2e_smoke_timeout.py -v
```
