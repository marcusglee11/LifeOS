---
name: review-build
description: Review a build from another agent using the tiered review-fix-report protocol. Fixes obvious issues in-place, proposes options for judgment calls, escalates architectural concerns.
---

# Review Build

Review a build from another agent using the tiered review-fix-report protocol. Fix obvious issues in-place rather than just reporting them.

## Inputs

The user will provide one or more of:
- A branch name (e.g., `build/master-plan-v1-1-canonicalization`)
- A commit range (e.g., `e7d7ab8..d848d1f`)
- A build summary (pasted from the building agent)
- A PR number

If only a branch name is given, diff against the branch's merge-base with `main`.

## Step 1: Understand the Scope

```bash
# Get the commit range
git log --oneline <base>..<head>

# Get the full diff
git diff <base>..<head> --stat
```

Read the changed files. Understand what was built, not just what changed.

## Step 2: Run Pre-Existing Baseline

```bash
# Check if failures exist BEFORE this build
git stash && git checkout <base-commit> --quiet
pytest runtime/tests -q 2>&1 | tail -5
git checkout <branch> --quiet && git stash pop 2>/dev/null
```

This establishes which test failures are pre-existing vs introduced.

## Step 3: Review Each Change

For each file changed, assess:

1. **Correctness** - Does the code do what it claims?
2. **Completeness** - Are there missing cases, uncovered paths?
3. **Consistency** - Does it follow existing codebase patterns?
4. **Safety** - Error handling, validation, security concerns?
5. **Tests** - Are new behaviors tested? Are edge cases covered?

## Step 4: Classify Findings by Tier

| Tier | Criteria | Action |
|------|----------|--------|
| **Critical** | Broken logic, security holes, dead code, contract violations | Fix immediately |
| **Moderate** | Missing error handling, coverage gaps, pattern inconsistencies | Fix if straightforward, otherwise propose |
| **Low** | Style, naming, documentation, minor improvements | Report only |

### Decision Rules

**Fix it yourself if ALL of these are true:**
- The fix follows an existing pattern in the codebase
- The fix is under ~20 lines of code
- The fix doesn't change any public API or contract
- You can write a test for it (or the fix IS a test)

**Propose options if ANY of these are true:**
- Multiple valid approaches exist
- The fix changes a public interface or data contract
- The fix touches protected paths (`docs/00_foundations/`, `docs/01_governance/`)
- The fix requires a design decision the builder should make

**Escalate if:**
- The issue requires architectural changes across multiple modules
- The issue affects governance or constitution
- You're unsure whether the fix is correct

## Step 5: Fix and Verify

For each fix applied:
1. Make the change
2. Run targeted tests for the affected module
3. Run `pytest runtime/tests -q` to check for regressions
4. Commit with a clear message: `Fix review findings: <summary>`

## Step 6: Report

Structure your report as:

```
Branch: <branch-name>
Commits: <start-sha>..<end-sha>
Test Results:
- Targeted: <result>
- Full/expanded: <result>
What Was Done:
- <concise bullet list>
What Remains:
- <open items or "None">
```

If needed, include a short `Verdict` line above this block, but keep the five
core sections in this exact order for inter-agent consistency.
