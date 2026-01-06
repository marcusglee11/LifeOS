# Council Ruling: Core TDD Design Principles v1.0 — APPROVED

**Ruling**: GO (Activation-Canonical)  
**Date**: 2026-01-06  
**Artefacts Under Review**: Bundle_TDD_Hardening_Enforcement_v1.3.zip  
**Trigger Class**: CT-2 (Governance Protocol) + CT-3 (Enforcement Scanner)

---

## Council Composition

| Role | Verdict |
|------|---------|
| Chair | GO |
| System Architect | GO |
| Governance / Alignment | GO |
| Risk / Security | GO |
| Lead Developer / QA | GO |

---

## Closed Items

1. **Envelope SSoT Split-Brain (P0)**: Resolved — Allowlist externalized to `tdd_compliance_allowlist.yaml` with integrity lock
2. **Determinism Optionality (P1)**: Resolved — "(if enabled)" removed; CI MUST run twice unconditionally
3. **Zip Path Separators (P0)**: Resolved — POSIX forward slashes in v1.2+
4. **Helper Ambiguity (P0)**: Resolved — Strict pinned-clock interface definition

---

## Non-Blocking Notes (Captured for Hygiene)

| Source | Note | Status |
|--------|------|--------|
| Architect | Filesystem I/O policy clarified | Addressed |
| Governance | Envelope Policy added as governance-controlled surface | Addressed |
| Testing | Dynamic detection (exec/eval/__import__) added | Addressed |

---

## Activation Status

The following are now **canonical and active**:

- `docs/02_protocols/Core_TDD_Design_Principles_v1.0.md` — **CANONICAL**
- `tests_doc/test_tdd_compliance.py` — Enforcement scanner
- `tests_doc/tdd_compliance_allowlist.yaml` — Governance-controlled allowlist
- `tests_doc/tdd_compliance_allowlist.lock.json` — Integrity lock

---

## Evidence

- **Bundle**: `Bundle_TDD_Hardening_Enforcement_v1.3.zip`
- **Bundle SHA256**: `75c41b2a4f9d95341a437f870e45901d612ed7d839c02f37aa2965a77107981f`
- **pytest**: 12 passed (enforcement self-tests)
- **Allowlist SHA256**: `d33c0d79695675d97dbcd2684321bf6587db6197f791be7c134ea0bbfb3f41c9`

---

**END OF RULING**
