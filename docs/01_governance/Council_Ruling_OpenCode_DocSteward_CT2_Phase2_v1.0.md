# Council Ruling: OpenCode Document Steward CT-2 Phase 2 — APPROVED

**Ruling**: GO (Activation-Canonical)  
**Date**: 2026-01-07 (Australia/Sydney)  
**Artefacts Under Review**: Bundle_OpenCode_Steward_Hardening_CT2_v1.4.2.zip  
**Trigger Class**: CT-2 (Tier Activation) + Governance Protocol

---

## Council Composition

| Role | Verdict |
|------|---------|
| Chair | GO |

---

## Scope Summary

**Phase 2: Human-Triggered Document Steward**

| Aspect | Constraint |
|--------|------------|
| Trigger | Human invokes `scripts/opencode_ci_runner.py --task "<JSON>"` |
| Input | JSON-only (free-text rejected) |
| Git Operations | Stage-only; commit/push blocked |
| Allowlist | `docs/**`, `artifacts/review_packets/**` (create-only), `artifacts/evidence/**` (read-only) |
| Denylist | `docs/00_foundations/**` (override required), `config/**`, `scripts/**`, `**/*.py`, `GEMINI.md` |
| Packet Requirement | ANY delete, >1 file, override, or governance touch |

---

## Waivers (Accepted)

| Waiver | Rationale | Status |
|--------|-----------|--------|
| Windows Kill Switch | `taskkill` only; cross-platform deferred to P3 | ACCEPTED |
| Destructive Rollback | `git reset --hard` is acceptable fail-closed behavior | ACCEPTED |
| Concurrency Prohibited | No lockfile in Phase 2; single-run only | ACCEPTED |

---

## Activation Status

The following are now **canonical and active**:

- **CCP**: `artifacts/review_packets/CCP_OpenCode_Steward_Activation_CT2_Phase2.md`
- **Runner**: `scripts/opencode_ci_runner.py`
- **Harness**: `scripts/run_certification_tests.py`
- **Certification Report**: `artifacts/evidence/opencode_steward_certification/CERTIFICATION_REPORT_v1_4.json`
- **Hash Manifest**: `artifacts/evidence/opencode_steward_certification/HASH_MANIFEST_v1.4.2.json`

---

## Evidence

- **Bundle**: `artifacts/bundles/Bundle_OpenCode_Steward_Hardening_CT2_v1.4.2.zip`
- **Certification**: 13/13 PASS (v1.4 suite)
- **Manifest SHA-256 (CCP)**: `072705d8306c2747f6901a2c915eaecd37dc0ad56ae5745f38dff5c8ab762e38`

---

**END OF RULING**
