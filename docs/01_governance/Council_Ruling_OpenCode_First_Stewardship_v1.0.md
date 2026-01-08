# Council Ruling: OpenCode-First Doc Stewardship Policy (Phase 2) — PASS (GO)

**Ruling**: PASS (GO)  
**Date**: 2026-01-07  
**Subject**: Adoption of "OpenCode-First Doc Stewardship" Routing Mandate  
**Related Policy**: [OpenCode_First_Stewardship_Policy_v1.0.md](./OpenCode_First_Stewardship_Policy_v1.0.md)  
**Related Protocol**: [F7_Runtime_Antigrav_Mission_Protocol_v1.0.md](../03_runtime/F7_Runtime_Antigrav_Mission_Protocol_v1.0.md)  

---

## Decision Summary

The Council approves the adoption of the **OpenCode-First Doc Stewardship** policy. This mandate requires Antigravity to route all documentation changes that fall within the authorized CT-2 Phase 2 envelope through the OpenCode steward and its associated audit gate.

## Rationale

- **Risk Reduction**: Eliminates ambiguity in documentation routing.
- **Auditability**: Ensures all eligible changes produce standardized, high-quality evidence bundles (v2.4+ hygiene).
- **Consistency**: Prevents drift between manual and agentic stewardship processes.

## Impact

- Antigravity MUST now route in-envelope doc changes through `scripts/opencode_ci_runner.py`.
- Any attempt to bypass this for in-envelope changes will be flagged as a process failure.
- Out-of-envelope changes continue to require explicit Council rulings.

---

## Sign-Off

**Chair (Architect/Head of Dev/Head of Testing)** — APPROVED FOR ADOPTION  
**Date**: 2026-01-07  

---

**END OF RULING**
