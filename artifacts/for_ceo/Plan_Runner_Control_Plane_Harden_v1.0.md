---
packet_id: 5a7e8b9c-22d3-4e8f-8c7a-9d2e1b3c4d5e
packet_type: PLAN_ARTIFACT
version: 1.0
mission_name: Runner Control-Plane Hardening v3
author: Antigravity
status: PENDING_REVIEW
date: 2026-01-07
---

# Plan: Runner Control-Plane Hardening v3 (Single Lockfile + Safe Kill)

## Goal
Implement a single-run concurrency lock, an OS-agnostic kill control with PID reuse protection, and comprehensive TDD coverage for the OpenCode CI runner.

## User Review Required
> [!IMPORTANT]
> - **Atomic Lock**: Uses `os.open(O_CREAT | O_EXCL)` for fail-closed concurrency.
> - **PID Identity Protection**: Matches `runner_token` substring in process command line. Rejects kill if mismatch detected.
> - **Windows Support**: Uses `taskkill /PID <pid> /T /F` for process-tree termination.
> - **CI Extension**: Matrix extended to include `windows-latest` for cross-platform validation.

## Proposed Changes

### 1. Repository Infrastructure
#### [MODIFY] [.gitignore](file:///c:/Users/cabra/Projects/LifeOS/.gitignore)
- Add `.runtime/` to untracked directory list.

### 2. Core Hardening Logic
#### [NEW] [runner_lock.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/runner_lock.py)
Small, focused module for lock management and OS-agnostic kill signals.
- **Lock Data**: `{pid, runner_token: "opencode_ci_runner", repo_marker: "<repo_root>"}`.
- **Identity Matching**: Substring search in command line (Linux `/proc`, macOS `ps`, Windows PowerShell).

### 3. CI Runner Integration
#### [MODIFY] [opencode_ci_runner.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/opencode_ci_runner.py)
- **Fast-Path Ops**: Add `--kill`, `--status`, `--force`.
- **Concurrency Guard**: Call `runner_lock.acquire()` before starting.
- **Cleanup**: Ensure `runner_lock.release()` in `finally` block of `main()`.

### 4. Test Suite
#### [NEW] [test_runner_hardening.py](file:///c:/Users/cabra/Projects/LifeOS/tests_recursive/test_runner_hardening.py)
- **Unit**: Lock exclusivity, cleanup on exit, identity match/mismatch rules.
- **Integration**: Real subprocess heartbeat test (spawn → verify → kill → verify).

### 5. CI Configuration
#### [MODIFY] [opencode_ci.yml](file:///c:/Users/cabra/Projects/LifeOS/.github/workflows/opencode_ci.yml)
- Add `windows-latest` to the test matrix.

## Verification Plan

### Automated Tests
```bash
pytest tests_recursive/test_runner_hardening.py -v
```

### Manual Verification
1. Start runner, verify `.runtime/RUN.lock` exists.
2. Try second run; verify rejection with PID info.
3. Run `python scripts/opencode_ci_runner.py --kill` and verify cleanup.

## Boundaries
- No changes to gate policy logic.
- No new external dependencies (Standard Library + OS commands only).
- Non-zero exit codes for all safety-failure scenarios.
