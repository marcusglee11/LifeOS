# Council V2 COO Unsandboxed Promotion L3 Handoff

Date: 2026-03-19
Branch: `build/coo-unsandboxed-promotion-l3`
Repo root: `/mnt/c/users/cabra/projects/lifeos/.worktrees/coo-unsandboxed-promotion-l3`
Subject commit under review: `3a31285c`

## Status

The promotion-specific Council V2 dogfood workflow is implemented locally in the promotion worktree but not committed.

Completed:

- Added a promotion CCP at `artifacts/council_reviews/coo_unsandboxed_prod_l3.ccp.yaml`
- Added a promotion-specific V2 runner at `scripts/workflow/run_council_review_coo_unsandboxed_promotion.py`
- Added shared dogfood helpers at `runtime/tools/council_v2_dogfood_common.py`
- Added promotion mock coverage at `runtime/tests/orchestration/council/test_council_promotion_mock.py`
- Refactored the existing dogfood tool to use shared helpers and restored `_parse_dotenv` compatibility in `runtime/tools/council_v2_dogfood_review.py`
- Updated `.gitignore` so the promotion CCP is no longer swallowed by `artifacts/council_reviews/`

Not completed:

- no live Council V2 run was executed
- no review packet artifact was generated from a live run
- no queue escalation was created from a live run
- no protected-path governance ruling was written
- no commit / close-build flow was done

## What The New Workflow Does

`scripts/workflow/run_council_review_coo_unsandboxed_promotion.py` now:

- loads the promotion CCP
- compiles with `compile_council_run_plan_v2`
- fails closed unless:
  - tier is `T3`
  - `Risk` is required
  - `Governance` is required
  - no compiled model assignment resolves to `anthropic` or `openai`
- runs the mock gate first
- runs `CouncilFSMv2` for the live path
- writes review artifacts under `artifacts/council_reviews/<timestamp>/`
- generates a draft ruling outside protected paths
- generates and validates a review packet
- creates a `GOVERNANCE_SURFACE_TOUCH` escalation only after packet validation passes and the live result is still `PASS`
- emits a summary JSON with `subject.branch` and `subject.commit`

Important implementation detail:

- packet generation was tightened so the final packet is rebuilt after the final summary write, avoiding stale AC-4 hashes

## V2-Specific Constraints Captured

The implementation follows the reviewed V2 constraints:

- no `override.mode`
- V2 preflight checks `tier == T3`, not `M2_FULL`
- V2 roles/lenses use:
  - `Chair`
  - `Challenger`
  - `Risk`
  - `Governance`
- the CCP explicitly overrides `Risk` and `Governance` to `openrouter/z-ai/glm-5`
- the CCP uses:
  - `aur_id: AUR-COO-UNSANDBOX-PROMO-L3-001`
  - `touches: [runtime_core, tests, governance_protocol]`

The `Risk` override is deliberate workaround coverage for the existing V1/V2 compiler independence mismatch.

## Current Dirty Files

- `.gitignore`
- `runtime/tools/council_v2_dogfood_review.py`
- `artifacts/council_reviews/coo_unsandboxed_prod_l3.ccp.yaml`
- `runtime/tests/orchestration/council/test_council_promotion_mock.py`
- `runtime/tools/council_v2_dogfood_common.py`
- `scripts/workflow/run_council_review_coo_unsandboxed_promotion.py`

## Verification Run

Passed:

- `python3 scripts/workflow/run_council_review_coo_unsandboxed_promotion.py --dry-run`
- `pytest runtime/tests/test_council_v2_dogfood_review.py -q`
  - result: `3 passed`
- `pytest runtime/tests/orchestration/council/test_council_promotion_mock.py -q`
  - result: `4 passed`

Did not complete cleanly within the session:

- `pytest runtime/tests -q`
  - advanced cleanly through council/dispatch/loop surfaces
  - last observed progress reached `24%`
  - last visible test area was `runtime/tests/orchestration/missions/test_review_council_runtime.py`
  - log path: `/tmp/pytest_runtime_tests.log`
  - do not claim a full-suite pass from this session

## Follow-On Work For Claude Code

1. Run `pytest runtime/tests -q` to a definitive completion and determine whether the `24%` stall is real or environmental.
2. If the full suite is green, run the new wrapper in a live-safe environment and inspect:
   - review directory contents
   - summary JSON
   - review packet validator output
   - queue escalation creation
3. Confirm the live path uses the intended provider credentials and does not drift to forbidden families.
4. If Council acceptance and manual approval are obtained later:
   - steward the approved ruling into `docs/01_governance/Council_Ruling_COO_Unsandboxed_Prod_L3_v1.0.md`
   - run `python3 scripts/campaign/gate3_prepare.py --repo-root . --ruling-ref docs/01_governance/Council_Ruling_COO_Unsandboxed_Prod_L3_v1.0.md`
5. Stage, commit, and continue the governance-gated promotion flow.

## Suggested Immediate Commands

```bash
git status --short --untracked-files=all
git diff --stat
python3 scripts/workflow/run_council_review_coo_unsandboxed_promotion.py --dry-run
pytest runtime/tests/test_council_v2_dogfood_review.py -q
pytest runtime/tests/orchestration/council/test_council_promotion_mock.py -q
pytest runtime/tests -q
```

If moving to a live council run:

```bash
python3 scripts/workflow/run_council_review_coo_unsandboxed_promotion.py
```

If checking the stalled full-suite log from this session:

```bash
tail -n 50 /tmp/pytest_runtime_tests.log
```

## Notes

- The promotion CCP path was initially ignored by `.gitignore`; that has been corrected locally but not committed.
- No protected-path files were touched in this session.
- No live Council V2 artifact set should be assumed to exist yet.
- The worktree remains dirty and uncommitted.
