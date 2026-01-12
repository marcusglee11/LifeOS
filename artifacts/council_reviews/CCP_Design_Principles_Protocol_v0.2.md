---
council_run:
  aur_id: "AUR_20260108_design_principles_protocol"
  aur_type: "governance"
  change_class: "new"
  touches:
    - "governance_protocol"
    - "docs_only"
  blast_radius: "module"
  reversibility: "easy"
  safety_critical: false
  uncertainty: "low"
  override:
    mode: null
    topology: null
    rationale: null

mode_selection_rules_v1:
  default: "M1_STANDARD"
  computed_mode: "M2_FULL"
  rationale: "touches includes 'governance_protocol' → M2_FULL required per mode_selection_rules_v1.M2_FULL_if_any"

model_plan_v1:
  topology: "MONO"
  models:
    primary: "claude-sonnet-4-20250514"
    adversarial: "claude-sonnet-4-20250514"
    implementation: "claude-sonnet-4-20250514"
    governance: "claude-sonnet-4-20250514"
  role_to_model:
    Chair: "primary"
    CoChair: "primary"
    Architect: "primary"
    Alignment: "primary"
    StructuralOperational: "primary"
    Technical: "primary"
    Testing: "primary"
    RiskAdversarial: "adversarial"
    Simplicity: "primary"
    Determinism: "adversarial"
    Governance: "governance"
  constraints:
    mono_mode:
      all_roles_use: "primary"
---

# Council Context Pack: Design Principles Protocol v0.2

**CCP ID:** CCP_20260108_design_principles_protocol  
**Date:** 2026-01-08  
**Prepared By:** Claude (Execution Partner)  
**Review Mode:** M2_FULL (governance_protocol touch)

---

## 1. AUR Package

### 1.1 Artefact Under Review

| Field | Value |
|-------|-------|
| **AUR ID** | AUR_20260108_design_principles_protocol |
| **Title** | LifeOS Design Principles Protocol v0.2 |
| **Path** | `docs/01_governance/LifeOS_Design_Principles_Protocol_v0.2.md` |
| **Type** | Governance Protocol |
| **Change Class** | New |

### 1.2 Supporting Context Artefacts

| Document | Path | Relevance |
|----------|------|-----------|
| LifeOS Constitution v2.0 | `docs/00_foundations/LifeOS_Constitution_v2.0.md` | Supreme authority |
| Council Protocol v1.2 | `docs/02_protocols/Council_Protocol_v1.2.md` | Defines review process |
| Tier Definition Spec v1.1 | `docs/Tier_Definition_Spec_v1.1.md` | Capability tier definitions |
| GEMINI.md | `GEMINI.md` | Agent constitution (reconciliation target) |
| Design Principles v0.1 | `docs/LifeOS_Design_Principles_Protocol_v0.1.md` | Previous draft (superseded) |

---

## 2. Council Objective

### 2.1 Purpose

Evaluate the Design Principles Protocol v0.2 for **promotion to canonical governance status** in `docs/01_governance/`.

### 2.2 Success Criteria

1. **Authority chain is valid** — Correctly subordinate to Constitution, Council Protocol, Tier Spec
2. **No governance conflicts** — Reconciliation with GEMINI.md and Council Protocol is sound
3. **Operationally clear** — Sandbox definition, spike/MVP workflow, and governance thresholds are unambiguous
4. **CEO authority preserved** — Override semantics do not constrain CEO invariants
5. **No scope creep** — Protocol stays within its declared scope

---

## 3. Scope Boundaries

### 3.1 In Scope

- Design principles for new capability development
- Spike/MVP/Stabilize/Harden workflow
- Sandbox location definitions
- Interaction with Council Protocol CT-1
- Interaction with GEMINI.md Plan Artefact Gate
- CEO override authority

### 3.2 Out of Scope

- Amendments to Constitution v2.0
- Amendments to Council Protocol v1.2
- Amendments to GEMINI.md
- Runtime implementation details
- Specific system architectures

### 3.3 Invariants (Non-Negotiable)

1. CEO authority is absolute — Protocol may not constrain CEO
2. Council authority for production — Protocol may not bypass Council for hardening
3. Governance surface protection — Protocol may not create exceptions for governance touches
4. Constitution supremacy — Protocol is subordinate, not peer

---

## 4. Gap Analysis: v0.1 → v0.2

### 4.1 Issues Identified in v0.1 Review

| Issue | Severity | Resolution in v0.2 |
|-------|----------|-------------------|
| No sandbox definition | Medium | Added §2.3 Development Sandbox |
| GEMINI.md Plan Artefact Gate conflict | High | Added §2.4 with Spike Mode exception |
| Council Protocol CT-1 ambiguity | High | Added §2.5 clarifying sandbox exemption |
| No Review Packet for spikes | Medium | Added §4.1 Lightweight Review Packet requirement |
| CEO override not explicit | Medium | Added §5.4 CEO Override Authority |
| "Governance surface" undefined | Medium | Added §5.5 referencing GEMINI.md Article XIII §4 |
| Missing sandbox escape anti-pattern | Low | Added §6.6 Sandbox Escape |

### 4.2 Additions in v0.2

1. **§2.3 Development Sandbox** — Formal definition of permitted experimental locations
2. **§2.4 GEMINI.md Reconciliation** — Spike Declaration as lightweight Plan Artefact alternative
3. **§2.5 Council Protocol Reconciliation** — CT-1 does not trigger for sandbox work
4. **§4.1 Review Packet** — Lightweight Review Packet required for spike completion
5. **§5.4 CEO Override Authority** — Explicit enumeration of CEO powers
6. **§5.5 Governance Surface Definition** — Reference to canonical definition
7. **§6.6 Sandbox Escape** — New anti-pattern for uncontrolled promotion

---

## 5. Risk Assessment

### 5.1 Risks If Approved

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Sandbox abuse (indefinite deferral of hardening) | Medium | Medium | Spike time boxes, CEO oversight |
| Spike mode used for governance touches | Low | High | §2.4 explicitly excludes governance surfaces |
| Premature reliance on untested code | Medium | Medium | MVP checklist requires happy-path tests |
| Council review deferred indefinitely | Low | High | §5.1 table is binding; hardening requires review |

### 5.2 Risks If Rejected

| Risk | Likelihood | Impact |
|------|------------|--------|
| Continued specification-first development | High | Medium — slower iteration |
| Governance theater for exploratory work | High | Low — wasted effort |
| No formal sandbox definition | Medium | Medium — ad-hoc experimental work |

---

## 6. Proposed Verdict Options

| Verdict | Condition |
|---------|-----------|
| **Accept** | Protocol is sound, no material issues |
| **Go with Fixes** | Minor issues require amendment before canonical status |
| **Reject** | Material conflicts with authority chain or governance model |

---

## 7. Attachments

### 7.1 Full AUR Content

The complete v0.2 document is located at:
- **Path:** `docs/01_governance/LifeOS_Design_Principles_Protocol_v0.2.md`

### 7.2 Superseded Document

The v0.1 document to be archived upon approval:
- **Path:** `docs/LifeOS_Design_Principles_Protocol_v0.1.md`
- **Action:** Move to `docs/99_archive/superseded/` after Council approval

---

## 8. Council Run Log (To Be Completed)

```yaml
council_run_log:
  ccp_id: "CCP_20260108_design_principles_protocol"
  execution_date: null  # To be filled
  mode: "M2_FULL"
  topology: "MONO"
  seats_executed: []  # To be filled
  verdict: null  # Accept | Go with Fixes | Reject
  fix_plan: []  # If applicable
  contradiction_ledger: []  # Required for M2_FULL
  notes:
    bootstrap_used: false
    override_rationale: null
```

---

**END OF CCP**
