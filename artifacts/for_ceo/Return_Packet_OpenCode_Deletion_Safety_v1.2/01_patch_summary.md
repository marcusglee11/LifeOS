# Patch Summary: OpenCode Deletion Safety v1.2

**Resolution:** P0.2 Safety Invariant Implementation + P0.1 Strict Containment
**Date:** 2026-01-15

## 1. Safety Guard Implementation (`runtime.safety.path_guard`)

Implemented a reusable `PathGuard` class enforcing the following invariants for any destructive operation:

1. **Absolute Real Path:** Target must resolve to a real, absolute path.
2. **Strict Descendant:** Target must be strictly within a recognized sandbox root.
   - **v1.1 Update:** Replaced string prefix check with `os.path.commonpath` to prevent prefix collisions (e.g. `/tmp/foo` vs `/tmp/foobar`).
3. **Marker Presence:** The target or its parent (up to sandbox root) must contain `.lifeos_sandbox_marker`.
4. **Repo/System Protection:** Target must NOT be the repository root, filesystem root, or home directory.

## 2. Script Hardening (`scripts/opencode_ci_runner.py` & `runtime/agents/opencode_client.py`)

- **Injected PathGuard:** Wrapped `shutil.rmtree` in `cleanup_isolated_config` (CI runner) and `_cleanup_config` (Client) with `PathGuard.verify_safe_for_destruction`.
- **Sandbox Marking:** Updated creation methods to apply `PathGuard.create_sandbox` (creating `.lifeos_sandbox_marker`).
- **Context Awareness:** Updated callsites to pass explicit `repo_root` to prevent ambiguity.
- **Removed Aggressive Reset:** Commented out `git reset --hard HEAD` calls in `opencode_ci_runner.py`.

## 3. Governance Layer Analysis

- **`runtime/orchestration/operations.py`:** Confirmed `COMPENSATION_COMMAND_WHITELIST` (including `git clean -fd`) is declarative only.
- **No Active Execution:** Grep search of orchestration layer found no active execution of compensation commands. The whitelist is used for validation of compensation receipts, not for executing destructive operations.
- **Future Proofing:** If compensation execution is implemented in the future, it should integrate with `PathGuard` to enforce sandbox constraints.

## 4. Validation

- **Unit Tests:** `runtime/tests/test_opencode_safety.py` verifies all PathGuard invariants including the new prefix collision case (7 tests, all passing).
- **Smoke Test:** `scripts/smoke_opencode_safety.py` provides runtime verification of blocked vs. allowed scenarios (all cases passed).
- **Repo-Policy Test:** Executed `python -m pytest runtime/tests/test_opencode_safety.py -v` as the canonical safety test suite.
