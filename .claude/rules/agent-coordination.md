---
paths: ["**"]
---
# Agent Coordination Rules

## Codex Dispatch — Worktree Isolation (Hard Gate)

**Never run Codex in the primary repo.** Shared working tree + concurrent agent writes = Article XIX blocks, merge conflicts, and orphaned files.

**Always use the wrapper:**
```bash
scripts/workflow/dispatch_codex.sh <topic> "<task>"
```

The wrapper hard-gates on worktree existence and rejects `cwd == primary repo root`.

**Failure modes to reject, never work around:**
- `dispatch_codex.sh` exits 2/3/4 → fix worktree creation, do NOT fall back to primary repo
- MCP unavailable → either use `dispatch_codex.sh` CLI fallback or build the task yourself (do NOT run Codex without worktree)
- `start_build.py` fails → investigate, do NOT continue without isolation

## Handoff Timing — No Conditional Starts

**Never write "begin only after X merges" in a handoff.** The receiving agent blocks or polls, wasting context.

Instead, always provide a file path or commit SHA that is available **right now**:
- If the resource exists in a worktree: `read from <absolute_path>` — available immediately, no merge required
- If the resource genuinely doesn't exist yet: don't write the handoff — wait until you have something real to hand off
- If timing is unavoidable: say exactly what to poll, for how long, and what to do if it times out

**Before finalising any outbound handoff, verify every "Start after..." or "Wait for..." phrase — replace each with a concrete path or commit SHA.**
