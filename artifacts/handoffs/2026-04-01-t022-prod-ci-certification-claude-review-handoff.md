# Handoff Pack: Phase 7 prod_ci Engineering Certification

## Metadata
- Reviewer target: Claude Code
- Branch: `build/t-022-prod-ci-certification`
- Worktree: `/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification`
- Base: `main` (`728e49b33a73114b15169c2fc6d117071450f814`)
- HEAD: `728e49b33a73114b15169c2fc6d117071450f814`
- Commit state: uncommitted changes in worktree
- Scope: Phase 7 / `T-022` implementation to promote CI certification to `prod_ci`

## Requested Review Focus
Please review the in-place worktree changes for correctness, contract alignment, and CI workflow safety. Highest-sensitivity areas:

1. CI certification mechanics
   - `scripts/run_certification.py`
   - `scripts/certification_proof.py`
   - `config/certification_profiles.yaml`
   - `.github/workflows/prod_ci_proof.yml`
2. Test replacement and platform coverage
   - `runtime/tests/test_demo_approval_determinism.py`
   - `runtime/tests/test_sandbox_remediation.py`
   - `runtime/tests/test_pipeline_certification.py`
3. CI classification / ignore consistency
   - `pyproject.toml`
   - `config/certification_profiles.yaml`

## Change Summary

### Certification path updates
- `scripts/run_certification.py`
  - adds a post-run cleanliness check and records a blocking `worktree_cleanliness_post_run` leak if the repo is dirty after profile execution
- `scripts/certification_proof.py`
  - now supports `--profile local|ci`
  - keeps writing transient JSON to `artifacts/status/certification_proof.json`
  - can also write Markdown proof evidence via `--evidence-output`
  - records per-run elapsed time, pytest summary, and leak count in the proof payload

### CI-classified test fixes
- `runtime/tests/test_sandbox_remediation.py`
  - replaces the old same-device hardlink test with explicit POSIX-fail and Windows-tolerate cases
- `runtime/tests/test_demo_approval_determinism.py`
  - removes the dead `python -m coo.cli run-approval-demo` path
  - replaces it with a deterministic `CEOQueue` round-trip over the real SQLite queue + JSON invocation receipt path
  - freezes timestamp generation by monkeypatching `runtime.orchestration.ceo_queue._utc_now`
- `runtime/tests/test_pipeline_certification.py`
  - adds coverage for the new WSL skip classification pattern

### CI metadata and workflow
- `config/certification_profiles.yaml`
  - adds a `platform` skip-reason pattern for `WSL git worktree operations too slow for full suite`
  - updates suite reasons for the repaired CI-classified tests
- `pyproject.toml`
  - updates inline ignore comments to match the new CI-classified intent
- `.github/workflows/prod_ci_proof.yml`
  - adds a dedicated manual-dispatch proof workflow on `ubuntu-latest`
  - runs steward triage, baseline CI certification, proof generation, and auto-commits only the Markdown proof artifact

## Files In Scope
- `.github/workflows/prod_ci_proof.yml`
- `config/certification_profiles.yaml`
- `pyproject.toml`
- `runtime/tests/test_demo_approval_determinism.py`
- `runtime/tests/test_pipeline_certification.py`
- `runtime/tests/test_sandbox_remediation.py`
- `scripts/certification_proof.py`
- `scripts/run_certification.py`

## Review Findings Already Fixed In This Pass
These issues were found and fixed before preparing this handoff:

1. Certification proof CLI was missing `argparse` import after adding the new flags.
   - Fix: added the import and verified `python3 scripts/certification_proof.py --help`
2. CI classification metadata still described the repaired tests as old failing/dead cases.
   - Fix: updated `config/certification_profiles.yaml` and `pyproject.toml` comments to reflect the new test intent

## Reviewer Questions
Please pay particular attention to these points:

1. Is the new `CEOQueue` determinism test scoped at the right persistence boundary, or is there a better current-path artifact than SQLite row + `artifacts/receipts/<run_id>/index.json` byte equality?
2. Is the unconditional post-run cleanliness leak in `scripts/run_certification.py` the right invariant, even though some CI-classified suites may intentionally exercise temp worktrees and venv setup?
3. Does `scripts/certification_proof.py` now expose enough information in Markdown proof form for Phase 7 review, or is any important CI context still missing?
4. Is the new `prod_ci_proof.yml` workflow safe to auto-commit with `[skip ci]`, or does it need one more guard before use on `main`?
5. Should `test_isolated_smoke_test.py` remain unchanged for this phase, given that it still requires a clean worktree and networked environment to be meaningful?

## Validation Evidence

### Targeted tests
- Commands:
  - `pytest runtime/tests/test_pipeline_certification.py -q -o addopts=`
  - `pytest runtime/tests/test_sandbox_remediation.py -q -o addopts=`
  - `pytest runtime/tests/test_demo_approval_determinism.py -q -o addopts=`
  - `pytest runtime/tests/test_ceo_queue.py -q -o addopts=`
- Result:
  - passed

### Steward triage in this WSL worktree
- Command:
  - `pytest tests_recursive/test_steward_runner.py -q -o addopts= -ra`
- Result:
  - `27 skipped`
  - all skips carried the expected `WSL git worktree operations too slow for full suite (W0-T05)` reason

### Proof CLI surface
- Command:
  - `python3 scripts/certification_proof.py --help`
- Result:
  - passed

### Smoke-test caveat
- Command:
  - `pytest runtime/tests/test_isolated_smoke_test.py -q -o addopts=`
- Result:
  - fails in the current worktree because the test asserts a completely clean repo and this review worktree contains uncommitted T-022 changes
  - failure is not evidence of a smoke-path regression

### Not run in this session
- `python3 -m runtime.cli certify pipeline --profile ci`
- `python3 scripts/certification_proof.py --profile ci --evidence-output artifacts/evidence/T_022_prod_ci_certification_proof.md`
- `pytest runtime/tests -q`
- `python3 scripts/workflow/quality_gate.py check --scope changed --json`

These were not run here because the current session used a read-only command sandbox for command execution, and the full certification/proof path writes transient repo artifacts.

## Suggested Claude Review Commands
- `git status --short`
- `git diff --stat`
- `git diff -- scripts/certification_proof.py scripts/run_certification.py`
- `git diff -- runtime/tests/test_demo_approval_determinism.py runtime/tests/test_sandbox_remediation.py runtime/tests/test_pipeline_certification.py`
- `git diff -- config/certification_profiles.yaml pyproject.toml .github/workflows/prod_ci_proof.yml`
- `pytest runtime/tests/test_pipeline_certification.py -q -o addopts=`
- `pytest runtime/tests/test_demo_approval_determinism.py -q -o addopts=`
- `pytest runtime/tests/test_sandbox_remediation.py -q -o addopts=`
- `pytest runtime/tests/test_ceo_queue.py -q -o addopts=`

## Notes
- No protected governance paths were modified in this worktree.
- The worktree is intentionally left uncommitted so review can happen before any landing/cleanup step.
- The new proof workflow is manual-dispatch only; it does not change `ci.yml`.
