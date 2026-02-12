---
name: handoff-pack
description: Use when handing work to another agent or processing an inbound handoff. Produces compact, deterministic pack sections and updates active context.
---

# Handoff Pack

Generate minimal-token handoffs with deterministic structure.

## Modes

- `to_codex`: outbound task handoff to Codex.
- `from_codex`: ingest Codex build summary and continue.

Default:
- If user supplied a pasted summary, use `from_codex`.
- Otherwise use `to_codex`.

## Step 1: Collect Facts

```bash
git rev-parse --abbrev-ref HEAD
git log --oneline -n 10
git status --short
```

Use targeted test routing:

```bash
scripts/workflow/test_router.sh
```

## Step 2: Refresh Active Context

```bash
python3 scripts/workflow/active_work.py refresh
python3 scripts/workflow/active_work.py show
```

## Step 3: Emit Strict Pack

Use exact section order:

1. `Branch`
2. `Commits`
3. `Test Results`
4. `What Was Done`
5. `What Remains`

Optional section (only when needed):
- `Key Files`
- `Gotchas`

## `to_codex` extras

Add:
- `Task`
- `Scope`
- `Acceptance Criteria`
- `Patterns To Follow`
- `Do NOT`

## `from_codex` extras

Add:
- `Claims Verified`
- `Deltas from Claims`
