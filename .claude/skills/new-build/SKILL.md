---
name: new-build
description: Create a branch in an isolated worktree before writing code to avoid cross-session contamination in the primary repo.
---

# New Build

Create a build branch in an isolated worktree. This prevents Article XIX
blocks and merge conflicts caused by concurrent agent activity in the primary
working tree.

## Command

```bash
python3 scripts/workflow/start_build.py <topic> [--kind build|fix|hotfix|spike]
cd <printed path>
```

Examples:
- `python3 scripts/workflow/start_build.py auth-token-refresh`
- `python3 scripts/workflow/start_build.py stale-cache-cleanup --kind fix`

## What It Does

1. Slugifies topic and derives branch name from `--kind`.
2. Resolves the primary repo worktree (even if invoked from a linked worktree).
3. Atomically creates branch + linked worktree from `main`.
4. Tracks metadata in `artifacts/active_branches.json` including `worktree_path`.

## Verify Isolation

```bash
git status --porcelain=v1
git branch --show-current
pytest runtime/tests -q
```

## Close Build

Run `/close-build` from the linked worktree. Successful closure removes the
linked worktree and branch.

## Recover Wrong-Path Work

If work already started on a scoped branch (`build/`, `fix/`, `hotfix/`,
`spike/`) in the primary repo, recover it instead of hand-migrating:

```bash
python3 scripts/workflow/start_build.py --recover-primary
```

## When To Skip

Only skip when you are the sole active build and the primary working tree is
confirmed clean (`git status --porcelain=v1` is empty). Hotfix work still uses
a worktree branch; never commit directly on `main`.
