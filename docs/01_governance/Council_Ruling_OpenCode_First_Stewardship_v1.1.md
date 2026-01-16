# Council Ruling: OpenCode-First Doc Stewardship Policy (Phase 2) — v1.1

**Ruling**: PASS (GO)
**Date**: 2026-01-07
**Subject**: Adoption of "OpenCode-First Doc Stewardship" Routing Mandate
**Related Policy**: [OpenCode_First_Stewardship_Policy_v1.1.md](./OpenCode_First_Stewardship_Policy_v1.1.md)
**Related Protocol**: [F7_Runtime_Antigrav_Mission_Protocol_v1.0.md](../03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md) (Section 7.3)

---

## Decision Summary

The Council approves the adoption of the **OpenCode-First Doc Stewardship** policy (v1.1). This mandate, hardened for mechanical auditability, requires Antigravity to route all documentation changes within the authorized CT-2 Phase 2 envelope through the OpenCode steward and its associated audit gate.

## Rationale

- **Mechanical Auditability**: Eliminates ambiguity in documentation routing via explicit envelope checks.
- **Evidence Quality**: Ensures all eligible changes produce standardized, no-ellipsis evidence bundles.
- **Governance Integrity**: Explicitly separates protected surfaces (councils-only) from steward surfaces.

## Scope & Implementation

- **Rule**: Antigravity MUST route in-envelope doc changes through `scripts/opencode_ci_runner.py`.
- **Demo Validated**: Demonstration run on `docs/08_manuals/Governance_Runtime_Manual_v1.0.md` passed with a complete evidence bundle.
- **Mechanical Inputs**: Authoritative spec SHAs recorded in the Implementation Report.

---

## Sign-Off

**Chair (Architect/Head of Dev/Head of Testing)** — APPROVED FOR ACTIVATION
**Date**: 2026-01-07

---

**END OF RULING**
