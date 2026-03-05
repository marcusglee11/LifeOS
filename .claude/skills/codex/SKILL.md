---
name: codex
description: Delegate a bounded task to the Codex agent via MCP. Claude enriches the prompt with repo context, Codex executes, Claude reviews the result using the tiered review-build protocol before reporting.
---

# Codex Delegation

Delegate a task to Codex via the `codex-builder` MCP server. Claude gathers context, enriches the prompt, calls Codex, reviews the output, and reports.

## When to Use

- You want Codex's implementation on a bounded task
- You want a second model's independent attempt at something
- Invocation: `/codex <brief task description>` with optional constraints in the message

## Skill Chain

`/codex` fits into a larger delegation pipeline. Use adjacent skills as needed:

| Stage | Skill | When |
|-------|-------|------|
| Pre-codex | `/handoff-pack to_codex` | Complex tasks — builds the full structured context block (Scope, Acceptance Criteria, Patterns, Do NOT) before calling Codex |
| Post-codex | `/review-build` | Codex produced a branch or commit range — use review-build for a full tiered review instead of the inline Step 4 |
| Post-review | `/review-fix` | Review findings exist — review-fix applies the obvious/patterned ones quickly with minimal tokens |
| Continuation | `/handoff` | Codex's output becomes the next sprint for Antigravity or another session |
| Merge | `/close-build` | Codex's branch is reviewed and ready — close-build gates apply identically to Codex output |

Full pipeline:

```
/handoff-pack to_codex  ->  /codex  ->  /review-build  ->  /review-fix  ->  /close-build
```

## Pre-flight — Worktree Isolation (Hard Gate)

Before delegating any task that writes files, Codex **must** run in an isolated worktree. The primary repo is shared state — Codex running there causes Article XIX blocks, merge conflicts, and stash pop failures.

**Use the wrapper script (preferred):**
```bash
scripts/workflow/dispatch_codex.sh <topic> "<task prompt>"
```
This atomically creates the worktree via `start_build.py` and hard-gates the `cwd` so it can never point at the primary repo root.

**If calling Codex MCP directly:** create the worktree first, then set `cwd` to the worktree path — never to the primary repo root.
```bash
python3 scripts/workflow/start_build.py <topic>
# → prints "Worktree ready at: <path>" — use that path as cwd
```

**Failure mode:** If `dispatch_codex.sh` exits with code 2/3/4, do NOT fall back to running Codex in the primary repo. Fix the worktree creation failure first, then retry.

**Read-only tasks:** worktree isolation not required (no writes). Set `sandbox: "read-only"` instead.

---

## Step 1 — Gather Repo Context

Read before constructing the prompt:

```bash
git branch --show-current
git log --oneline -5
git status --short
head -35 docs/11_admin/LIFEOS_STATE.md
```

Also grep/glob for files directly relevant to the task description. Include their paths (and brief purpose) in the context block.

## Step 2 — Construct Enriched Prompt

Combine into a structured block:

```
Task: <user's intent, verbatim>
Constraints: <any constraints the user specified, or omit this line>

Repo context:
- Branch: <current branch>
- Recent commits: <3-5 git log one-liners>
- Current focus: <LIFEOS_STATE.md Current Focus line>
- Relevant files: <list with one-line purpose each>
```

Parse constraints from the user's message — anything after `--constraints`, in quotes, or phrased as don't, avoid, must, only. If none, omit the Constraints line entirely.

For complex tasks, run `/handoff-pack to_codex` first — it produces a richer block including Scope, Acceptance Criteria, and Do NOT constraints. Paste that output as the enriched prompt.

## Step 3 — Call Codex via MCP

Use the `codex` MCP tool from the `codex-builder` server with these parameters:

```json
{
  "prompt": "<enriched prompt from Step 2>",
  "cwd": "<absolute path to worktree — NOT primary repo root>",
  "sandbox": "workspace-write"
}
```

The `workspace-write` sandbox allows Codex to read and write files in the repo but blocks network access and system changes. This is appropriate for bounded implementation tasks.

If the task is read-only (review, analysis, planning only), use `sandbox: "read-only"` instead.

The tool returns `{threadId, content}`. Save the `threadId` if you need to continue the session — use the `codex-reply` tool with `{threadId, prompt}` for follow-up turns.

## Step 4 — Review the Result

Apply the tiered review-build protocol to whatever Codex produced.

**For simple in-session changes** (Codex edited files, no separate branch):

| Finding | Action |
|---------|--------|
| Obvious/patterned issue | Fix in-place, commit with `fix: review finding — <summary>` |
| Judgment call | Propose 2-3 options, wait for user decision |
| Architectural concern | Report only, escalate |

**For branch-level output** (Codex committed to a branch): invoke `/review-build` with the branch name or commit SHA — it handles the full tiered review and applies obvious fixes in-place.

**If review findings were already produced**: invoke `/review-fix` to apply the obvious/patterned ones quickly with minimal tokens.

Run tests after any in-place fixes:

```bash
pytest runtime/tests -q
```

## Step 5 — Report

Output in this exact order:

```
Delegated Task: <brief>
Codex Output: <summary of what Codex produced — files changed, tests run, etc.>
Review Findings: <tiered list, or none>
Fixes Applied: <what Claude fixed in-place, or none>
Test Results: <N passed, M failed — or not run>
What Remains: <open items or none>
```
