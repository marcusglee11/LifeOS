# Codex Delegation Skill — Design

**Date:** 2026-02-26
**Status:** Approved
**Author:** Claude Code (brainstorming session)

---

## Purpose

A project-local Claude Code skill (`/codex`) that delegates bounded tasks to the Codex agent via the `codex-builder` MCP server, enriches the prompt with live repo context, and applies the review-build protocol to Codex's output before reporting results.

## Identity

- **Skill name:** `codex`
- **Invocation:** `/codex <brief task description>` with optional `--constraints "..."`
- **Location:** `.claude/skills/codex/SKILL.md`
- **Pattern:** Consistent with existing standalone skills (`close-build`, `handoff-pack`)

## Approach Chosen

**MCP-native (Option A):** Claude calls `codex-builder` MCP tools directly within the session. No Bash bridge for the delegation step. If the MCP surface proves insufficient, a Bash fallback (`codex exec`) can be added later.

## Flow

### Step 1 — Gather Repo Context

Read before constructing the prompt:

```bash
git branch --show-current
git log --oneline -5
git status --short
head -35 docs/11_admin/LIFEOS_STATE.md
```

Also grep/glob for files relevant to the user's task description.

### Step 2 — Construct Enriched Prompt

```
Task: <user's intent>
Constraints: <user-supplied, or omitted>

Repo context:
- Branch: <branch>
- Recent commits: <3-5 one-liners>
- Current focus: <from LIFEOS_STATE.md>
- Relevant files: <list with brief purpose>
```

User constraints are parsed from the invocation message (e.g. `--constraints "no new deps"`). If absent, the field is omitted.

### Step 3 — Call Codex MCP

Inspect available `codex-builder` tools at invocation time. Prefer whichever tool supports full execution (file I/O, code changes) over review-only tools. Pass the enriched prompt with repo root as working directory.

### Step 4 — Review Result (tiered)

Apply the review-build protocol:

| Finding | Action |
|---------|--------|
| Obvious/patterned | Fix in-place, commit, note it |
| Judgment call | Propose 2-3 options |
| Architectural | Report only, escalate |

Run `pytest runtime/tests -q` after any in-place fixes.

### Step 5 — Report

```
Delegated Task: <brief>
Codex Output: <what Codex produced>
Review Findings: <tiered>
Fixes Applied: <or "none">
Test Results: <pass/fail + count>
What Remains: <open items or "none">
```

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary mode | Delegation-first | Peer review is secondary use case |
| Result flow | Claude reviews before reporting | Reduces unreviewed Codex output reaching user |
| Task scope | Any task (user decides) | Optional constraints allow per-invocation guidance |
| Prompt construction | Claude enriches | Brief intent → full context, less user burden |
| Integration | MCP-native first | Dogfoods the configured codex-builder server |

## Out of Scope (v1)

- Peer-review / cognitive broadening mode (second use case — add in v2)
- Bash `codex exec` fallback
- Multi-turn Codex sessions
- Automatic task selection from BACKLOG.md
