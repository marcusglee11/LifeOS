---
description: Review a build from another agent using the tiered review-fix-report protocol. Fixes obvious issues in-place, proposes options for judgment calls, escalates architectural concerns.
---

Invoke the lifeos-workflow:review-build skill and follow it exactly as presented to you.

The user may provide a branch name, commit range, build summary, or PR number. If none is provided, ask for the branch or commits to review.

Output must end in compact sections in this order:
1. Branch
2. Commits
3. Test Results
4. What Was Done
5. What Remains
