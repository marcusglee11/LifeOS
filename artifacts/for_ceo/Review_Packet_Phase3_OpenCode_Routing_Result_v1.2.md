# Review Packet: Phase 3 OpenCode Routing Result (v1.2)

**Mission**: Implement Evidence-Grade OpenCode Routing for Steward Mission
**Date**: 2024-10-24
**Status**: VERIFIED (Phase 3 Targeted) / FULL SUITE: FAIL (24 Regressions)
**Author**: Antigravity

## 1. Summary

This packet provides proof of implementation and verification for Phase 3 OpenCode routing. The `StewardMission` now correctly routes in-envelope documentation changes to the `scripts/opencode_ci_runner.py` with strict safety, fail-closed behavior, and full evidence-grade logging.

> [!IMPORTANT]
> **Verification Status Statement**
>
> - **Phase 3 Routing Logic**: **VERIFIED** (49/49 specific tests PASSED).
> - **Repo Health**: **FAIL** (24 full-suite failures detected).
> The full-suite failures are primarily due to the disabled legacy script `scripts/steward_runner.py.DISABLED`, which causes regressions in `tests_recursive/` that depend on it. This is a known transition state.

## 2. Implementation Reference

- **Branch**: `gov/repoint-canon`
- **HEAD Commit**: `416e23cb216a88ed4eeee267b1d027b8193bac24`
- **Changed Files (Deterministic Inventory)**:
  1. `runtime/orchestration/engine.py` (Modified: Added logger)
  2. `runtime/orchestration/missions/steward.py` (Modified: Implementation of `_route_to_opencode`)
  3. `runtime/tests/test_missions_phase3.py` (Modified: Added routing test suite)
  4. `scripts/opencode_ci_runner.py` (Modified: Added `--task-file` support)

- **Full Diff Hash**: `ae8c68ecbb3c1d1e1523709aa055b6090e47e9da6994738c166c0b46be25229c` (SHA256 of `artifacts/evidence/Phase3_Complete_v1.2.diff`)

## 3. Verbatim Verification Outputs

### 3.1 Phase 3 Mission Tests (Targeted)

Command: `python -m pytest runtime/tests/test_missions_phase3.py -v`
Result: **49 PASSED**

```text
runtime/tests/test_missions_phase3.py::TestMissionType::test_all_types_defined PASSED
runtime/tests/test_missions_phase3.py::TestMissionType::test_string_enum PASSED
...
runtime/tests/test_missions_phase3.py::TestStewardRouting::test_steward_routes_success PASSED
runtime/tests/test_missions_phase3.py::TestStewardRouting::test_steward_routes_failure_exit_code PASSED
runtime/tests/test_missions_phase3.py::TestStewardRouting::test_steward_routes_timeout PASSED
...
======================== 49 passed, 1 warning in 1.62s ========================
```

### 3.2 Full Suite Verification

Command: `python -m pytest -v`
Result: **Exit Code 1 (24 failures)**

```text
FAILED tests_recursive/test_steward_runner.py::TestAT11TestScopeEnforcement::test_tests_argv_includes_paths - AssertionError: Should have log file
FAILED tests_recursive/test_steward_runner.py::TestZ88TestStewardRunner::test_steward_runner_execution - FileNotFoundError: [Errno 2] No such file or directory: 'scripts/steward_runner.py'
...
================= 24 failed, 790 passed, 5 skipped, 1 xfailed, 128 warnings =================
```

## 4. Runner Interface Truth

The `scripts/opencode_ci_runner.py` interface has been verified against source code:

- **Supports `--task-file`**: YES (Line 348: `parser.add_argument("--task-file", ...)`)
- **Supports `--task`**: YES (Line 347: `parser.add_argument("--task", ...)`)
- **Safety Checks**: Verified in code (Lines 359-391 enforce `artifacts/` containment, reject symlinks/traversal).

## 5. Artefact Inventory & Hashes

| Artefact | Path | FULL SHA256 Hash |
| :--- | :--- | :--- |
| Task JSON | `artifacts/steward_tasks/steward_task_v1.json` | `04d199604d22cbb7d814a2a8ea28f58677620fa2da8617873cc3095121a5a890` |
| Runner Stdout | `artifacts/logs/opencode_steward_stdout_v1.log` | `5acbd6a0b00508ba57e00ff81ef92d1f7e88b7c6cca56dfbdfa594b0e4551fad` |
| Runner Stderr | `artifacts/logs/opencode_steward_stderr_v1.log` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Change Diff | `artifacts/evidence/Phase3_Complete_v1.2.diff` | `ae8c68ecbb3c1d1e1523709aa055b6090e47e9da6994738c166c0b46be25229c` |
| Changed Files List | `artifacts/evidence/changed_files_v1.2.txt` | `04300e4762a784ea00277aa38a5c2b2c34a0981f0a2bff8d53fa386d7456bb8a` |

## 6. Meets DONE?

- [x] Functional routing to OpenCode runner? (YES)
- [x] Fail-closed on all errors? (YES)
- [x] Evidence-grade logs produced and hashed? (YES)
- [x] Protected roots and out-of-scope files blocked? (YES)
- [x] Task-file security validation implemented? (YES)
