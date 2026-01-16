# Emergency Declaration Protocol v1.0

<!-- LIFEOS_TODO[P1][area: docs/02_protocols/Emergency_Declaration_Protocol_v1.0.md][exit: status change to ACTIVE + DAP validate] Finalize Emergency_Declaration_Protocol v1.0: Remove WIP/Provisional markers -->

**Status**: WIP (Non-Canonical)
**Authority**: LifeOS Constitution v2.0 → Council Protocol v1.2
**Effective**: 2026-01-07 (Provisional)

---

## 1. Purpose

Defines the procedure for declaring and operating under emergency conditions that permit CEO override of Council Protocol invariants.

---

## 2. Emergency Trigger Conditions

An emergency MAY be declared when **any** of:
1. **Time-Critical**: Decision required before normal council cycle can complete
2. **Infrastructure Failure**: Council model(s) unavailable
3. **Cascading Risk**: Delay would cause escalating harm
4. **External Deadline**: Contractual or regulatory constraint

---

## 3. Declaration Procedure

### 3.1 Declaration Format

```yaml
emergency_declaration:
  id: "EMERG_YYYYMMDD_<slug>"
  declared_by: "CEO"
  declared_at: "<ISO8601 timestamp>"
  trigger_condition: "<one of: time_critical|infrastructure|cascading|external>"
  justification: "<brief description>"
  scope: "<what invariants are being overridden>"
  expected_duration: "<hours or 'until resolved'>"
  auto_revert: true|false
```

### 3.2 Recording
- Declaration MUST be recorded in `artifacts/emergencies/`
- CSO is automatically notified
- Council Run Log must include `compliance_status: "non-compliant-ceo-authorized"`

---

## 4. Operating Under Emergency

During declared emergency:
- CEO may authorize Council runs without model independence
- Bootstrap mode limits are suspended
- Normal waiver justification requirements relaxed

**Preserved invariants** (never suspended):
- CEO Supremacy
- Audit Completeness
- Amendment logging

---

## 5. Resolution

### 5.1 Mandatory Follow-Up
Within 48 hours of emergency resolution:
- [ ] Compliant re-run scheduled (if council decision)
- [ ] Emergency record closed with outcome
- [ ] CSO review completed

### 5.2 Auto-Revert
If `auto_revert: true`, emergency expires after `expected_duration` and normal governance resumes automatically.

---

## 6. Audit Trail

| Event | Record Location |
|-------|-----------------|
| Declaration | `artifacts/emergencies/<id>.yaml` |
| Council runs during | Council Run Log `notes.emergency_id` |
| Resolution | Same file, `resolution` block added |

---

**END OF PROTOCOL**
