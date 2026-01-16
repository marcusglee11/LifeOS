# Root Cause Analysis: OpenCode Aggressive Cleanup

**Incident:** "Aggressive git clean" / Unsafe deletion risk in OpenCode context.
**Date:** 2026-01-15
**Status:** RESOLVED

## 1. Analysis

Investigation of the `runtime` and `scripts` directories identified two primary vectors for unsafe deletion:

### A. CI Runner Repo Reset (`scripts/opencode_ci_runner.py`)

- **Mechanism:** The script contained fallback logic that executed `git reset --hard HEAD` upon detecting envelope violations, diff errors, or symlink insertions.
- **Risk:** While standard for a CI environment (to ensure a clean slate), when run in a local development environment (supported via `--mode`), this command blindly wipes all uncommitted user changes in the repository. This matches the "aggressive cleanup" symptom.
- **Evidence:** Lines 391, 408, 420 in original `scripts/opencode_ci_runner.py`.

### B. Unverified Sandbox Cleanup (`cleanup_isolated_config`)

- **Mechanism:** `scripts/opencode_ci_runner.py` used `shutil.rmtree(config_dir)` to clean up temporary configuration directories.
- **Risk:** The `config_dir` path was not strictly validated against a "sandbox" invariant. If path resolution failed or an erroneous path was passed, `rmtree` could destroy non-sandbox directories.
- **Evidence:** `shutil.rmtree` usage without guard in `cleanup_isolated_config`.

### C. Operation Governance Gap (`runtime/orchestration/operations.py`)

- **Mechanism:** `COMPENSATION_COMMAND_WHITELIST` includes `git clean -fd`.
- **Risk Assessment:** While whitelisting is a governance step, analysis shows this whitelist is declarative only (used for validation, not execution). No active execution pathway for compensation commands was found in the orchestration layer. The compensation mechanism stores commands in receipts but does not execute them automatically.
- **Conclusion:** This represents a potential future risk if compensation execution is implemented, but is not an active threat vector in the current codebase.

## 2. Conclusion

The root cause was the lack of a centralized, reusable safety guard for destructive operations, leading to ad-hoc and potentially unsafe cleanup logic in `opencode_ci_runner.py`. The primary risk vectors were the unguarded `git reset --hard` commands and `shutil.rmtree` calls in the CI runner.
