# BUILD REPORT: OpenCode Sandbox Activation (Builder Envelope)

**Date**: 2026-01-12
**Status**: SUCCESS
**Task**: OpenCode Sandbox Activation - Builder Write Envelope (Phase 3)

## 1. Executive Summary

Successfully implemented the "Builder Mode" write envelope in `scripts/opencode_gate_policy.py`, enabling trusted Phase 3 code modification capabilities (`.py` in `runtime/`, `tests/`) while strictly preserving Phase 2 Doc-Steward protections.

- **Key Achievement**: Authorized "Builder" write access established under strict allowlist policy.
- **Security Check**: Enforced "Critical File" denylist blocking modifications to the gate itself, even in Builder Mode.
- **Unblocking**: Unstranded `OpenCode_First_Stewardship_Policy_v1.1.md` to `docs/01_governance/` to comply with mandate.

## 2. Artifacts & Changes

### Modified Safety Gates

- `scripts/opencode_gate_policy.py` (SHA256: `b066121d55290c2fae8c61ec1792851224bbfd6a962f42e5c47b04275559fa20`)
  - Added `MODE_STEWARD` (Default) and `MODE_BUILDER`.
  - Added `validate_operation(status, path, mode)`.
  - Defined `BUILDER_ALLOWLIST_ROOTS` (`runtime/`, `tests/`).
  - Defined `CRITICAL_ENFORCEMENT_FILES`.
- `scripts/opencode_ci_runner.py` (SHA256: `a5b177c544e9df4d9e96a95e804e29c09931998c1f4094344f6a5acf28c67f60`)
  - Added explicit `--mode` argument (trusted sourcing).
  - Delegated validation to `policy.validate_operation`.
  - Restored `detect_blocked_ops` for Steward Mode strictness.

### Verified Governance

- **Policy**: `docs/01_governance/OpenCode_First_Stewardship_Policy_v1.1.md` (Restored).

### Verification

- **New Tests**: `tests/test_opencode_gate_policy_builder.py` (SHA256: `d3867c350b9cd836e6884d75797b849c76d0cfd2af964a0b9eff35379f71220e`)
- **Regression Tests**: `tests_recursive/test_opencode_gate_policy.py` (Updated fixture, All 73 PASS).

## 3. Evidence of Verification

### Automated Test Results

- **Builder Envelope**: `PASS` (6 scenarios)
  - `artifacts/reports/captures/test_opencode_builder_PASS.txt` (SHA256: `f4bd496b4672a3b29f8fc10870dcdeeb4106d473b67ea9e929e325a7f0591b80`)
- **Steward Regression**: `PASS` (73 scenarios)
  - `artifacts/reports/captures/test_opencode_regression_PASS.txt` (SHA256: `85352164edaad71d69b7097c5863f31185daade9d241b09879a6ecdb9a20a4a0`)

## 4. Policy Compliance

- **P0.2 Trusted Mode**: `opencode_ci_runner.py` accepts `--mode` from the Orchestrator.
- **P0.4 Builder Allowlist**: Validated to allow `runtime/` and `tests/`.
- **P0.5 Denylists**: Validated to block `scripts/`, `docs/01_governance/`, and Critical Files (`opencode_gate_policy.py`).
- **Fail-Closed**: Logic defaults to Steward Mode if no mode specified. Unknown modes rejected by argparse choice constraint.

## 5. Next Steps

- Update `StewardMission` / `BuildMission` to invoke `opencode_ci_runner.py` with the appropriate `--mode`.
- Begin Phase 3 Autonomous Build Loop.
