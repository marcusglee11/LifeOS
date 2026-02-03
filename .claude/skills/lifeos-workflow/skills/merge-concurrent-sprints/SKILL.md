---
name: merge-concurrent-sprints
description: Use when multiple feature branches have diverged concurrently, creating complex merge scenarios with risk of lost work or conflicts. Symptoms include 5+ unmerged branches, unclear branch relationships, stashes accumulating (3+), or uncertainty about which work is canonical. Guides through safe merge strategies with pre-merge inventory, integration testing, and cleanup.
---

# Merge Concurrent Sprints

## Overview

Safely merge multiple divergent feature branches developed in parallel without losing work or creating conflicts. This skill provides structured workflows for auditing branch state, selecting appropriate merge strategies, and maintaining code quality through the integration process.

## When to Use

**Symptoms checklist:**
- 5+ active feature branches unmerged to main
- Branches >1 week old with divergent histories
- Multiple stashes accumulating (3+)
- Unclear which branch contains "latest" work
- Test counts differ significantly between branches
- Team members asking "which branch should I base on?"
- Protected paths potentially modified across branches (`docs/00_foundations/`, `docs/01_governance/`)

**When NOT to use:**
- Single feature branch with clean history
- Branches with clear parent-child relationships already established
- Simple fast-forward merges with no conflicts

## Pre-Merge Inventory

**CRITICAL: Run this BEFORE attempting any merges.**

### Step 1: Run Branch Audit Script

```bash
bash .claude/skills/lifeos-workflow/skills/merge-concurrent-sprints/branch-audit.sh
```

This generates:
- Branch commit counts (+ahead/-behind main)
- Last commit timestamps
- Stash inventory with ages
- Test status per branch (LifeOS-specific)
- Current LifeOS state (from `docs/11_admin/LIFEOS_STATE.md`)

### Step 2: Manual Branch Relationship Analysis

```bash
# Find common ancestors
for branch in $(git branch | sed 's/\*//'); do
  ancestor=$(git merge-base main $branch)
  echo "$branch ancestor: $ancestor"
done

# Check for duplicate work (similar commit messages)
git log --all --oneline --graph --decorate
```

### Step 3: Identify Protected Path Conflicts

```bash
# Check if any branch modified protected paths
for branch in $(git branch | sed 's/\*//'); do
  protected=$(git diff main..$branch --name-only | grep -E '^docs/0[01]_' || echo "none")
  echo "$branch protected changes: $protected"
done
```

### Step 4: Document Findings

Create a merge plan document with:
- Branch dependency graph
- Merge strategy selection (see Decision Flowchart below)
- Conflict risk assessment
- Protected path approval status

## Decision Flowchart: Select Merge Strategy

```
START: Multiple branches to merge
│
├─ Do branches have linear dependency? (A depends on B depends on C)
│  YES → Use SEQUENTIAL MERGE
│  NO  → Continue
│
├─ Does work overlap or conflict?
│  YES → Use CHERRY-PICK strategy
│  NO  → Continue
│
├─ Do all branches pass tests independently?
│  YES → Use INTEGRATION BRANCH
│  NO  → FIX TESTS FIRST (do not proceed)
```

## Merge Strategies

### Strategy 1: Sequential Merge (Linear Dependencies)

**Use when:** Branch A depends on B, B depends on C (chain relationship).

```bash
git checkout main
git merge --no-ff feature/A
pytest runtime/tests -q  # Verify
git merge --no-ff feature/B
pytest runtime/tests -q  # Verify
git merge --no-ff feature/C
pytest runtime/tests -q  # Final verification
```

**Why `--no-ff`:** Preserves merge audit trail even for fast-forward-eligible merges.

### Strategy 2: Integration Branch (Parallel Work)

**Use when:** Multiple branches developed concurrently with independent work.

```bash
git checkout -b integration/phase-X main
git merge --no-ff feature/A
pytest runtime/tests -q  # Verify
git merge --no-ff feature/B
pytest runtime/tests -q  # Verify
git merge --no-ff feature/C
pytest runtime/tests -q  # Integration testing
git checkout main
git merge --no-ff integration/phase-X
pytest runtime/tests -q  # Final verification
```

**Tag the integration point:**
```bash
git tag phase-X-integration-complete
```

### Strategy 3: Cherry-Pick (Overlapping Work)

**Use when:** Multiple branches have duplicate or conflicting implementations of same feature.

```bash
# Identify unique valuable commits from each branch
git log main..feature/A --oneline  # Review A's unique work
git log main..feature/B --oneline  # Review B's unique work

# Cherry-pick only unique commits (prefer newer implementation)
git checkout main
git cherry-pick <commit-hash-from-A>
pytest runtime/tests -q  # Verify
git cherry-pick <commit-hash-from-B>
pytest runtime/tests -q  # Verify
```

**Conflict resolution:** Prefer the newer or more complete implementation.

## Execution Checklist

### Before Merge (LifeOS-Specific)

- [ ] All target branches have clean working trees (`git status` clean on each)
- [ ] Test suite passes on each branch independently (`pytest runtime/tests -q`)
- [ ] Common ancestor identified for each branch pair
- [ ] Stashes reviewed and either committed to WIP branch or dropped (NO stashes >24 hours)
- [ ] State documentation reviewed (`docs/11_admin/LIFEOS_STATE.md` - know what's in flight)
- [ ] Protected paths checked (`docs/00_foundations/`, `docs/01_governance/` - require approval if modified)
- [ ] Branch audit script executed and results documented
- [ ] Merge strategy selected based on decision flowchart

### During Merge

- [ ] Merge with `--no-ff` for audit trail (ALWAYS)
- [ ] Run `pytest runtime/tests -q` after EACH merge step (not just at end)
- [ ] Document merge commit with phase summary (`git commit --amend` if needed)
- [ ] Handle conflicts by preferring newer implementation
- [ ] If protected paths conflict, STOP and get Council approval
- [ ] Tag integration points for rollback capability

### After Merge

- [ ] Full test suite passes on main (`pytest runtime/tests -q` shows all green)
- [ ] Tag merge point (`git tag phase-X-integration-complete`)
- [ ] Archive or delete merged branches (see Post-Merge Cleanup)
- [ ] Update `docs/11_admin/LIFEOS_STATE.md` ("Current Focus", "Recent Wins")
- [ ] Update `docs/11_admin/AUTONOMY_STATUS.md` if capabilities changed
- [ ] Clean up all stashes related to merged work
- [ ] Document any merge conflicts and resolutions for future reference

## Post-Merge Cleanup

### Archive Merged Branches

```bash
# Tag before deleting (preserves history)
git tag archive/phase-X-feature-name feature/branch-name
git branch -d feature/branch-name  # Local
git push origin --delete feature/branch-name  # Remote (if applicable)
```

### Review Unmerged Branches

For each remaining branch, decide:
1. **Already in main?** → Delete (`git branch -d` will verify)
2. **Unique valuable work?** → Cherry-pick or create new PR
3. **Obsolete?** → Archive with tag and delete

```bash
# Check if branch work is in main
git log main..feature/branch-name --oneline
# If empty, safe to delete
```

### Clean Stashes (CRITICAL)

```bash
# Review all stashes
git stash list

# Drop stashes related to merged work
git stash drop stash@{N}

# NEVER keep stashes >24 hours - commit to WIP branch instead:
git stash pop
git checkout -b wip/descriptive-name
git add -A
git commit -m "WIP: <description>"
```

### Update LifeOS Documentation

**Required updates:**
- `docs/11_admin/LIFEOS_STATE.md`:
  - Update "Current Focus" section
  - Add merged phase to "Recent Wins"
  - Clear completed items from "Active WIP"
- `docs/11_admin/AUTONOMY_STATUS.md`:
  - Update capability matrix if new features added
  - Update baseline references if canonical implementation changed
- Verify no protected paths modified without approval:
  - `docs/00_foundations/` (Constitution, architecture)
  - `docs/01_governance/` (Protocols, council rulings)

## Common Mistakes

| Mistake | Symptom | Fix |
|---------|---------|-----|
| **Stash as storage** | Stashes accumulate >1 week | Commit stash to WIP branch: `git checkout -b wip/name && git stash pop && git commit` |
| **No integration testing** | Tests pass on branches, fail on main | Use integration branch for pre-merge testing (Strategy 2) |
| **Cherry-pick dependencies** | Cherry-pick fails with conflicts | Merge entire branch or rebase first, don't cherry-pick dependent commits |
| **Unclear branch state** | "Which branch is latest?" | Run branch audit script, check commit counts and timestamps |
| **No merge audit trail** | Fast-forward merges hide integration points | ALWAYS use `--no-ff` flag |
| **Skipping cleanup** | Branches accumulate indefinitely | Archive/delete within 1 week of merge |
| **Protected path conflicts** | Constitution/governance changes conflict | STOP - get Council approval before merging |
| **Test after all merges** | Integration breaks but unclear which merge caused it | Test after EACH merge step, not just at end |

## Prevention (Going Forward)

**Workflow to prevent concurrent sprint complexity:**

### 1. Integration Branch Per Phase

```bash
git checkout -b phase-X/integration main
# All phase-X subtasks merge here FIRST, then to main
```

### 2. Frequent Integration

- Merge to integration branch after each sub-task (5-10 commits max)
- Merge integration to main after each phase (weekly max)
- NEVER let branches diverge >1 week without integration

### 3. Branch Naming Convention

```
phase-X/integration         # Main integration branch for phase
phase-X/subtask-name       # Feature branches for subtasks
wip/descriptive-name       # Work-in-progress (replaces stashes)
```

### 4. No Stashes >24 Hours

**Instead of stashing:**
```bash
git checkout -b wip/current-work
git add -A
git commit -m "WIP: <what you're working on>"
# Resume later: git checkout wip/current-work
```

### 5. ACTIVE_BRANCHES.md Tracking (Optional)

Create `docs/11_admin/ACTIVE_BRANCHES.md`:
```markdown
# Active Branches

## Integration Branches
- `phase-5/integration` - Phase 5 main integration (merges to main weekly)

## Feature Branches
- `phase-5/coo-metrics` - COO metrics dashboard (merges to phase-5/integration)
- `phase-5/governance-hooks` - Governance validation hooks (merges to phase-5/integration)

## WIP Branches
- `wip/autonomy-testing` - Autonomy baseline testing (personal, will merge or discard)

## Archive (Merged)
- `phase-4/integration` - Merged to main 2026-02-03 (tag: phase-4-complete)
```

Update on create/merge/archive events.

## Quick Reference

```bash
# Pre-flight: Audit current state
bash .claude/skills/lifeos-workflow/skills/merge-concurrent-sprints/branch-audit.sh

# Sequential merge (linear dependencies)
git checkout main && git merge --no-ff A && pytest runtime/tests -q

# Integration branch (parallel work)
git checkout -b integration/phase-X main
git merge --no-ff A && git merge --no-ff B && pytest runtime/tests -q
git checkout main && git merge --no-ff integration/phase-X

# Cherry-pick (overlapping work)
git log main..feature/A --oneline  # Review
git cherry-pick <hash> && pytest runtime/tests -q

# Post-merge cleanup
git tag archive/phase-X-name feature/branch
git branch -d feature/branch
git stash drop stash@{N}

# Update LifeOS state
vim docs/11_admin/LIFEOS_STATE.md  # Current Focus, Recent Wins
```

## Success Indicators

After completing a concurrent sprint merge, you should have:

✅ All target work merged to main
✅ Full test suite passing (`pytest runtime/tests -q`)
✅ No stashes remaining from merged work
✅ Merged branches archived with tags and deleted
✅ Integration point tagged (e.g., `phase-X-integration-complete`)
✅ LifeOS state documentation updated
✅ Protected paths either unchanged or approved by Council
✅ Clear audit trail (all merges used `--no-ff`)

---

**Remember:** The goal is not just to get code into main, but to do so with full confidence that nothing was lost, tests pass, and the integration is documented for future reference. When in doubt, use an integration branch and test thoroughly.
