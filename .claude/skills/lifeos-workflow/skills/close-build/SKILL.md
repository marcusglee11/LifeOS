---
name: close-build
description: Use when a branch is ready to close with low friction. Runs closure tests, doc stewardship when needed, merge to main, and cleanup.
---

# Close Build

Complete the final lifecycle step with minimal prompts.

## Default behavior

```bash
python3 scripts/workflow/closure_pack.py
```

This runs:
- targeted closure tests,
- doc stewardship gate only when `docs/` changed,
- squash merge to `main`,
- local cleanup.

## Dry run

```bash
python3 scripts/workflow/closure_pack.py --dry-run
```

Use for preflight verification without merge/cleanup.

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
