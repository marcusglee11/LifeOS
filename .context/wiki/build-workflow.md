---
source_docs:
  - docs/02_protocols/Git_Workflow_Protocol_v1.1.md
  - docs/02_protocols/Build_Handoff_Protocol_v1.1.md
  - CLAUDE.md
  - .claude/rules/agent-coordination.md
  - .claude/rules/git-hygiene.md
last_updated: bf4d9ecd
concepts:
  - worktree isolation
  - branch naming
  - Article XIX
  - close-build
  - start_build
  - sprint isolation
---

# Build Workflow

## Summary

All builds run in isolated git worktrees — never in the primary repo. This is
a hard gate, not a soft instruction: shared working tree + concurrent agent
writes causes Article XIX blocks, merge conflicts, and orphaned files. The
`start_build.py` / `close_build.py` scripts are the canonical entry points.

## Key Relationships

- **[agent-roles](agent-roles.md)** — sprint agents own builds; COO issues work orders.
- **[doc-stewardship](doc-stewardship.md)** — doc changes follow this same workflow.
- **Scripts**: `scripts/workflow/start_build.py`, `scripts/workflow/close_build.py`
- **Dispatch wrapper**: `scripts/workflow/dispatch_codex.sh` (hard-gates on worktree existence)

## Branch Naming

| Kind | Branch prefix | Command |
|------|--------------|---------|
| Feature | `build/<topic>` | default |
| Fix | `fix/<topic>` | `--kind fix` |
| Hotfix | `hotfix/<topic>` | `--kind hotfix` |
| Spike | `spike/<topic>` | `--kind spike` |

Never commit directly on `main`.

## Start a Build

```bash
python3 scripts/workflow/start_build.py <topic> [--kind build|fix|hotfix|spike]
# → prints worktree path, e.g. .worktrees/<topic>/
cd <worktree_path>
```

Atomically: creates branch + linked worktree from `main`. Tracks metadata in
`artifacts/active_branches.json`.

## Article XIX

Pre-commit hook blocks commits when untracked files exist on the current
branch. `--no-verify` exemption requires all three: (1) commit IS the
resolution, (2) remaining untracked files belong to concurrent agent WIP,
(3) file cannot be staged here. Document exemption in commit message body.

## Close a Build

Run from the linked worktree:
```bash
python3 scripts/workflow/close_build.py
# or: /close-build skill
```

Gates: tests pass, quality gate green, git status clean, doc stewardship valid.

## Handoff Rules

- Never "wait for branch X to merge" in a handoff — provide a direct file path or commit SHA.
- If a resource doesn't exist yet, don't write the handoff — wait until it does.
- Git is the shared bus between agents: commits, diffs, files.

## Current State

Primary repo on `main`. 117 commits ahead of `origin/main` (Phase 7 pending
remote sync). `close_build` performance note: `pytest runtime/tests` on NTFS
takes 8–25 min; targeted test routing in `runtime/tools/workflow_pack.py`
can reduce this to ~10s for config/doc-only changes.

## Open Questions

None currently flagged.
