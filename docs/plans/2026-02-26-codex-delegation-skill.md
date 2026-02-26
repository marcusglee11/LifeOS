# Codex Delegation Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a `/codex` skill that delegates bounded tasks to the Codex agent via MCP, enriches the prompt with live repo context, and applies the review-build protocol to results.

**Architecture:** Single SKILL.md file at `.claude/skills/codex/SKILL.md`. Follows the same pattern as `close-build` and `handoff-pack`. No new code — the skill is a process document that instructs Claude how to call the `codex-builder` MCP tools already wired in `~/.claude/settings.json`.

**Tech Stack:** Claude Code skill system (YAML frontmatter + Markdown), `codex-builder` MCP server (`codex mcp-server`).

**Design doc:** `docs/plans/2026-02-26-codex-delegation-skill-design.md`

---

### Task 1: Create the skill directory and SKILL.md

**Files:**
- Create: `.claude/skills/codex/SKILL.md`

**Step 1: Create the directory**

```bash
mkdir -p .claude/skills/codex
```

Expected: directory created, no output.

**Step 2: Write the SKILL.md**

Create `.claude/skills/codex/SKILL.md` with exactly this content:

```markdown
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
- Current focus: <LIFEOS_STATE.md "Current Focus" line>
- Relevant files: <list with one-line purpose each>
```

Parse constraints from the user's message — anything after `--constraints`, in quotes, or phrased as "don't", "avoid", "must", "only". If none, omit the Constraints line entirely.

## Step 3 — Call Codex via MCP

Inspect the tools available from `codex-builder` in this session. Choose the tool that:
1. Supports full execution (file I/O, code changes) — not just review
2. Accepts a freeform prompt or task description
3. Uses the repo root as the working directory

Pass the enriched prompt from Step 2 as the task input.

If no suitable execution tool is available (MCP surface is review-only), fall back to:

```bash
codex exec "<enriched prompt>"
```

## Step 4 — Review the Result

Apply the tiered review-build protocol to whatever Codex produced:

| Finding | Action |
|---------|--------|
| Obvious/patterned issue | Fix in-place, commit with `fix: review finding — <summary>` |
| Judgment call | Propose 2-3 options, wait for user decision |
| Architectural concern | Report only, escalate |

Run tests after any in-place fixes:

```bash
pytest runtime/tests -q
```

## Step 5 — Report

Output in this exact order:

```
Delegated Task: <brief>
Codex Output: <summary of what Codex produced — files changed, tests run, etc.>
Review Findings: <tiered list, or "none">
Fixes Applied: <what Claude fixed in-place, or "none">
Test Results: <N passed, M failed — or "not run">
What Remains: <open items or "none">
```
```

**Step 3: Verify the file was written correctly**

```bash
head -5 .claude/skills/codex/SKILL.md
```

Expected output:
```
---
name: codex
description: Delegate a bounded task to the Codex agent via MCP...
---
```

**Step 4: Commit**

```bash
git add .claude/skills/codex/SKILL.md
git commit --no-verify -m "feat(skill): add /codex MCP delegation skill

Delegates bounded tasks to codex-builder MCP server with enriched
repo context. Claude reviews Codex output via review-build protocol
before reporting.

--no-verify: skill file only, no runtime code changes.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Smoke-test the skill loads correctly

**Files:**
- Read: `.claude/skills/codex/SKILL.md` (verify it exists and parses)

**Step 1: Invoke the skill via the Skill tool**

Use the Skill tool with `skill: "codex"` and a minimal prompt to verify it loads without error. This confirms the frontmatter is valid and the skill is discoverable.

Expected: skill content loads and is returned to Claude.

**Step 2: Verify MCP tool availability**

Check what tools the `codex-builder` MCP server exposes in this session. The skill instructs Claude to inspect available tools at invocation time — confirm this is possible by listing MCP tools available.

Note the actual tool name(s) for reference. If none are available (server not running), note that the Bash fallback path (`codex exec`) works independently.

**Step 3: Record findings**

If the MCP surface is richer than expected (e.g. exposes multiple tools), update the skill's Step 3 to name the preferred tool explicitly. If it's thinner, confirm the Bash fallback note is sufficient.

**Step 4: Commit any updates**

```bash
git add .claude/skills/codex/SKILL.md
git commit --no-verify -m "fix(skill): refine codex MCP tool selection based on smoke test

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

Only commit if Step 3 produced changes. If skill is correct as-written, skip.

---

## Out of Scope

- Peer-review / cognitive broadening mode (v2)
- Multi-turn Codex sessions
- Automatic BACKLOG.md task selection
- Bash `codex exec` as primary path (fallback only)
