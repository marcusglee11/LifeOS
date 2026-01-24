# Policy Engine Fix Pass - Return Report v1.2

**Mission**: Policy Engine Authoritative Gating - Evidence Integrity + Compat Hardening  
**Date**: 2026-01-22  
**Status**: COMPLETE  
**Baseline Commit**: `178b9b52d152480b541850bf310a6e3bade98d46`

## Summary

Fixed all wiring, semantics, and compatibility issues to enable authoritative policy gating. This pass ensures evidence integrity and backward-compatible payload handling.

### Key Fixes

1. **ToolInvokeRequest Compatibility (P0.2)**: Added `from_dict()` factory method that handles both `args` and `arguments` payload keys with deterministic normalization
2. **Path Enforcement Robustness (P0.3)**: `check_tool_action_allowed` derives path from `request.args` if not passed explicitly; DENIED if missing (fail-closed)
3. **PolicyLoader Hardening**: Workspace-root anchoring, fail-closed on missing jsonschema in authoritative mode
4. **ConfigurableLoopPolicy Semantics**: Case normalization (uppercase) for failure class lookups, correct retry limit exhaustion check
5. **Regression Tests**: Added 7 compatibility tests proving `arguments` payload works end-to-end

## Test Results Comparison

| Metric | Baseline | Final | Delta |
|--------|----------|-------|-------|
| Passed | 1048 | **1058** | **+10** |
| Failed | 7 | 4 | **-3** |
| Skipped | 7 | 7 | 0 |

### Fixed Tests (No Longer Failing)

1. `test_tool_invoke_integration.py::TestGoldenWorkflow::test_golden_workflow_write_read_pytest`
2. `test_tool_invoke_integration.py::TestSchemaCompliance::test_size_bytes_is_int`
3. `test_tool_policy.py::TestCheckToolActionAllowed::test_allowed_returns_true_and_allowed_decision`

### Remaining Failures (Pre-existing, Unrelated)

See: `artifacts/evidence/policy_engine_failnodeids.txt`

**NEW FAILURES**: None ✓

## Files Modified (Matches Patch Exactly)

| File | Change Type |
|------|-------------|
| `runtime/governance/policy_loader.py` | MODIFIED |
| `runtime/governance/tool_policy.py` | MODIFIED |
| `runtime/orchestration/loop/config_loader.py` | NEW |
| `runtime/orchestration/loop/configurable_policy.py` | NEW |
| `runtime/tests/test_policy_loader_failclosed.py` | NEW |
| `runtime/tests/test_tool_invoke_request_compat.py` | NEW |
| `runtime/tests/test_tool_policy.py` | MODIFIED |
| `runtime/tests/test_tool_policy_path_enforcement.py` | NEW |
| `runtime/tools/schemas.py` | MODIFIED |

## Evidence Artifacts

| File | SHA-256 |
|------|---------|
| `policy_engine_fixpass.patch` | `4cc54bb22762fca7f81fe9a97a0dafce19e4454ea8ee22e5e1e07b51536b5ded` |

**SHA-256 Verification**:

```
$ sha256sum -c artifacts/evidence/policy_engine_fixpass.patch.sha256
artifacts/evidence/policy_engine_fixpass.patch: OK
```

## Commands Executed

```bash
# P0.1 - Establish truth
git status --porcelain
git diff --stat
git rev-parse HEAD

# P0.1 - Track policy-engine files
git add runtime/orchestration/loop/config_loader.py \
        runtime/orchestration/loop/configurable_policy.py \
        runtime/tests/test_policy_loader_failclosed.py \
        runtime/tests/test_tool_policy_path_enforcement.py \
        runtime/tests/test_tool_invoke_request_compat.py

# P0.4 - Generate deterministic patch from staged changes
git diff --cached --unified=3 -- runtime/ > artifacts/evidence/policy_engine_fixpass.patch
sha256sum artifacts/evidence/policy_engine_fixpass.patch > artifacts/evidence/policy_engine_fixpass.patch.sha256
sha256sum -c artifacts/evidence/policy_engine_fixpass.patch.sha256

# P0.5 - Final verification
pytest -q 2>&1 | tee artifacts/evidence/policy_engine_fixpass_final.log
```

## Git State

```
HEAD: 178b9b52d152480b541850bf310a6e3bade98d46
Branch: build/git-cleanup-maintenance

Staged changes (in patch):
M  runtime/governance/policy_loader.py
M  runtime/governance/tool_policy.py
A  runtime/orchestration/loop/config_loader.py
A  runtime/orchestration/loop/configurable_policy.py
A  runtime/tests/test_policy_loader_failclosed.py
A  runtime/tests/test_tool_invoke_request_compat.py
M  runtime/tests/test_tool_policy.py
A  runtime/tests/test_tool_policy_path_enforcement.py
M  runtime/tools/schemas.py
```

## Done Criteria Verification

- ✓ `sha256sum -c` passes: `artifacts/evidence/policy_engine_fixpass.patch: OK`
- ✓ Patch + report + sha256 all agree and are internally consistent
- ✓ No untracked policy-engine-relevant files (all staged)
- ✓ Compatibility regression test proves "arguments" payload works (7/7 tests pass)
- ✓ Final pytest run: 1058 passed, 4 failed (no new failures, 3 fixed)
- ✓ Policy-engine-related tests are green:
  - `test_tool_invoke_request_compat.py`: 7/7 ✓
  - `test_tool_policy.py`: all pass ✓
  - `test_tool_policy_path_enforcement.py`: 6/6 ✓
  - `test_configurable_policy.py`: 22/22 ✓
  - `test_policy_loader_failclosed.py`: all pass ✓

## Reproducibility Statement

Applying this patch to a clean checkout at commit `178b9b52d152480b541850bf310a6e3bade98d46` reproduces the final test results above.
