---
name: review-build
description: Review a build from another agent using the tiered review-fix-report protocol. Fixes obvious issues in-place, proposes options for judgment calls, escalates architectural concerns.
---

# Review Build

Review a build from another agent using the tiered review-fix-report protocol.
Fix obvious issues in-place rather than just reporting them.

Default target:
- the current worktree branch against its merge-base with `main`

Use this skill for:
- post-build review before `close_build.py`
- review of a feature/build branch from another agent
- review-and-fix passes where the builder already produced code and tests

Close-build integration:
- `python3 scripts/workflow/close_build.py` now writes a review brief under `.git/lifeos/reviews/<branch>.md`
- treat that brief as the starting checklist, not the end of the review

## Inputs

The user will provide one or more of:
- A branch name (e.g., `build/master-plan-v1-1-canonicalization`)
- A commit range (e.g., `e7d7ab8..d848d1f`)
- A build summary (pasted from the building agent)
- A PR number

If only a branch name is given, diff against the branch's merge-base with `main`.

## Step 1: Establish Shared Truth

```bash
BASE=$(git merge-base main HEAD)
git log --oneline "$BASE"..HEAD
git diff --stat "$BASE"..HEAD
git diff "$BASE"..HEAD
```

Read the changed files. Understand what was built, not just what changed.

For large diffs:

```bash
git diff --name-only "$BASE"..HEAD
git diff "$BASE"..HEAD -- runtime/
git diff "$BASE"..HEAD -- scripts/ config/ docs/
```

## Step 2: Run Pre-Existing Baseline

```bash
# Check if failures exist BEFORE this build
git stash && git checkout <base-commit> --quiet
pytest runtime/tests -q 2>&1 | tail -5
git checkout <branch> --quiet && git stash pop 2>/dev/null
```

This establishes which test failures are pre-existing vs introduced.

If checkout/stash churn is risky, skip this step and use the current branch as the
baseline. Record that assumption in the report.

## Step 3: Run the Review Verification Stack

Always run the light stack first:

```bash
python3 scripts/workflow/quality_gate.py check --scope changed --json
git diff --check
```

If runtime Python changed:

```bash
/mnt/c/Users/cabra/Projects/LifeOS/.venv/bin/python -m ruff check runtime
/mnt/c/Users/cabra/Projects/LifeOS/.venv/bin/python -m ruff format --check runtime
```

If the router points to tests, run those before a broad suite:

```bash
scripts/workflow/test_router.sh <changed-file>...
```

Then run the returned commands. Only run the broader suite if the changed surface
needs it.

## Step 4: Review Each Change

For each file changed, assess:

1. **Correctness** - Does the code do what it claims?
2. **Completeness** - Are there missing cases, uncovered paths?
3. **Consistency** - Does it follow existing codebase patterns?
4. **Safety** - Error handling, validation, security concerns?
5. **Tests** - Are new behaviors tested? Are edge cases covered?

Focus first on:
- import changes that can introduce circular dependencies
- fail-closed logic changed to fail-open behavior
- hook/build workflow changes that can block closure
- test edits that only silence failures instead of checking behavior
- broad lint suppressions on executable code

## Step 5: Classify Findings by Tier

| Tier | Criteria | Action |
|------|----------|--------|
| **Critical** | Broken logic, circular imports, security holes, dead code, contract violations | Fix immediately |
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

## Step 6: Fix and Verify

For each fix applied:
1. Make the change
2. Run targeted tests for the affected module
3. Re-run the changed-scope quality gate
4. Run `pytest runtime/tests -q` if runtime behavior changed materially
5. Commit with a clear message: `Fix review findings: <summary>`

If a review fix introduces a new import edge, always run at least one import-time
or collection-time verification command before moving on.

## Step 7: Report

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

When no findings remain, say so explicitly:
- `Findings: none after review fixes`

When assumptions remain, keep them short and concrete:
- `Assumptions: full runtime suite not re-run after doc-only fix`
