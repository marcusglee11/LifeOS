# Handoff Pack: Closure Plan for Both Builds

## Status
- Branch prepared: `build/council-process-fixes`
- Base: `main` (`cb6b7fc`)
- Worktree state: clean
- Full suite: `1981 passed, 10 skipped, 6 warnings` (`pytest runtime/tests -q`)

## Build A (Phase C code fixes)
- Commits:
  - `c74e449` `fix(receipts): harden phase c land gate and recovery semantics`
  - `1a6ceb8` `docs(handoff): add phase c council dogfood fixes pack`
- Handoff doc:
  - `artifacts/handoffs/Handoff_Phase_C_Council_Dogfood_Fixes.md`

## Build B (Council quality/process hardening)
- Commits:
  - `b213eca` `fix(council): enforce evidence-grounded seat outputs`
  - `71de232` `chore(council): add grounding preflight to reviewer prompts`
  - `cfa6273` `docs(handoff): add council evidence-grounding hardening pack`
- Handoff doc:
  - `artifacts/handoffs/Handoff_Council_Evidence_Grounding_Hardening.md`

## LifeOS-Compliant Closure Path (recommended)
Run from repository root (`/mnt/c/Users/cabra/Projects/LifeOS`) using the close-build workflow skill/script.

### Option 1: Close both builds together (single merge)
1. `cd /mnt/c/Users/cabra/Projects/LifeOS/.worktrees/council-process-fixes`
2. `python3 scripts/workflow/closure_gate.py`
3. `python3 scripts/workflow/closure_pack.py`

Expected outcome:
- Squash merge into `main`
- State/backlog refresh via closure script
- Branch cleanup
- Standard close-build report sections

### Option 2: Close as two separate merges
If you want isolated PR/merge artifacts per build:

1. From `main`, create branch for Build A and cherry-pick:
   - `git checkout -b build/phase-c-fixes-final main`
   - `git cherry-pick c74e449 1a6ceb8`
   - run closure (`closure_gate.py`, then `closure_pack.py`)

2. From updated `main`, create branch for Build B and cherry-pick:
   - `git checkout -b build/council-quality-hardening-final main`
   - `git cherry-pick b213eca 71de232 cfa6273`
   - run closure (`closure_gate.py`, then `closure_pack.py`)

## Notes for Claude Code
- Close-build gate enforces tests/doc stewardship automatically via hook.
- If closure is run from wrong context and reports worktree/main conflict, rerun from the worktree path above.
- Use `--no-cleanup` only if you explicitly want to keep branch/context after merge.
