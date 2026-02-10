# Validation Surface Map — v2.1a P0

## Mission / Build Entrypoints

- `runtime/cli.py`: `cmd_mission_run()`
  - CLI mission entrypoint (`lifeos mission run ...`), currently dispatches into registry/engine and direct mission fallback.
- `runtime/orchestration/registry.py`: `run_mission()`
  - Canonical mission dispatch API for orchestration callers.
- `runtime/orchestration/engine.py`: `Orchestrator._execute_mission()`
  - Runtime mission execution boundary where mission types are resolved and executed.
- `runtime/orchestration/missions/build_with_validation.py`: `BuildWithValidationMission.run()`
  - Existing mission-local validation/evidence writer path.

## Acceptance / Gate-Like Paths (Existing)

- `runtime/orchestration/run_controller.py`: `mission_startup_sequence()`
  - Existing startup checks (kill switch, lock, repo clean, canon spine), but not token-based acceptance.
- `scripts/steward_runner.py`: `run_preflight()`, `run_validators()`, `run_postflight()`
  - Existing script-level pre/post runner with validator stage.
- `scripts/claude_session_complete.py`: `main()`
  - Existing multi-gate script orchestrator (review packet/doc gates), not autonomous build acceptance token flow.

## Validator / Capsule-Adjacent Clones

- `runtime/orchestration/validation.py`
  - Schema gate helper (`gate_check`) for payload/schema checks.
- `runtime/validator/anti_failure_validator.py`
  - Workflow validator package path (separate concern; potential naming collision risk with new validation suite).
- `runtime/workflows/validator.py`
  - Another workflow validation surface, not gate-token acceptance flow.
- `scripts/packaging/validate_return_packet_preflight.py`
  - Packet validation script with manifest checks (`08_evidence_manifest.sha256`).

## Recommended Integration Chokepoint (P0)

- Primary chokepoint: `runtime/orchestration/orchestrator.py:ValidationOrchestrator.run`
  - Trusted owner of retries, workspace lock, and job spec generation.
  - Calls trusted gate runner and acceptor; agent runner remains untrusted and single-shot.
- Gate boundary: `runtime/validation/gate_runner.py:GateRunner.run_preflight` and `runtime/validation/gate_runner.py:GateRunner.run_postflight`
  - Single emission boundary for deterministic `validator_report.json` failures and `acceptance_token.json` success.
- Acceptance boundary: `runtime/validation/acceptor.py:accept`
  - Non-bypassable token verification path; computes `acceptance_token_sha256` at read time.

## Notes

- Existing mission stack remains intact; v2.1a P0 adds a trusted validation pipeline adjacent to it.
- Worktree cleanliness and evidence root ignore proof are enforced against the active worktree root, not main tree state.
