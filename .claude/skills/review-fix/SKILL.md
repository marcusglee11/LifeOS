---
name: review-fix
description: Use when review findings are provided and you must fix obvious/patterned issues quickly with minimal tokens. Reads reviewer commit diff first, then applies the tiered review-fix-report protocol.
---

# Review Fix (Diff-First)

This skill enforces low-friction review handling:
- read reviewer commit diff first (shared truth),
- fix obvious/patterned issues in-place,
- keep judgment/architectural items explicit,
- emit compact deterministic report.

## Inputs

At least one of:
- reviewer commit SHA,
- commit range (`<base>..<head>`),
- branch to review.

## Step 1: Read Shared Truth First

```bash
git show --stat --name-only <reviewer-commit>
git show <reviewer-commit>
```

If a range is provided:

```bash
git log --oneline <base>..<head>
git diff <base>..<head> --stat
```

Do not rely on pasted prose if commit diff exists.

## Step 2: Run Targeted Tests via Router

```bash
scripts/workflow/test_router.sh <changed-file>...
```

Run returned commands first, then run broader suite only if needed.

## Step 3: Fix by Tier

- **Obvious/Patterned:** fix and commit directly.
- **Judgment:** present 2-3 options with recommendation.
- **Architectural:** escalate, do not silently decide.

## Step 4: Update Active Context Artifact

```bash
python3 scripts/workflow/active_work.py refresh \
  --focus "<task-id-or-scope>" \
  --test "<targeted-test-command>"
```

This keeps sessions small and handoffs deterministic.

## Step 5: Report Format (strict)

Always use these headings and order:

1. `Branch`
2. `Commits`
3. `Test Results`
4. `What Was Done`
5. `What Remains`

If no remaining items exist, write `What Remains: None`.
