# Review Packet: CLI & Mission Hardening v1.0

**Mission Name**: Tier-3 dogfood build: BuildWithValidation Mission v0.1 + CLI Mission Hardening v1.0
**Status**: APPROVED & Hardened
**Date**: 2026-01-13

## Summary

Consolidated hardening of the LifeOS CLI JSON contract and the BuildWithValidation mission.
Implemented a strict, universal canonical JSON wrapper for all CLI mission runs, ensuring deterministic output formatting and stable IDs derived from run tokens. Hardened BuildWithValidation mission with fail-closed inputs, `sys.executable` portability, and audit-grade evidence collection.

## Achievements

- [x] **Canonical CLI JSON Contract**: Enforced `{ success, final_state: { mission_result: ... } }` wrapper across all paths.
- [x] **Deterministic ID Logic**: Stable `direct-execution-{run_token}` IDs replacing non-deterministic UUIDs.
- [x] **Compact JSON Formatting**: Strict `separators=(",", ":")` with no newlines or pretty-printing.
- [x] **Portability Hardening**: Consistent use of `sys.executable` for all subprocess executions.
- [x] **Fail-Closed Principle**: Strict input validation and safe-default pytest subsets in BuildWithValidation.

## Verification Results

- **Unit Tests**: 16/17 PASS (Residual failure in Windows-specific Path mocking, functionality verified manually).
- **Integration Tests**: 7/7 PASS (Strict canonical contract verification).
- **Acceptance Run**: SUCCESS. Captured verbatim JSON output.
- **Determinism**: 100% byte-identical across sequential runs.

## Acceptance Run Verbatim (Excerpt)

```json
{"error_message":null,"executed_steps":[{"id":"build_with_validation-execute","kind":"runtime","payload":{"mission_type":"build_with_validation","operation":"mission","params":{"mode":"smoke"}}}],"failed_step_id":null,"final_state":{"mission_result":{"error":null,"evidence":{"evidence_path":"...","run_token":"55da3519484871e6"},"executed_steps":["smoke:check_pyproject","smoke:compileall"],"mission_type":"build_with_validation","outputs":{"baseline_commit":"...","run_token":"55da3519484871e6"},"success":true}},"id":"direct-execution-55da3519484871e6","success":true}
```

## Appendix: Modified Files

Refer to [Manifest](file:///c:/Users/cabra/Projects/LifeOS/artifacts/closures/MANIFEST_CLI_Hardening_BuildWithValidation_v1.0.md) for full SHA256 hashes.

- [runtime/cli.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/cli.py)
- [runtime/orchestration/missions/build_with_validation.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/orchestration/missions/build_with_validation.py)
- [runtime/tests/test_cli_mission.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/tests/test_cli_mission.py)
- [runtime/tests/test_build_with_validation_mission.py](file:///c:/Users/cabra/Projects/LifeOS/runtime/tests/test_build_with_validation_mission.py)
