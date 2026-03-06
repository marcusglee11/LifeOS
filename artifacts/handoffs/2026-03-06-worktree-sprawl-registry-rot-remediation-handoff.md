# Handoff: Worktree Sprawl and Active-Branch Registry Remediation

**Date:** 2026-03-06
**From:** Codex
**To:** Next implementation / review session
**Type:** Code handoff

---

## Branch

- Current branch: `fix/worktree-sprawl-registry-rot-r`
- Worktree: `/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/worktree-sprawl-registry-rot-r`
- Commit state: no commits yet for this build; worktree currently has 12 uncommitted file changes

---

## Scope Completed

Implemented the remediation plan from:

- `artifacts/plans/2026-03-06-worktree-sprawl-registry-rot-remediation-plan.md`

Core fixes completed:

1. `cleanup_after_merge()` now force-deletes merged scoped branches with `git branch -D`.
2. Post-merge cleanup now closes active registry rows through shared helpers in `scripts/git_workflow.py`.
3. `start_build.py` upsert logic now closes duplicate active rows for the same branch instead of leaving multiple active entries behind.
4. RPPV `check_rppv_014()` now removes temp worktree registrations and prunes in a unified cleanup path.
5. Session-start hook now runs a safe worktree audit and warns only on real high-count / stale-registration conditions.
6. Added a standalone reconciliation script for `artifacts/active_branches.json`.
7. Reconciled the canonical primary-repo registry once against git ground truth.

---

## Files Changed In This Worktree

- `.claude/hooks/session-context-inject.py`
- `runtime/tests/test_git_workflow_worktree.py`
- `runtime/tests/test_workflow_pack.py`
- `runtime/tools/workflow_pack.py`
- `scripts/git_workflow.py`
- `scripts/packaging/tests/test_rppv_validator.py`
- `scripts/packaging/validate_return_packet_preflight.py`
- `scripts/workflow/start_build.py`
- `scripts/workflow/reconcile_active_branches.py`
- `runtime/tests/test_reconcile_active_branches.py`
- `runtime/tests/test_session_context_inject.py`

Related primary-repo state updated outside this linked worktree:

- `/mnt/c/Users/cabra/Projects/LifeOS/artifacts/active_branches.json`

This file is the canonical active-branch registry and was reconciled by running:

```bash
python3 scripts/workflow/reconcile_active_branches.py --repo-root /mnt/c/Users/cabra/Projects/LifeOS
```

---

## Test Results

Passed:

- `pytest runtime/tests/test_workflow_pack.py -q`
- `pytest scripts/packaging/tests/test_rppv_validator.py -q`
- `pytest runtime/tests/test_git_workflow_worktree.py -q`
- `pytest runtime/tests/test_session_context_inject.py runtime/tests/test_reconcile_active_branches.py -q`
- Full suite excluding `test_spine.py`: `2397 passed, 7 skipped, 0 failed`
- `pytest runtime/tests/orchestration/loop/test_spine.py -q`
  - passes independently (`3.65s`)

Registry verification:

- `python3 scripts/workflow/reconcile_active_branches.py --repo-root /mnt/c/Users/cabra/Projects/LifeOS --dry-run`
  - Result after reconciliation: `No changes required.`

Operational verification:

- `git worktree list --porcelain`
  - After pruning, only live worktrees remain.

Known verification caveat:

- `pytest runtime/tests -q`
  - intermittently hangs around `runtime/tests/orchestration/loop/test_spine.py` when run inside the full WSL suite
  - `test_spine.py` itself passes independently
  - treat this as a pre-existing WSL concurrency issue, not a regression from this branch

---

## Canonical Registry State After Reconcile

Observed in `/mnt/c/Users/cabra/Projects/LifeOS/artifacts/active_branches.json`:

- stale active rows for missing branches were closed
- stale `worktree_path` values for missing worktrees were cleared
- duplicate active rows for:
  - `build/build-entry-enforcement`
  - `build/build-entry-hooks`
  were collapsed so only one active row remains for each

Current active branch count in the canonical registry:

- `5`

Active names at handoff time:

- `build/openclaw-upgrade-and-council-dogfood`
- `build/coo-security-audit-warning-gatefix`
- `build/build-entry-enforcement`
- `build/build-entry-hooks`
- `fix/worktree-sprawl-registry-rot-r`

---

## Notable Implementation Details

- Shared registry mutation now lives in `scripts/git_workflow.py` via `close_active_branch_records(...)`.
- `cleanup_after_merge()` returns `registry_records_closed` so callers/tests can assert actual registry mutation.
- `start_build._upsert_active_branch_record()` now preserves a single active row per branch and closes older duplicate active rows.
- The reconciliation script is idempotent and safe to dry-run repeatedly.
- The session hook audit is intentionally non-destructive beyond `git worktree prune`.

---

## Remaining Work

If continuing from here:

1. Investigate the hang in `runtime/tests/orchestration/loop/test_spine.py` if a full `runtime/tests -q` pass is required for closure.
2. Commit the work in this branch; nothing is committed yet.
3. Decide whether to stage the reconciled primary-repo `artifacts/active_branches.json` into this branch explicitly, since it was updated against the canonical repo root rather than through the linked worktree checkout.
4. Review whether `closed` vs `merged` semantics in the registry should be normalized further; this remediation preserved existing semantics and only enforced consistency.

---

## Quick Resume Commands

From the linked worktree:

```bash
cd /mnt/c/Users/cabra/Projects/LifeOS/.worktrees/worktree-sprawl-registry-rot-r
pytest runtime/tests/test_workflow_pack.py -q
pytest scripts/packaging/tests/test_rppv_validator.py -q
pytest runtime/tests/test_git_workflow_worktree.py -q
pytest runtime/tests/test_session_context_inject.py runtime/tests/test_reconcile_active_branches.py -q
python3 scripts/workflow/reconcile_active_branches.py --repo-root /mnt/c/Users/cabra/Projects/LifeOS --dry-run
```
