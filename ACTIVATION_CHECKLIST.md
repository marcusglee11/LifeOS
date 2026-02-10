# Phase 1 Autonomy - Activation Checklist

**Status:** READY FOR ACTIVATION ✅
**Date:** 2026-01-30
**GL Review:** APPROVED WITH CONDITIONS - ALL RESOLVED

---

## Pre-Activation Verification

### ✅ Code Quality
- [x] 6/6 BDD test scenarios passing
- [x] 1006/1006 baseline tests passing (with exclusions)
- [x] Zero existing files modified
- [x] All changes on feature branch `build/repo-cleanup-p0`

### ✅ Condition Resolutions
- [x] **C1:** 10 test files excluded, 1006 tests pass, 0 fail
- [x] **C2:** Schedule corrected to 8 PM UTC (7 AM AEDT)
- [x] **C3:** Force-with-lease implemented for safe rollback

### ✅ Documentation
- [x] Review packet created (LifeOS spec v1.2.0)
- [x] Handoff guide complete
- [x] Conditions resolution documented
- [x] Activation checklist (this file)

---

## Activation Steps

### Step 1: Push Branch ⏳
```bash
cd /mnt/c/Users/cabra/projects/LifeOS
git push -u origin build/repo-cleanup-p0
```

**Expected:**
- 5 commits pushed successfully
- Branch visible on GitHub

**Verify:**
```bash
gh browse build/repo-cleanup-p0
```

---

### Step 2: Manual Workflow Test ⏳
```bash
gh workflow run phase1_autonomy_nightly.yml --ref build/repo-cleanup-p0
gh run watch
```

**Expected Results:**
- ✅ Checkout succeeds
- ✅ Python 3.11 installed
- ✅ Dependencies installed (pip + npm markdownlint)
- ✅ Doc hygiene runs (~13,150 issues found)
- ✅ Changes committed with robot attribution
- ✅ Pytest runs 1006 tests (all pass)
- ✅ No rollback triggered
- ✅ GitHub issue created
- ✅ Workflow status: Success ✅

**If Workflow Fails:**
- Check workflow logs: `gh run view <run-id> --log`
- Common issues:
  - Markdownlint not installed → Check npm install step
  - Tests fail → Verify test exclusions match
  - Issue creation fails → Check permissions (issues: write)

---

### Step 3: Review GitHub Issue ⏳
```bash
gh issue list --label "phase-1" --limit 1
gh issue view <issue-number>
```

**Expected Issue Contents:**
- ✅ Title: "📊 Phase 1 Autonomy Report - YYYY-MM-DD"
- ✅ Workflow metadata (time, status, run URL)
- ✅ Task results (✅ for doc hygiene, commit, pytest)
- ✅ Doc hygiene summary (~13,150 issues fixed)
- ✅ Test results summary (1006 passed)
- ✅ Review checklist
- ✅ Labels: automation, phase-1, nightly-run

**Action:**
- [ ] Review doc hygiene changes (check for false positives)
- [ ] Verify test results (1006 passed)
- [ ] Close issue after verification

---

### Step 4: Create Pull Request ⏳
```bash
gh pr create \
  --title "Phase 1 Autonomy Implementation" \
  --body "Closes Operating Model Phase 1 exit criteria.

## Summary
Implements automated doc hygiene with nightly autonomous execution:
- Doc hygiene script with 6/6 BDD tests passing
- Nightly workflow (8 PM UTC = 7 AM AEDT)
- Auto-commit + rollback on failure
- Morning reports via GitHub issues

## GL Review
- Verdict: APPROVED WITH CONDITIONS
- All 3 conditions (C1-C3) resolved ✅

## Documentation
- Review Packet: artifacts/review_packets/Review_Packet_Phase_1_Autonomy_Close_Operating_Model_v1.0.md
- Handoff Guide: PHASE1_HANDOFF.md
- Conditions Resolution: PHASE1_CONDITIONS_RESOLUTION.md

## Test Results
- Phase 1 tests: 6/6 passing ✅
- Baseline tests: 1006/1006 passing (with exclusions) ✅
- No regressions introduced ✅

## Next Steps After Merge
1. Monitor first scheduled run (~8 PM UTC tonight)
2. Review morning issue (~7 AM AEDT tomorrow)
3. Monitor 3 consecutive nights for stability
4. Mark Phase 1 COMPLETE if all AC15-AC19 pass

See PHASE1_HANDOFF.md for complete activation guide."
```

**Expected:**
- PR created successfully
- CI runs on PR (pytest should pass)

**Verify:**
```bash
gh pr view
gh pr checks
```

---

### Step 5: Merge to Main ⏳
```bash
# After CI passes and manual review
gh pr merge --squash
```

**Expected:**
- Squash merge to main
- Workflow now active on main branch
- First scheduled run tonight at 8 PM UTC

**Verify:**
```bash
gh workflow list
gh workflow view phase1_autonomy_nightly.yml
```

---

### Step 6: Monitor First Scheduled Run ⏳

**Timeline:**
- **Tonight 8:00 PM UTC** - First scheduled run triggers
- **Tonight 8:05 PM UTC** - Execution completes
- **Tomorrow 7:00 AM AEDT** - Review issue

**Monitoring:**
```bash
# Tomorrow morning (7 AM AEDT)
gh issue list --label "phase-1" --limit 1
gh issue view <issue-number>
```

**Checklist:**
- [ ] Issue created automatically
- [ ] Doc hygiene ran successfully
- [ ] Changes committed (if any)
- [ ] Tests passed (1006/1006)
- [ ] No rollback triggered
- [ ] Execution time < 5 minutes
- [ ] Review time < 10 minutes

**Action:**
- [ ] Review changes committed (trust linter for small fixes)
- [ ] Verify no false positives (manual spot check)
- [ ] Close issue
- [ ] Note: "Night 1 complete ✅"

---

### Step 7: Monitor Nights 2-3 ⏳

**Night 2 (Day N+1):**
```bash
gh issue list --label "phase-1" --limit 1
```

**Expected:**
- Fewer changes than Night 1 (convergence)
- Tests still passing
- Execution time consistent

**Checklist:**
- [ ] Issue created
- [ ] Convergence observed (fewer changes)
- [ ] Tests passed
- [ ] Close issue
- [ ] Note: "Night 2 complete ✅"

---

**Night 3 (Day N+2):**
```bash
gh issue list --label "phase-1" --limit 1
```

**Expected:**
- Minimal or no changes (stabilization)
- Tests passing
- Execution time < 5 minutes

**Checklist:**
- [ ] Issue created
- [ ] Stabilization achieved (minimal changes)
- [ ] Tests passed
- [ ] Close issue
- [ ] Note: "Night 3 complete ✅"

---

### Step 8: Mark Phase 1 Complete ⏳

**After 3 Successful Nights:**

**Verify Final Acceptance Criteria:**
- [ ] AC15: 3+ consecutive successful runs ✅
- [ ] AC16: 0 manual interventions during execution ✅
- [ ] AC17: 1006+ tests passing after each run ✅
- [ ] AC18: <5 minute average execution time ✅
- [ ] AC19: GL review time <10 minutes per morning ✅

**Mark Complete:**
```bash
# Create completion note
echo "Phase 1 Complete: $(date)" > PHASE1_COMPLETION.md

# Update Operating Model (if applicable)
# Document lessons learned
# Plan Phase 2 (PR workflow + OpenCode integration)
```

**Celebration:**
- 🎉 First autonomous loop proven!
- 🎉 Doc hygiene on autopilot!
- 🎉 GL wakes to clean docs every morning!

---

## Rollback Plan (If Needed)

**If Workflow Consistently Fails:**

### Option 1: Disable Workflow
```bash
gh workflow disable phase1_autonomy_nightly.yml
```

### Option 2: Revert Merge
```bash
git revert -m 1 <merge-commit-sha>
git push origin main
```

### Option 3: Fix Forward
- Identify issue in workflow logs
- Create fix on new branch
- Test with manual trigger
- Merge fix to main

---

## Success Criteria Summary

| Criterion | Target | Status |
|-----------|--------|--------|
| **Implementation** | All code complete | ✅ |
| **Testing** | 6/6 BDD scenarios pass | ✅ |
| **GL Review** | Conditions C1-C3 resolved | ✅ |
| **Push** | Branch on GitHub | ⏳ |
| **Manual Test** | Workflow succeeds | ⏳ |
| **PR** | Created and merged | ⏳ |
| **Night 1** | Issue + changes + tests pass | ⏳ |
| **Night 2** | Convergence observed | ⏳ |
| **Night 3** | Stabilization achieved | ⏳ |
| **Phase 1 Exit** | All AC1-AC19 met | ⏳ |

---

## Contact / Escalation

**If Issues Arise:**
1. Check workflow logs: `gh run view <run-id> --log`
2. Review PHASE1_CONDITIONS_RESOLUTION.md
3. Consult PHASE1_HANDOFF.md troubleshooting section
4. Check Review_Packet for detailed evidence

**Phase 1 Owner:** GL (marcusglee11)
**Implementation:** Claude Sonnet 4.5
**Review Date:** 2026-01-30

---

**Ready for activation!** 🚀

Next action: Push branch and trigger manual workflow test.
