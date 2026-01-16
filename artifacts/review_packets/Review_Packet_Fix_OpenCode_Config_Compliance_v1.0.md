# Review Packet: Fix OpenCode Config Compliance v1.0

**Mission**: Fix OpenCode Runner Configuration Compliance
**Date**: 2026-01-13
**Status**: APPROVED

## Summary

Fixed a critical issue where `scripts/opencode_ci_runner.py` (and related utilities) ignored the project's canonical model configuration (`config/models.yaml`) and hardcoded a fallback to `minimax-m2.1-free`.

**Refined Fix (v1.1)**: Improved `OpenCodeClient` to be provider-aware when loading keys. It now correctly parses `.env` for `ZEN_STEWARD_KEY` and `OPENROUTER_STEWARD_KEY`, ensuring that Direct Zen REST calls use the correct Zen key even if an OpenRouter key is also present.

## Issue Catalogue

| Issue | Description | Status |
|-------|-------------|--------|
| **Hardcoded Default** | `opencode_ci_runner.py` hardcoded `DEFAULT_MODEL = "minimax-m2.1-free"` | FIXED |
| **Missing Logs** | The hardcoded path bypassed `OpenCodeClient` logging; new runner didn't log | FIXED |
| **Multi-Provider Key Conflict** | `OpenCodeClient` used one key for all providers; broke Zen calls | FIXED |

## Acceptance Criteria

- [x] `opencode_ci_runner.py` imports `runtime.agents.models`
- [x] `verify_opencode_connectivity.py` reflects configured model (`minimax/minimax-m2.1`)
- [x] Zen connectivity proven via `Model used: ZEN:MiniMax-M2.1` in logs.
- [x] `.env` keys retrieved correctly by `OpenCodeClient`.

## Changes

### Modified Files

- `scripts/opencode_ci_runner.py`
- `scripts/verify_opencode_connectivity.py`
- `scripts/opencode_performance_tests.py`
- `runtime/agents/opencode_client.py`
- `runtime/agents/models.py`
- `config/models.yaml`

### New Files

- `runtime/tests/verify_runner_config.py` (Regression test)

## Verification

- **Test**: `python runtime/tests/verify_runner_config.py` PASSED
- **E2E**: `python scripts/verify_opencode_connectivity.py` PASSED (Confirmed `Model used: ZEN:MiniMax-M2.1`)
- **Trace**: Verified Correctness with debug logs: `DEBUG: Using Zen key starting with: sk-NdFDtwV...` (confirming correct key from .env used).
- **Comprehensive Multi-Role Test**: `python runtime/tests/test_multi_role_keys.py` PASSED ✓
  - Validated isolate key loading logic for all 4 roles.
- **True E2E Verification**: `python scripts/verify_all_roles_execution.py` **PASSED ✓**
  - **Proven Outcome**: Validated Actual Execution for all 4 roles (Steward, Builder, Designer, Reviewer).
  - **Primary Call**: Confirmed success calling Zen/Minimax (Primary) with Zen Key.
  - **Fallback Call**: Confirmed success calling Grok (OpenRouter Fallback) via **Dynamic Key Swapping**.
  - **Trace Evidence**:

    ```text
    TESTING ROLE: STEWARD
    ✓ Initialized with key: sk-NdFDtwV... (Provider check: Zen)
    [1/2] Testing Primary Call (Zen)... ✓ SUCCESS
    [2/2] Testing Fallback Fallback (OpenRouter)... 
      [TRACE] SWAPPED to OpenRouter Key (sk-or-v1-5...)
      [TRACE] Injecting OPENROUTER_API_KEY...
    ✓ SUCCESS
    ```

## Appendix: Flattened Code

### [scripts/opencode_ci_runner.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/opencode_ci_runner.py)

See file content in repo.

### [scripts/verify_opencode_connectivity.py](file:///c:/Users/cabra/Projects/LifeOS/scripts/verify_opencode_connectivity.py)

See file content in repo.

### [runtime/tests/verify_runner_config.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/tests/verify_runner_config.py)

See file content in repo.
