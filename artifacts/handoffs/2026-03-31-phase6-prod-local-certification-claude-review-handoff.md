# Handoff Pack: Phase 6 prod_local Certification

## Metadata
- Reviewer target: Claude Code
- Branch: `build/phase6-prod-local-certificatio`
- Worktree: `/mnt/c/users/cabra/projects/lifeos/.worktrees/phase6-prod-local-certificatio`
- Base: `main` (`badff56b81ad7517b5dd1edcb0895e906662be18`)
- HEAD: `dcddfd0c39a022923f7af5771f4b1b2ab573562f`
- Reviewed commits in scope:
  - `7a96bcf3` `feat: complete local certification blockers`
  - `dcddfd0c` `fix: preserve changed-file fallback in bypass ledger`
- Commit state: committed, clean worktree
- Scope: Phase 6 / `T-021` implementation to promote local certification to `prod_local`

## Requested Review Focus
Please review the committed branch for correctness, regression risk, and any contract drift in the local certification path. Highest-sensitivity areas:

1. `runtime/orchestration/missions/autonomous_build_cycle.py`
   - review-rejection bypass integration
   - `evaluate_plan_bypass()` inputs built from live workspace diff
   - ledger persistence for `plan_bypass_info`
   - `changed_files` extraction and fallback behavior
2. Tests and certification classification
   - `runtime/tests/orchestration/missions/test_bypass_dogfood.py`
   - `runtime/tests/test_pipeline_certification.py`
   - `config/certification_profiles.yaml`
3. Determinism and local-readiness support changes
   - `scripts/generate_repo_map.py`
   - `runtime/tests/test_doc_hygiene.py`
   - `.gitignore`
   - `scripts/certification_proof.py`

## Change Summary

### Local certification blockers closed
- `scripts/generate_repo_map.py`
  - `is_tree_dirty()` now ignores untracked files via `git status --porcelain=v1 --untracked-files=no`
- `runtime/tests/test_doc_hygiene.py`
  - activated the markdownlint missing-binary regression and asserted exit code `127`
- `config/certification_profiles.yaml`
  - removed the two obsolete local `wip` skip entries
- `runtime/tests/test_pipeline_certification.py`
  - updated classification expectations to match the active tests

### Review-rejection bypass activation
- `runtime/orchestration/missions/autonomous_build_cycle.py`
  - imports `PROTECTED_PATHS` and `run_git_command`
  - computes `proposed_patch` from `git diff --numstat HEAD` and `git diff --summary HEAD`
  - calls `policy.evaluate_plan_bypass(...)` on review rejection
  - records bypass decisions in `AttemptRecord.plan_bypass_info`
  - carries approved bypass decisions onto the next successful attempt
  - records `changed_files` from review packet artifacts or packet file paths
- `runtime/tests/orchestration/missions/test_bypass_dogfood.py`
  - activated the bypass dogfood test
  - added regression coverage for `packet.files` fallback when `artifacts_produced` is empty

### Proof artifact support
- `.gitignore`
  - added `artifacts/status/pipeline_readiness.json`
  - added `artifacts/status/certification_proof.json`
- `scripts/certification_proof.py`
  - added to this worktree branch so the 3-run proof can execute locally without leaving the tree dirty

## Files In Scope
- `.gitignore`
- `config/certification_profiles.yaml`
- `runtime/orchestration/missions/autonomous_build_cycle.py`
- `runtime/tests/orchestration/missions/test_bypass_dogfood.py`
- `runtime/tests/test_doc_hygiene.py`
- `runtime/tests/test_pipeline_certification.py`
- `scripts/certification_proof.py`
- `scripts/generate_repo_map.py`

## Review Findings Already Fixed In This Pass
These issues were found and fixed before preparing this handoff:

1. Review-rejection bypass needed a concrete `proposed_patch` source.
   - Fix: `autonomous_build_cycle.py` now builds the bypass payload from live workspace diff stats (`git diff --numstat HEAD`, `git diff --summary HEAD`) before calling policy.
2. `changed_files` evidence could be lost when `artifacts_produced` existed but was an empty list.
   - Fix: `_changed_files_from_review_packet()` now falls back to `payload.packet.files`, with explicit regression coverage.

## Reviewer Questions
Please pay particular attention to these points:

1. Is using `git diff --numstat HEAD` and `git diff --summary HEAD` at review-rejection time the correct patch boundary for bypass policy, or is there still a latent mismatch with what the build step intended to change?
2. Is `has_suspicious_modes = bool(summary_output.strip())` too broad, given that `git diff --summary` can include benign rename summaries as well as mode changes?
3. Does carrying `pending_plan_bypass_info` only onto the next successful attempt preserve the ledger semantics you expect for multi-attempt loops?
4. Are there any local-certification edge cases left after removing the two `wip` skip classifications?
5. Is `.gitignore` the right place to absorb proof/readiness artifacts, or should that cleanliness policy live elsewhere?

## Validation Evidence

### Targeted tests
- Command:
  - `pytest runtime/tests/test_generate_repo_map.py -q -p no:cacheprovider`
  - `pytest runtime/tests/test_doc_hygiene.py -q -p no:cacheprovider`
  - `pytest runtime/tests/orchestration/missions/test_bypass_dogfood.py -q -p no:cacheprovider`
  - `pytest runtime/tests/test_pipeline_certification.py -q -p no:cacheprovider`
- Result:
  - passed

### Full runtime suite
- Command:
  - `pytest runtime/tests -q -p no:cacheprovider`
- Result:
  - `2830 passed, 6 skipped, 6 warnings`

### Scoped quality gate
- Command:
  - `python3 scripts/workflow/quality_gate.py check --scope changed --json`
- Result:
  - passed
  - advisory-only tool-unavailable warnings for `ruff`, `mypy`, `biome`, and `yamllint`

### Local certification
- Command:
  - `python3 -m runtime.cli certify pipeline --profile local`
- Result:
  - `state: prod_local`
  - zero blocking leaks
  - zero non-blocking leaks

### Proof run
- Command:
  - `python3 scripts/certification_proof.py`
- Result:
  - passed
  - `3` consecutive `prod_local` runs recorded

## Suggested Claude Review Commands
- `git status --short`
- `git show --stat HEAD~2..HEAD`
- `git diff badff56b81ad7517b5dd1edcb0895e906662be18..HEAD -- runtime/orchestration/missions/autonomous_build_cycle.py`
- `git diff badff56b81ad7517b5dd1edcb0895e906662be18..HEAD -- runtime/tests/orchestration/missions/test_bypass_dogfood.py`
- `git diff badff56b81ad7517b5dd1edcb0895e906662be18..HEAD -- config/certification_profiles.yaml runtime/tests/test_pipeline_certification.py`
- `pytest runtime/tests/orchestration/missions/test_bypass_dogfood.py -q -p no:cacheprovider`
- `pytest runtime/tests -q -p no:cacheprovider`
- `python3 -m runtime.cli certify pipeline --profile local`

## Notes
- No protected governance paths were modified in this branch.
- The branch is already in a reviewable committed state; this handoff adds context only.
- The readiness and proof artifacts are expected outputs and are now ignored so the proof harness can keep the worktree clean.
