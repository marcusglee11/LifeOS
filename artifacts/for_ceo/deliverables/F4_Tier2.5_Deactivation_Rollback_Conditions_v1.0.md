# Tier-2.5 Deactivation & Rollback Conditions v1.0

**Status**: Active  
**Authority**: LifeOS Constitution v2.0 → Governance Protocol v1.0  
**Implements**: Tier2.5_Unified_Fix_Plan_v1.0 (F4)  
**Effective**: 2026-01-02

---

## 1. Purpose

This document defines the conditions that trigger automatic deactivation or suspension of Tier-2.5 operations, and the rollback procedures to restore system integrity.

Tier-2.5 operates under a **fail-closed** posture: uncertainty defaults to deactivation.

---

## 2. Automatic Deactivation Triggers

Any of the following conditions triggers immediate Tier-2.5 deactivation:

### 2.1 Runtime Failures

| ID | Trigger | Detection |
|----|---------|-----------|
| R1 | Test pass rate drops below 100% | `pytest` returns any failures |
| R2 | `EnvelopeViolation` raised during mission | Exception in mission execution |
| R3 | `AntiFailureViolation` raised during mission | Exception in mission execution |
| R4 | `AntiFailurePlanningError` raised during build | Exception in mission planning |

### 2.2 Protocol Breaches

| ID | Trigger | Detection |
|----|---------|-----------|
| P1 | Antigrav invokes non-whitelisted entrypoint | F7 protocol violation |
| P2 | Mission executed without required validation | F7 protocol violation |
| P3 | Commit made without test verification | Git hook or manual detection |
| P4 | Governance doc modified without Council review | Constitution v2.0 violation |

### 2.3 Governance Holds

| ID | Trigger | Detection |
|----|---------|-----------|
| G1 | Council issues explicit HOLD | Council ruling with HOLD status |
| G2 | CEO issues explicit STOP | CEO directive |
| G3 | Unresolved conflict between agents | Escalation without resolution |

### 2.4 Operational Failures

| ID | Trigger | Detection |
|----|---------|-----------|
| O1 | Corpus generation fails | `generate_corpus.py` returns non-zero |
| O2 | Git push fails | Network or permission error |
| O3 | Index validation fails | `index_checker.py` returns errors |

---

## 3. Deactivation Protocol

When any trigger in Section 2 fires:

### 3.1 Immediate Actions (Automatic)

1. **HALT** - Current Tier-2.5 mission stops immediately
2. **LOG** - Trigger condition logged with timestamp and context
3. **PRESERVE** - Current state preserved (no cleanup that destroys evidence)

### 3.2 Assessment Actions (Manual or Automated)

4. **DIAGNOSE** - Identify root cause of trigger
5. **CLASSIFY** - Determine severity:
   - **Transient**: Network glitch, temporary resource issue
   - **Recoverable**: Test failure from bad code, fixable
   - **Structural**: Protocol flaw, governance gap, requires redesign

### 3.3 Resolution Paths

| Severity | Resolution | Reactivation |
|----------|------------|--------------|
| Transient | Retry after delay | Auto-reactivate if F3 conditions pass |
| Recoverable | Fix issue, run tests | Manual reactivation after CEO/Council confirm |
| Structural | Fix Pack required | Full Council review before reactivation |

---

## 4. Rollback Procedures

### 4.1 Code Rollback

If Tier-2.5 mission produced bad code:

```bash
# Identify last known-good commit
git log --oneline -10

# Rollback to specific commit
git revert <bad-commit-hash>

# Verify tests pass
pytest runtime/tests -q

# Commit revert
git commit -m "rollback: Revert Tier-2.5 mission due to <trigger>"
```

### 4.2 Document Rollback

If Tier-2.5 mission produced bad governance docs:

```bash
# Restore specific file from previous commit
git checkout <good-commit-hash> -- docs/path/to/file.md

# Regenerate corpus
python docs/scripts/generate_corpus.py

# Commit restoration
git commit -m "rollback: Restore <file> due to <trigger>"
```

### 4.3 Full State Rollback

If system state is uncertain:

```bash
# Hard reset to last known-good tag
git reset --hard <tag>

# Verify integrity
pytest runtime/tests -q
python docs/scripts/generate_corpus.py

# Force push if necessary (requires CEO approval)
git push --force-with-lease
```

---

## 5. Reactivation Requirements

After deactivation, Tier-2.5 may only reactivate when:

1. **Root cause identified** and documented
2. **Fix applied** (if applicable)
3. **All F3 conditions pass** (full checklist)
4. **CEO approves** reactivation (explicit or implicit via standing authorization)

For **Structural** severity issues:
- Council review required
- Fix Pack documenting the issue and resolution required
- Extended test period may be mandated

---

## 6. Escalation

If deactivation trigger is ambiguous or contested:

1. **Escalate to CEO** with full context
2. **CEO decides** whether to:
   - Confirm deactivation
   - Override and continue (logged as exception)
   - Request Council review

Per Constitution v2.0: CEO may override any system decision at any time.

---

**END OF DOCUMENT**

