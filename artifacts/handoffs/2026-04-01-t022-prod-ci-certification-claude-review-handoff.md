# Handoff Pack: T-022 prod_ci Certification Claude Review

## Metadata
- Reviewer target: Claude Code
- Branch: `build/t-022-prod-ci-certification`
- Worktree: `/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification`
- Base: `main` (`a8a13218c7fd4aecca8a2aa83c7a5420b36f6f79`)
- HEAD: `866413a2e876236bc3f7cf2f5a37f3f3af03f113`
- Reviewed commits in scope:
  - `5ea04af3` `fix prod-ci certification harness and shell entrypoints`
  - `866413a2` `rewrite prod-ci certification harness`
- Commit state: committed, clean worktree
- Scope: Phase 7 / `T-022` implementation to promote CI certification to `prod_ci`

## Requested Review Focus
Please review the committed branch for correctness, contract alignment, and merge risk. Highest-sensitivity areas:

1. Policy-harness rewrite
   - [`scripts/run_certification_tests.py`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/scripts/run_certification_tests.py)
   - [`scripts/opencode_gate_policy.py`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/scripts/opencode_gate_policy.py)
2. CI skip classification and workflow safety
   - [`config/certification_profiles.yaml`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/config/certification_profiles.yaml)
   - [`prod_ci_proof.yml`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/.github/workflows/prod_ci_proof.yml)
3. Shell entrypoint mode changes
   - tracked `.sh` files promoted from `100644` to `100755`
   - especially `runtime/tools/openclaw_coo_update_protocol.sh` and `runtime/tools/openclaw_upgrade_module.sh`

## Change Summary

### Certification path changes
- [`scripts/run_certification_tests.py`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/scripts/run_certification_tests.py)
  - replaced the old `opencode serve` harness with a pure Python policy-layer harness
  - uses a detached temp worktree instead of a server lifecycle
  - directly exercises the `opencode_gate_policy` enforcement surface
  - restores the canonical report artifact at `artifacts/evidence/opencode_steward_certification/CERTIFICATION_REPORT_v1_4.json`
  - cleans up the detached temp worktree on success unless explicitly preserved
- [`scripts/opencode_gate_policy.py`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/scripts/opencode_gate_policy.py)
  - fixes `parse_git_status_z()` so local `git diff --name-status -z` records like `M\0path\0` parse correctly

### CI classification and workflow changes
- [`config/certification_profiles.yaml`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/config/certification_profiles.yaml)
  - adds `platform` skip patterns for `POSIX only`, `Windows only`, and `Waived: governance/mission-registry-v0.1`
- [`prod_ci_proof.yml`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/.github/workflows/prod_ci_proof.yml)
  - removes the duplicate standalone steward-runner triage step
  - uploads `artifacts/status/pipeline_readiness.json` and `artifacts/status/certification_proof.json` as ephemeral workflow artifacts

### Shell entrypoint portability fix
- The branch records execute bits for tracked shell entrypoints so direct `subprocess.run(["...sh", ...])` works in clean Linux checkouts.
- This specifically closes the failure mode seen in clean worktrees for:
  - [`runtime/tests/test_openclaw_coo_update_protocol_promotion.py`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/runtime/tests/test_openclaw_coo_update_protocol_promotion.py)
  - [`runtime/tests/test_openclaw_upgrade_module.py`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/runtime/tests/test_openclaw_upgrade_module.py)

## Files In Scope
- `.github/workflows/prod_ci_proof.yml`
- `config/certification_profiles.yaml`
- `scripts/opencode_gate_policy.py`
- `scripts/run_certification_tests.py`
- tracked `.sh` entrypoints changed to `100755`, including:
  - `runtime/tools/openclaw_coo_update_protocol.sh`
  - `runtime/tools/openclaw_upgrade_module.sh`
  - `runtime/tools/coo_worktree.sh`
  - `scripts/workflow/dispatch_codex.sh`

## Review Findings Already Fixed In This Pass
These issues were found and fixed before preparing this handoff:

1. Clean Linux worktrees failed direct shell-script execution with `PermissionError`.
   - Fix: recorded executable mode for tracked shell entrypoints in git.
2. The rewritten certification harness only wrote its report inside the detached temp worktree.
   - Fix: mirrored the report back to the canonical repo artifact path.
3. The rewritten harness leaked detached temp worktrees on successful runs.
   - Fix: success path now removes the temp worktree unless `--preserve-isolation` is set.
4. `parse_git_status_z()` mishandled simple `-z` local diff output.
   - Fix: added the missing path-parsing branch in [`scripts/opencode_gate_policy.py`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/scripts/opencode_gate_policy.py).

## Reviewer Questions
Please pay particular attention to these points:

1. Is the new policy-harness coverage in [`scripts/run_certification_tests.py`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/scripts/run_certification_tests.py) sufficient to preserve the intended security contract from the old server-based harness?
2. Is classifying the AT-12 waiver as `platform` in [`config/certification_profiles.yaml`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/config/certification_profiles.yaml) the right Phase 7 boundary, or do you see any contract drift there?
3. Are the broader `.sh` mode changes acceptable as a repository metadata fix, or should the scope be narrowed before merge?
4. Does [`prod_ci_proof.yml`](/mnt/c/users/cabra/projects/lifeos/.worktrees/t-022-prod-ci-certification/.github/workflows/prod_ci_proof.yml) have any merge-risk around artifact upload or proof-only commit behavior?

## Validation Evidence

### Targeted certification harness
- Command:
  - `python3 scripts/run_certification_tests.py`
- Result:
  - passed
  - canonical report written at `artifacts/evidence/opencode_steward_certification/CERTIFICATION_REPORT_v1_4.json`

### Targeted shell-script regression checks
- Commands:
  - `python3 -m pytest runtime/tests/test_openclaw_coo_update_protocol_promotion.py -q -o addopts=`
  - `python3 -m pytest runtime/tests/test_openclaw_upgrade_module.py -q -o addopts=`
- Result:
  - passed

### Full runtime suite
- Command:
  - `python3 -m pytest runtime/tests -q`
- Result:
  - `2832 passed, 6 skipped, 6 warnings`

### Scoped quality gate
- Command:
  - `python3 scripts/workflow/quality_gate.py check --scope changed --json`
- Result:
  - passed
  - advisory-only tool-unavailable results for `ruff`, `mypy`, `biome`, `yamllint`, and `shellcheck`

### CI certification
- Command:
  - `python3 -m runtime.cli certify pipeline --profile ci`
- Result:
  - `state: prod_ci`
  - zero leaks
  - readiness artifact written at `artifacts/status/pipeline_readiness.json`

## Suggested Claude Review Commands
- `git status --short`
- `git show --stat HEAD~2..HEAD`
- `git diff a8a13218c7fd4aecca8a2aa83c7a5420b36f6f79..HEAD -- scripts/run_certification_tests.py scripts/opencode_gate_policy.py`
- `git diff a8a13218c7fd4aecca8a2aa83c7a5420b36f6f79..HEAD -- config/certification_profiles.yaml .github/workflows/prod_ci_proof.yml`
- `git diff --summary a8a13218c7fd4aecca8a2aa83c7a5420b36f6f79..HEAD`
- `python3 scripts/run_certification_tests.py`
- `python3 -m pytest runtime/tests/test_openclaw_upgrade_module.py -q -o addopts=`
- `python3 -m pytest runtime/tests/test_openclaw_coo_update_protocol_promotion.py -q -o addopts=`
- `python3 -m runtime.cli certify pipeline --profile ci`

## Notes
- No protected governance paths were modified in this branch.
- The branch is in a reviewable committed state; this handoff adds context only.
- I did not mark `T-022` complete in backlog/state docs yet, because the remaining closure step is the explicit 3-run proof and workflow proof.
