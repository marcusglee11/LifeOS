# Tier-2.5 Activation Conditions Checklist v1.0

**Status**: Active  
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0  
**Implements**: Tier2.5_Unified_Fix_Plan_v1.0 (F3)  
**Effective**: 2026-01-02

---

## 1. Purpose

This checklist defines the mandatory conditions that must be satisfied before Tier-2.5 (Semi-Autonomous Development Layer) operations may commence.

Tier-2.5 activation is not a one-time gate but a **continuous assertion**. If any condition becomes false during operation, Tier-2.5 must deactivate per F4 (Deactivation & Rollback Conditions).

---

## 2. Activation Conditions

All conditions must be TRUE for Tier-2.5 to be active.

### 2.1 Runtime Integrity

| ID | Condition | Verification Method |
|----|-----------|---------------------|
| A1 | Tier-2 test suite passes at 100% | `pytest runtime/tests -q` returns 0 failures |
| A2 | No unresolved envelope violations in last test run | Test output contains no `EnvelopeViolation` exceptions |
| A3 | Anti-Failure invariants hold | Test output contains no `AntiFailureViolation` exceptions |

### 2.2 Governance Integrity

| ID | Condition | Verification Method |
|----|-----------|---------------------|
| B1 | Constitution v2.0 is active | `docs/00_foundations/LifeOS_Constitution_v2.0.md` exists and is current |
| B2 | Governance Protocol v1.0 is active | `docs/01_governance/Governance_Protocol_v1.0.md` exists |
| B3 | Document Steward Protocol v1.0 is active | `docs/01_governance/Document_Steward_Protocol_v1.0.md` exists |
| B4 | F4 (Deactivation Conditions) is documented | This companion doc exists |
| B5 | F7 (Runtime↔Antigrav Protocol) is documented | Protocol spec exists |

### 2.3 Operational Readiness

| ID | Condition | Verification Method |
|----|-----------|---------------------|
| C1 | Rollback procedure documented and tested | Rollback to last known-good commit is possible |
| C2 | Corpus generation functional | `python docs/scripts/generate_corpus.py` succeeds |
| C3 | Git repository in clean state | `git status` shows no uncommitted governance changes |

### 2.4 Authorization

| ID | Condition | Verification Method |
|----|-----------|---------------------|
| D1 | CEO has approved Tier-2.5 activation | Logged in Council ruling or explicit CEO statement |
| D2 | Council review of Tier-2 completion recorded | Tier2_Completion_Tier2.5_Activation_Ruling exists |

---

## 3. Activation Protocol

When all conditions in Section 2 are TRUE:

1. **Verify** - Run verification methods for A1-A3 (runtime tests)
2. **Assert** - Confirm B1-B5 docs exist
3. **Confirm** - CEO confirms activation (may be implicit if Council ruling exists)
4. **Log** - Record activation timestamp in commit message or governance log
5. **Operate** - Tier-2.5 missions may proceed under F7 protocol

---

## 4. Continuous Assertion

Tier-2.5 is not "activated once and forgotten." The following must remain true:

- **Before each Tier-2.5 mission**: A1 (tests pass) must be verified
- **After each Tier-2.5 mission**: If any condition becomes FALSE, deactivate per F4
- **Daily**: C3 (clean git state) should be verified before autonomous commits

---

## 5. Current Status

As of 2026-01-02:

| Condition | Status | Notes |
|-----------|--------|-------|
| A1-A3 | ✓ PASS | 316 tests passing |
| B1-B3 | ✓ PASS | Governance docs exist |
| B4-B5 | ✓ PASS | F4, F7 now documented |
| C1-C3 | ✓ PASS | Operational infrastructure functional |
| D1-D2 | ✓ PASS | Council ruling exists, CEO approved |

**Tier-2.5 Status: ACTIVE**

---

**END OF DOCUMENT**
