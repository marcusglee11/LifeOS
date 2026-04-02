# Handoff Pack: T-022 prod_ci Proof Close Follow-Up

## Metadata
- Reviewer target: Claude Code
- Branch: `fix/t-022-proof-close-v2`
- Worktree: `/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-proof-close-v2`
- Base: `main` (`6ec61da3`)
- HEAD: `f096abc2447c0fbe78dcae0532a08a5994c2e7c3`
- Commit state: clean worktree, branch pushed to `origin/fix/t-022-proof-close-v2`
- Scope: follow-up fixes required to actually close `T-022` after the earlier squash merge left out proof-critical pieces

## Requested Review Focus
Please review the follow-up branch for correctness and merge safety. The highest-sensitivity areas are:

1. Repeat-run certification correctness
   - `scripts/run_certification_tests.py`
   - `scripts/opencode_gate_policy.py`
   - `config/certification_profiles.yaml`
2. CI proof workflow correctness
   - `.github/workflows/prod_ci_proof.yml`
3. Proof evidence / closure readiness
   - `artifacts/evidence/T_022_prod_ci_certification_proof.md`

## Why This Follow-Up Exists

`main` already contains squash merge `6ec61da3` for the original `T-022` branch, but several proof-critical follow-up changes were still missing from `main`:

- the `prod_ci` proof workflow still had the duplicate steward step and lacked ephemeral artifact upload
- `scripts/generate_repo_map.py` was missing the dirty-check retry fix used to stabilize proof runs
- `config/certification_profiles.yaml` was missing the `POSIX only`, `Windows only`, and AT-12 waiver classifications
- `scripts/run_certification_tests.py` was still the old `opencode serve` harness on this follow-up branch until fixed in-place
- `scripts/opencode_gate_policy.py` was missing the `parse_git_status_z()` fix needed by the direct policy harness

This branch closes those gaps and proves the result locally.

## Change Summary

### Proof follow-ups restored
- `.github/workflows/prod_ci_proof.yml`
  - removes duplicate standalone steward triage
  - uploads `artifacts/status/pipeline_readiness.json` and `artifacts/status/certification_proof.json`
- `scripts/generate_repo_map.py`
  - retries `git status --short` timeouts before failing closed
- `runtime/tests/test_generate_repo_map.py`
  - adds regression coverage for timeout retry and fail-closed git errors

### Classification and repeatability fixes
- `config/certification_profiles.yaml`
  - adds:
    - `POSIX only` → `platform`
    - `Windows only` → `platform`
    - `"Waived: governance/mission-registry-v0.1"` → `platform`
- `scripts/run_certification_tests.py`
  - replaces the old `opencode serve` server harness with the direct policy-layer certification harness
  - removes server lifecycle, API/model dependency, Windows `taskkill`, and temp clone complexity not needed for CI certification
- `scripts/opencode_gate_policy.py`
  - fixes `parse_git_status_z()` so plain `A/M/D` NUL-separated records without `\t` parse correctly

### Durable proof evidence
- `artifacts/evidence/T_022_prod_ci_certification_proof.md`
  - committed durable receipt for the successful local 3-run proof

## Files In Scope
- `.github/workflows/prod_ci_proof.yml`
- `config/certification_profiles.yaml`
- `runtime/tests/test_generate_repo_map.py`
- `scripts/generate_repo_map.py`
- `scripts/opencode_gate_policy.py`
- `scripts/run_certification_tests.py`
- `artifacts/evidence/T_022_prod_ci_certification_proof.md`

## Commits In Scope
- `0b34d7be` `fix t-022 proof follow-ups`
- `8f34e836` `fix t-022 skip classification drift`
- `0ed3d22d` `fix t-022 proof repeatability`
- `f096abc2` `docs: record T-022 prod_ci proof`

## Key Validation Results

### Targeted validation
- `python3 -m pytest runtime/tests/test_generate_repo_map.py -q -o addopts=`
  - PASS (`18 passed`)
- `python3 scripts/run_certification_tests.py`
  - PASS (`16` policy tests, all passing)
- `python3 scripts/workflow/quality_gate.py check --scope changed --json`
  - PASS with advisory-only missing-tool warnings (`ruff`, `mypy`, `biome`, `yamllint` unavailable locally)

### Full local certification
- `python3 -m runtime.cli certify pipeline --profile ci`
  - PASS
  - readiness state: `prod_ci`
  - leaks: `[]`

### 3-run proof
- `python3 scripts/certification_proof.py --profile ci --evidence-output artifacts/evidence/T_022_prod_ci_certification_proof.md`
  - PASS
  - `3` consecutive runs
  - all `prod_ci`
  - zero leaks on all runs

## Current Blocker

The remaining blocker is GitHub-side, not code-side.

- `gh workflow list` does **not** show `Prod CI Proof`
- `gh workflow run .github/workflows/prod_ci_proof.yml --ref fix/t-022-proof-close-v2` returns:
  - `HTTP 404: workflow ... not found on the default branch`

Interpretation: the canonical proof workflow still is not registered on the default branch, so the final GitHub proof cannot be dispatched until that is resolved.

Because of that, these closure updates were intentionally **not** done yet:
- `config/tasks/backlog.yaml`
- `docs/11_admin/LIFEOS_STATE.md`
- `docs/INDEX.md`
- `docs/LifeOS_Strategic_Corpus.md`

## Reviewer Questions

1. Does the restored policy-layer `scripts/run_certification_tests.py` look correct and sufficiently equivalent to the intended certification contract for `prod_ci`?
2. Is the `parse_git_status_z()` fix in `scripts/opencode_gate_policy.py` the right and complete correction for the direct diff-parse path?
3. Is the skip classification in `config/certification_profiles.yaml` now correct for the Phase 7 contract, especially the use of `platform` for the AT-12 waiver?
4. Does the updated `.github/workflows/prod_ci_proof.yml` look safe to use once it is present on the default branch?
5. Do you see any reason not to update backlog/state/docs immediately after the canonical GitHub proof becomes dispatchable and passes?

## Suggested Claude Review Commands
- `git status --short`
- `git log --oneline -n 8`
- `git diff 6ec61da3..HEAD --stat`
- `git diff 6ec61da3..HEAD -- scripts/run_certification_tests.py scripts/opencode_gate_policy.py`
- `git diff 6ec61da3..HEAD -- config/certification_profiles.yaml .github/workflows/prod_ci_proof.yml`
- `python3 scripts/run_certification_tests.py`
- `python3 -m runtime.cli certify pipeline --profile ci`
- `sed -n '1,220p' artifacts/evidence/T_022_prod_ci_certification_proof.md`

## Notes
- No governance-protected paths were modified in this branch.
- The branch is already pushed and clean.
- Local proof is complete; only the canonical GitHub workflow proof remains blocked by workflow registration on the default branch.
