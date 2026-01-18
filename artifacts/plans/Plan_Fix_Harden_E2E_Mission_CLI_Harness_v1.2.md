# Plan: Fix Harden E2E Mission CLI Harness v1.2

**Mission:** Harden E2E Mission CLI Harness to be truly fail-closed and proof-based.
**Version:** 1.2
**Owner:** Antigravity

## Goal

Implement strict fail-closed proofing, eliminate guessed negative/determinism behavior, ensure pytest reflects gates, and guarantee CI robustness.

## Proposed Changes

### 1. Harness Logic (`scripts/e2e/run_mission_cli_e2e.py`)

- **P0.1: Repo-Root Anchoring**: Force `cwd=repo_root` in all subprocess calls.
- **P0.3: Prove-or-Skip Negative Case**: Extract concrete failing invocation from `test_cli_mission.py`. Skip if unproven or ambiguous.
- **P0.4: Prove-or-Skip Determinism**: Extract `VOLATILE_FIELDS` from repo artifacts. Skip if missing or unparseable.
- **P0.5: Prove-or-Block Wrapper Authority**: Validate only fields explicitly asserted in `test_cli_mission.py`. Block if authority is missing.
- **P0.8: Coherent Wrapper Errors**: Ensure `wrapper_validation.ok` is false with explicit errors if JSON parse fails.
- **P0.9: Negative Source Metadata**: Record the exact proof locator in `E2E-3.meta.json`.
- **P0.10: Full Evidence Hashing**: Explicitly include `summary.json` and `search_log.txt` in the evidence hash inventory.

### 2. Test Logic (`runtime/tests/test_e2e_mission_cli.py`)

- **P0.2: Entrypoint Blessing Gate**: Assert `lifeos` usage if in path; else verify `python-m` blessing or expect `BLOCKED`.

## Verification Plan

- **Automated**: `pytest runtime/tests/test_e2e_mission_cli.py -v`
- **Manual**: Verify `summary.json` for proof-based skips and evidence hashing.
