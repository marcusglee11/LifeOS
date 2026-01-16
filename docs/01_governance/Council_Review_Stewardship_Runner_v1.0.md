# Council_Review_Stewardship_Runner_v1.0

**Date**: 2026-01-02
**Subject**: Stewardship Runner Fix Pack v0.5 Delta
**Status**: APPROVED

---

## 1. Council P1 Conditions: SATISFIED

| Condition | Required | Delivered | Verification |
|-----------|----------|-----------|--------------|
| **P1-A** | Dirty-during-run check | `run_commit` re-checks `git status` | AT-14 ✅ |
| **P1-B** | Log determinism | ISO8601 UTC + sorted lists | AT-15 ✅ |
| **P1-C** | Platform policy doc | `PLATFORM_POLICY.md` created | Manual ✅ |
| **P1-D** | CLI commit control | `--commit` required, default dry-run | AT-16, 17, 18 ✅ |
| **P1-E** | Log retention doc | `LOG_RETENTION.md` created | Manual ✅ |

## 2. P2 Hardenings: COMPLETE

| Item | Status |
|------|--------|
| **P2-A Empty paths** | Validation added |
| **P2-B URL-encoded** | `%` rejected, AT-13 updated |
| **P2-C Error returns** | Original path returned |

---

## 3. Council Verdict

**Decision**: All conditions met.

| Final Status | Verdict |
|--------------|---------|
| **D1 — Operational readiness** | **APPROVED** for agent-triggered runs |
| **D2 — Canonical surface scoping** | **APPROVED** (v1.0) |
| **D3 — Fail-closed semantics** | **APPROVED** |

### Clearances
The Stewardship Runner is now cleared for:
1. Human-triggered runs (was already approved)
2. **Agent-triggered runs** (newly approved)
3. CI integration with `--dry-run` default

---

## 4. Operating Rules

The Stewardship Runner is now the **authoritative gating mechanism** for stewardship operations.

1.  **Clean Start**: Stewardship is performed in a clean worktree.
2.  **Mandatory Run**: After edits, steward must run Steward Runner (dry-run unless explicitly authorised).
3.  **Green Gate**: Steward must fix until green (or escalate if it’s a policy decision).
4.  **Reporting**: Steward reports back with:
    -   `run-id`
    -   pass/fail gate
    -   changed files
    -   JSONL tail (last 5 lines)
