# Handoff Pack: T-022 Canonical Closure Blockers

## Metadata

- Branch: `fix/phase7-prod-ci-closure`
- Base: `main` (`215e0d28`)
- Scope: Phase 7 `prod_ci` closure verification and canon truth-sync

## Verified Local State

- `pytest runtime/tests -q`
  - PASS (`2903 passed`, `6 skipped`)
- `python3 scripts/run_certification_tests.py`
  - PASS (`16/16`)
- `python3 -m runtime.cli certify pipeline --profile ci`
  - PASS once from a clean worktree
  - readiness state: `prod_ci`
  - leaks: `[]`

## Blocking Findings

### 1. Default-branch GitHub proof cannot be dispatched yet

- `gh workflow run .github/workflows/prod_ci_proof.yml --ref main`
  - FAIL: `HTTP 404: workflow .github/workflows/prod_ci_proof.yml not found on the default branch`
- After `git fetch origin main`, local divergence is:
  - `origin/main...main` = `0 117`
- Interpretation:
  - the local repo contains `.github/workflows/prod_ci_proof.yml`
  - the remote default branch does not yet contain that workflow, so canonical GitHub proof cannot run from this environment

### 2. Repeat-run proof is not closure-clean on current branch state

- `python3 scripts/certification_proof.py --profile ci --evidence-output artifacts/evidence/T_022_prod_ci_certification_proof.md`
  - FAIL on run 1
  - recorded suite failures for:
    - `runtime/tests/test_isolated_smoke_test.py`
    - `scripts/run_certification_tests.py`
- Follow-up isolation showed:
  - `pytest runtime/tests/test_isolated_smoke_test.py -q` fails once the tracked proof artifact is modified, because the test requires an empty `git status`
- Interpretation:
  - the durable pass receipt already committed at `artifacts/evidence/T_022_prod_ci_certification_proof.md` should remain authoritative for now
  - a fresh repeat-run proof should only be captured once the write path is handled without polluting the cleanliness-sensitive certification run

## Closure Decision

- Leave `T-022` **pending**
- Do not claim Phase 7 canonical closure yet
- Update canon only with truthful status:
  - Phase 9 ratification is complete
  - Phase 10 executor expansion has started
  - Phase 7 still needs remote default-branch proof availability and a clean repeat-run capture

## Next Actions

1. Push or otherwise reconcile the 117 local `main` commits so `.github/workflows/prod_ci_proof.yml` exists on `origin/main`.
2. Re-run `gh workflow run .github/workflows/prod_ci_proof.yml --ref main` after the workflow exists remotely.
3. Re-run `python3 scripts/certification_proof.py --profile ci --evidence-output artifacts/evidence/T_022_prod_ci_certification_proof.md` from a clean worktree after confirming the proof write path does not invalidate cleanliness-sensitive substeps.
