# Handoff Pack: Remaining Phases Closure Review

## Metadata
- Reviewer target: Claude Code
- Branch: `main`
- Worktree: `/mnt/c/Users/cabra/Projects/lifeos`
- Base: `main` (`2a62d1c87771d5d06d5ed480da7cbec98b15c904`)
- HEAD: `2a62d1c87771d5d06d5ed480da7cbec98b15c904`
- Commit state: dirty worktree, local-only changes, not pushed
- Scope: Phase 8 closure work (`T-016`, `T-019`, `T-020`) plus initial Phase 9 groundwork (`certify ops`, lane manifest, ops readiness artifact contract)

## Requested Review Focus
Please review the local change set for correctness, fail-closed behavior, and closure honesty. The highest-sensitivity areas are:

1. COO control-plane closure correctness
   - `runtime/orchestration/coo/invoke.py`
   - `runtime/tests/orchestration/coo/test_invoke_receipts.py`
   - `config/agent_roles/coo.md`
   - `config/coo/prompt_canonical.md`
   - `config/tasks/backlog.yaml`
2. Ops-certification surface design
   - `runtime/cli.py`
   - `scripts/run_ops_certification.py`
   - `config/ops/lanes.yaml`
   - `runtime/tests/test_ops_certification.py`
3. Proof-harness compatibility regression fix
   - `scripts/certification_proof.py`

## Why This Handoff Exists

The local implementation was done directly against `main` after the remaining-phases planning pass. The goal was to:

- close `T-016` from existing evidence instead of reimplementing already-proven behavior
- close `T-019` by explicitly documenting the runtime prompt/schema authority split
- close `T-020` by making proposal-indentation recovery fail closed on unknown structure
- add the first code surface for Phase 9 work:
  - `lifeos certify ops --profile local|ci|live`
  - `config/ops/lanes.yaml`
  - `artifacts/status/ops_readiness.json` as an ephemeral readiness artifact
- preserve backward compatibility for the existing certification proof harness after the new work exposed a regression in `runtime/tests/test_certification_proof.py`

This pack is for local code review before any commit/push/closure steps.

## Change Summary

### Phase 8 closure work
- `runtime/orchestration/coo/invoke.py`
  - replaced the previous hard-coded indentation recovery list with schema-enumerated item-key handling for `task_id` and `proposal_id` list items
  - raises `ProposalNormalizationError` on malformed or unknown keys instead of silently widening recovery
  - records a failed invocation receipt when normalization fails
- `runtime/tests/orchestration/coo/test_invoke_receipts.py`
  - adds direct tests for task proposal recovery, operation proposal recovery, and unknown-key rejection
- `config/coo/prompt_canonical.md`
  - adds explicit machine-output authority language
- `config/agent_roles/coo.md`
  - adds explicit pointer to `config/coo/prompt_canonical.md` as runtime prompt authority
  - keeps `artifacts/coo/schemas.md` as the human-readable schema authority
- `config/tasks/backlog.yaml`
  - marks `T-016`, `T-019`, and `T-020` complete
  - records the `T-019` rescope in the task description/DoD instead of pretending the original wording was implemented literally

### Phase 9 groundwork
- `runtime/cli.py`
  - adds `lifeos certify ops --profile local|ci|live`
- `scripts/run_ops_certification.py`
  - new constrained-ops certification runner
  - validates lane manifest invariants
  - runs declared test suites per profile
  - writes `artifacts/status/ops_readiness.json`
  - enforces clean-worktree pre/post-run gates
- `config/ops/lanes.yaml`
  - declares the initial `workspace_mutation_v1` lane
  - allowlists `workspace.file.write`, `workspace.file.edit`, `lifeos.note.record`
  - keeps the lane `ratification_pending` and `explicit_human_approval`
- `.gitignore`
  - ignores `artifacts/status/ops_readiness.json` like the existing pipeline readiness artifacts
- `runtime/tests/test_ops_certification.py`
  - covers manifest loading, unknown-action rejection, approval/overlap fail-closed checks, and readiness artifact write path

### Compatibility fix
- `scripts/certification_proof.py`
  - restores `run_proof()` defaulting to `"local"`
  - reduces elapsed-time precision so the existing deterministic proof test remains stable under fixed-input mocks

## Files In Scope
- `.gitignore`
- `config/agent_roles/coo.md`
- `config/coo/prompt_canonical.md`
- `config/tasks/backlog.yaml`
- `config/ops/lanes.yaml`
- `runtime/cli.py`
- `runtime/orchestration/coo/invoke.py`
- `runtime/tests/orchestration/coo/test_invoke_receipts.py`
- `runtime/tests/test_ops_certification.py`
- `scripts/certification_proof.py`
- `scripts/run_ops_certification.py`

## Key Validation Results

### Focused validation
- `pytest runtime/tests/orchestration/coo/test_invoke_receipts.py -q`
  - PASS (`19 passed`)
- `python3 -m pytest runtime/tests/orchestration/ops/test_ops_lane.py runtime/tests/orchestration/coo/test_service.py runtime/tests/orchestration/coo/test_commands.py runtime/tests/test_ops_certification.py runtime/tests/test_certification_proof.py -q`
  - PASS (`76 passed`)
- `python3 scripts/workflow/quality_gate.py check --scope changed --json`
  - PASS with advisory-only missing-tool warnings (`ruff`, `mypy`, `biome`, `yamllint` unavailable locally)

### Runtime behavior check
- `python3 -m runtime.cli certify ops --profile local`
  - command executes, validates the lane manifest, runs the lane suites, and writes `ops_readiness.v1`
  - in the current dirty worktree it returns `red` only because the clean-worktree gate is intentionally blocking while these edits are uncommitted

### Broader suite status
- `pytest runtime/tests -q`
  - not carried to completion during this session
  - after the `scripts/certification_proof.py` compatibility fix, the run progressed past the earlier `runtime/tests/test_certification_proof.py` failure point and through the changed COO surfaces without additional failures observed during monitoring

## Current Review Questions

1. Is closing `T-016` from existing Gate 6 evidence plus current code/tests honest enough, or does it still need one more explicit evidence pointer or replay artifact in backlog/state?
2. Is the `T-019` rescope recorded clearly enough in `config/tasks/backlog.yaml`, or should the closure evidence point at a dedicated note explaining why prompt authority moved to `config/coo/prompt_canonical.md`?
3. Is the fail-closed behavior in `runtime/orchestration/coo/invoke.py` strict enough, especially around unknown root-level keys after a list item?
4. Does `scripts/run_ops_certification.py` feel like the right minimum Phase 9 foundation, or is there a design gap before this should be committed?
5. Is the proof-harness determinism fix in `scripts/certification_proof.py` acceptable, or do you see a better way to preserve deterministic tests without reducing elapsed-time precision?

## Suggested Claude Review Commands
- `git status --short`
- `git diff --stat`
- `git diff -- runtime/orchestration/coo/invoke.py runtime/tests/orchestration/coo/test_invoke_receipts.py`
- `git diff -- config/agent_roles/coo.md config/coo/prompt_canonical.md config/tasks/backlog.yaml`
- `git diff -- runtime/cli.py scripts/run_ops_certification.py config/ops/lanes.yaml runtime/tests/test_ops_certification.py`
- `python3 -m pytest runtime/tests/orchestration/coo/test_invoke_receipts.py -q`
- `python3 -m pytest runtime/tests/orchestration/ops/test_ops_lane.py runtime/tests/orchestration/coo/test_service.py runtime/tests/orchestration/coo/test_commands.py runtime/tests/test_ops_certification.py runtime/tests/test_certification_proof.py -q`
- `python3 -m runtime.cli certify ops --profile local`

## Notes
- No governance-protected paths under `docs/00_foundations/` or `docs/01_governance/` were modified.
- This is a local dirty-worktree review handoff, not a branch-pushed review handoff.
- `T-022` was intentionally left pending because the canonical default-branch GitHub proof run has not been executed from this environment.
