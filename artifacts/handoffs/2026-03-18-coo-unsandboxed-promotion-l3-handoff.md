# COO Unsandboxed Promotion L3 Handoff

Date: 2026-03-18
Plan source: `artifacts/plans/2026-03-18-coo-unsandboxed-promotion-l3.md`
Repo root: `/mnt/c/users/cabra/projects/lifeos`

## Status

The executable engineering portions of the plan are implemented locally but not committed.

Completed:

- Step 1 foundations:
  - capture-dump support added to `runtime/orchestration/coo/commands.py`
  - promotion fixture pack created under `artifacts/coo/promotion_campaign/fixtures/`
  - fixture manifest created
- Step 2 foundations:
  - new instance profiles created
  - pending approval manifest created
  - `runtime/orchestration/coo/promotion_guard.py` added
  - `runtime/tools/openclaw_verify_surface.sh` now runs approval-manifest validation for named profiles
- Step 3, Step 4, Step 6, Step 7 scaffolding:
  - campaign controller, stability checker, rollback, gate3 prepare, gate4 probes/runner, gate5 soak runner/validator, and gate6 handoff builder added under `scripts/campaign/`
- Test surface added for the new seams
- `runtime/orchestration/ceo_queue.py` widened to accept escalation types used by the promotion plan:
  - `budget_above_threshold`
  - `unknown_action_category`

Not completed:

- Step 5 protected-path governance ruling in `docs/01_governance/`
- final campaign execution against live COO / live verify surface
- clean worktree / commit / close-build flow

## Important Constraint

`python3 scripts/workflow/start_build.py coo-unsandboxed-promotion-l3 --kind build` created `.worktrees/coo-unsandboxed-promotion-l3`, but that worktree came up with an inconsistent git index: tracked files appeared as deleted and untracked simultaneously. Because of that, implementation was done in primary to avoid corrupting work on top of a bad worktree state.

Before proceeding, Claude Code should either:

1. diagnose and repair the worktree-first workflow defect, or
2. explicitly continue from primary and then recover into a proper worktree before closure.

## Changed Files

Tracked modifications:

- `runtime/orchestration/ceo_queue.py`
- `runtime/orchestration/coo/commands.py`
- `runtime/tools/openclaw_verify_surface.sh`

New files/directories:

- `artifacts/coo/promotion_campaign/`
- `config/openclaw/instance_profiles/coo_shared_ingress_burnin.json`
- `config/openclaw/instance_profiles/coo_unsandboxed_prod_l3.json`
- `config/openclaw/profile_approvals/`
- `runtime/orchestration/coo/promotion_guard.py`
- `runtime/tests/orchestration/coo/test_campaign_controller.py`
- `runtime/tests/orchestration/coo/test_capture_dump.py`
- `runtime/tests/orchestration/coo/test_handoff_pack.py`
- `runtime/tests/orchestration/coo/test_host_probes.py`
- `runtime/tests/orchestration/coo/test_promotion_fixtures.py`
- `runtime/tests/orchestration/coo/test_promotion_guard.py`
- `runtime/tests/orchestration/coo/test_soak_validator.py`
- `scripts/campaign/`

## Verification Run

Passed:

- `pytest runtime/tests/orchestration/coo/test_capture_dump.py -q`
- `pytest runtime/tests/orchestration/coo/test_promotion_guard.py -q`
- `pytest runtime/tests/orchestration/coo/test_campaign_controller.py -q`
- `pytest runtime/tests/orchestration/coo/test_host_probes.py -q`
- `pytest runtime/tests/orchestration/coo/test_soak_validator.py -q`
- `pytest runtime/tests/orchestration/coo/test_handoff_pack.py -q`
- `pytest runtime/tests/orchestration/coo/test_promotion_fixtures.py -q`
- `pytest runtime/tests/orchestration/coo -q`
  - result: `174 passed`

Started but not completed within the session:

- `pytest runtime/tests -q`
  - observed progress was green while running
  - do not treat as a completed full-suite pass yet

## Likely Follow-On Work

1. Repair or replace the broken worktree flow for this branch.
2. Run `pytest runtime/tests -q` to completion and record final result.
3. Review the newly added `scripts/campaign/*` and manifests for any needed tightening before live execution.
4. Decide whether `coo_promotion_controller.py` should gain a more fixture-aware execution path rather than assuming live CLI invocation for all scenarios.
5. If approved, execute Step 5:
   - create `docs/01_governance/Council_Ruling_COO_Unsandboxed_Prod_L3_v1.0.md`
   - run doc stewardship obligations if any docs are touched
   - run `scripts/campaign/gate3_prepare.py`
6. Run gate execution in order once governance approval exists:
   - gate1 fixtures
   - gate4 candidate checks
   - gate5 soak
   - gate6 handoff
7. Clean/stage/commit and close build properly.

## Suggested Immediate Commands

Inspect current state:

```bash
git status --short
git diff --stat
pytest runtime/tests -q
```

If continuing on the promotion work:

```bash
pytest runtime/tests/orchestration/coo -q
python3 scripts/campaign/gate6_handoff.py --repo-root . --json
python3 -m runtime.orchestration.coo.promotion_guard --repo-root . --json
```

If moving into governance-approved phase:

```bash
python3 scripts/campaign/gate3_prepare.py --repo-root . --ruling-ref docs/01_governance/Council_Ruling_COO_Unsandboxed_Prod_L3_v1.0.md --dry-run
```

## Notes

- No protected-path governance document was created in this session.
- No commit was made.
- Repo is currently dirty and requires stewarding before exit.
