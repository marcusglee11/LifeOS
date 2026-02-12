---
name: close-build
description: Use when a branch is ready to close. Closure gates (tests, doc stewardship) are enforced automatically by the PreToolUse hook on git merge/push. This skill handles merge orchestration, cleanup, and the final report.
---

# Close Build

Merge to main and clean up. Closure gates run automatically via the PreToolUse hook.

## Default behavior

```bash
python3 scripts/workflow/closure_pack.py
```

This runs:
- squash merge to `main`,
- local cleanup (branch delete + active context clear).

Note: targeted closure tests and doc stewardship are enforced by the
`.claude/hooks/close-build-gate.sh` PreToolUse hook on `git merge`/`git push`.
They no longer need to be invoked manually.

## Dry run (gates only)

```bash
python3 scripts/workflow/closure_gate.py
```

Use to check gate status without merge/cleanup. Returns JSON verdict.

## No cleanup mode

```bash
python3 scripts/workflow/closure_pack.py --no-cleanup
```

Use when you need to keep branch/context after merge.

## Report contract (strict)

Output must use this section order:

1. `Branch`
2. `Commits`
3. `Test Results`
4. `What Was Done`
5. `What Remains`
