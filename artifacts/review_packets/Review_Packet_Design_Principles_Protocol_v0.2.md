# Review Packet: Design Principles Protocol v0.2

**Packet ID:** Review_Packet_Design_Principles_Protocol_v0.2  
**Date:** 2026-01-08  
**Author:** Claude (Execution Partner)  
**Mission:** Adopt recommendations from v0.1 review, create v0.2, prepare CCP for Council

---

## 1. Summary

Created LifeOS Design Principles Protocol v0.2, incorporating all governance reconciliation recommendations from the v0.1 review. The protocol establishes "prove then harden" development principles while maintaining full compatibility with existing LifeOS governance.

---

## 2. Issue Catalogue

| ID | Issue | Resolution |
|----|-------|------------|
| T1 | No sandbox definition | Added §2.3 Development Sandbox |
| T2 | GEMINI.md Plan Artefact Gate conflict | Added §2.4 with Spike Declaration exception |
| T3 | Council Protocol CT-1 ambiguity | Added §2.5 clarifying sandbox exemption |
| T4 | No Review Packet for spikes | Added §4.1 Lightweight Review Packet |
| T5 | CEO override not explicit | Added §5.4 CEO Override Authority |
| T6 | "Governance surface" undefined | Added §5.5 referencing GEMINI.md Article XIII §4 |

---

## 3. Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| v0.2 incorporates all recommendations | ✅ PASS |
| Sandbox definition is precise | ✅ PASS |
| GEMINI.md reconciliation is sound | ✅ PASS |
| Council Protocol CT-1 is clarified | ✅ PASS |
| CEO override authority is explicit | ✅ PASS |
| Governance surface is defined | ✅ PASS |
| CCP has valid YAML header | ✅ PASS |
| CCP contains all required sections | ✅ PASS |

---

## 4. Non-Goals

- Amending Constitution v2.0
- Amending Council Protocol v1.2
- Amending GEMINI.md
- Runtime implementation
- Executing the Council review (that is the next step)

---

## 5. Files Created/Modified

| Action | Path |
|--------|------|
| CREATE | `docs/01_governance/LifeOS_Design_Principles_Protocol_v0.2.md` |
| CREATE | `artifacts/council_reviews/CCP_Design_Principles_Protocol_v0.2.md` |
| UPDATE | `docs/INDEX.md` (timestamp + entry) |

---

## 6. Appendix — Flattened Code Snapshots

### File: docs/01_governance/LifeOS_Design_Principles_Protocol_v0.2.md

```markdown
# LifeOS Design Principles Protocol

**Version:** v0.2  
**Status:** Draft — For Council Review  
**Date:** 2026-01-08  
**Author:** Claude (Execution Partner)  
**Canonical Path:** `docs/01_governance/LifeOS_Design_Principles_Protocol_v0.2.md`

---

## 1. Purpose

This document establishes design principles for LifeOS development that prioritize working software over comprehensive documentation, while maintaining appropriate governance for production systems.

**The Problem It Solves:**

Council reviews produce thorough, hardened specifications. This is correct for production systems. However, applying full council rigor to unproven concepts creates:

- Weeks of specification work before any code runs
- Governance overhead for systems that don't exist
- Edge case handling for scenarios never encountered
- Analysis paralysis disguised as thoroughness

**The Principle:**

> Governance follows capability. Prove it works, then harden it.

---

## 2. Authority & Binding

### 2.1 Subordination

This document is subordinate to:

1. LifeOS Constitution v2.0 (Supreme)
2. Council Protocol v1.2
3. Tier Definition Spec v1.1
4. GEMINI.md Agent Constitution

### 2.2 Scope

This protocol applies to:

- New capability development (features, systems, integrations)
- Architectural exploration
- Prototypes and proofs of concept

This protocol does NOT override:

- Existing governance surface protections
- Council authority for production deployments
- CEO authority invariants

### 2.3 Development Sandbox

MVP and spike work MUST occur in locations that:

1. **Are not under governance control** — Not in `docs/00_foundations/`, `docs/01_governance/`, `runtime/governance/`, or any path matching `*Constitution*.md` or `*Protocol*.md`
2. **Are explicitly marked as experimental** — Permitted locations:
   - `runtime/experimental/`
   - `spikes/`
   - `sandbox/`
   - Any directory containing `_wip` or `_experimental` suffix
3. **Can be deleted without triggering governance alerts**
4. **Do NOT trigger Document Steward Protocol** — Files in sandbox locations are exempt from `INDEX.md` updates and corpus regeneration until promoted

> [!IMPORTANT]
> Sandbox locations provide a "proving ground" where full governance protocol does not apply until the capability seeks production status.

### 2.4 GEMINI.md Reconciliation (Plan Artefact Gate)

GEMINI.md Article XIII requires a Plan Artefact before substantive work. This protocol provides a lightweight exception:

**Spike Mode:**

For time-boxed explorations (≤3 days), agents may use a **Spike Declaration** instead of a full `implementation_plan.md`:

```markdown
## Spike Declaration
**Question:** [Single question to answer]
**Time Box:** [Duration: 2 hours / 1 day / 3 days]
**Success Criteria:** [Observable result]
**Sandbox Location:** [Path within permitted sandbox]
```

**Conditions:**
- Spike Declaration must be recorded in `artifacts/spikes/` or task.md
- Work must remain within declared sandbox location
- CEO retains authority to cancel at any time
- Upon spike completion, a Lightweight Review Packet is required (see §4.1)

### 2.5 Council Protocol Reconciliation (CT-1 Trigger)

Council Protocol v1.2 CT-1 triggers on "new capability introduction." This protocol clarifies:

1. **MVP work in sandbox locations does NOT trigger CT-1** — Exploratory work is not a capability until it seeks production status
2. **Integration with governance surfaces triggers CT-1** — When MVP work touches governance-controlled paths or seeks promotion to `runtime/` or `docs/`, CT-1 applies
3. **Council reviews working systems** — Hardening reviews evaluate running code with test evidence, not theoretical architectures

---

## 3. Core Principles

### 3.1 Working Software Over Comprehensive Specification

**Do:** Write code that runs and produces observable results.  
**Don't:** Write specifications for code that doesn't exist.

A 50-line script that executes is more valuable than a 500-line specification describing what a script might do.

### 3.2 Prove Then Harden

Development follows three stages:

| Stage | Focus | Governance |
|-------|-------|------------|
| **Prove** | Does it work at all? | Minimal — CEO oversight only, sandbox locations |
| **Stabilize** | Does it work reliably? | Light — Tests, basic error handling |
| **Harden** | Is it production-ready? | Full — Council review, edge cases, compliance |

Moving to Harden before completing Prove is forbidden. It produces governance for vaporware.

### 3.3 Tests Are The Specification

Code without tests is a prototype. Code with tests is a candidate for production.

Tests serve as:
- Executable specification (what the code should do)
- Regression protection (proof it still works)
- Documentation (examples of correct usage)

A feature is "done" when its tests pass, not when its specification is complete.

### 3.4 Smallest Viable Increment

Each development cycle should produce the smallest increment that:
- Runs end-to-end (no partial implementations)
- Is observable (produces output CEO can verify)
- Is reversible (can be deleted without breaking other systems)

Prefer 5 small increments over 1 large increment. Each small increment teaches something.

### 3.5 Fail Fast, Learn Faster

Early failures are cheap. Late failures are expensive.

- Prototype the riskiest part first
- If it can't work, find out in hours, not weeks
- Dead ends are acceptable; late dead ends are not

---

## 4. Development Workflow

### 4.1 The Spike

A **spike** is a time-boxed exploration to answer a specific question.

**Format:**
```
Question: Can X work?
Time box: [2 hours / 1 day / 3 days]
Success criteria: [Observable result that answers the question]
Sandbox location: [Permitted experimental path]
```

**Rules:**
- Spikes produce code, not documents
- Spike code is disposable — it exists to learn, not to ship
- Spikes end with a decision: proceed, pivot, or abandon

**Review Packet Requirement:**

Per GEMINI.md Article XVIII (Lightweight Stewardship Mode), spikes produce a **Lightweight Review Packet** documenting:

1. **Question answered** — The original spike question
2. **Outcome** — proceed / pivot / abandon
3. **Key learnings** — What was discovered
4. **Evidence** — Test output, execution logs, or demo results
5. **Next steps** — If proceeding, what MVP scope is proposed

**Example:**
```
Question: Can we invoke OpenCode programmatically via HTTP?
Time box: 2 hours
Success criteria: Python script that sends prompt, receives response
Sandbox location: spikes/opencode_http/
```

### 4.2 The MVP Build

Once a spike proves viability, build the **Minimum Viable Product**:

**Definition:** The smallest implementation that delivers end-to-end value.

**MVP Checklist:**
- [ ] Runs without manual intervention (for its scope)
- [ ] Produces observable output
- [ ] Has at least one happy-path test
- [ ] Has basic error handling (fails loudly, not silently)
- [ ] Is documented in a README or inline comments
- [ ] Remains within sandbox until hardening

**MVP Exclusions (defer to Harden phase):**
- Edge case handling
- Performance optimization
- Comprehensive error recovery
- Audit logging
- Governance compliance (beyond sandbox rules)

### 4.3 Test-Driven Development

For MVP builds, follow TDD:

1. **Write a failing test** — Define what success looks like
2. **Write minimal code to pass** — No more than needed
3. **Refactor** — Clean up without changing behavior
4. **Repeat** — Next test, next increment

**Test Priorities:**

| Priority | Test Type | When to Write |
|----------|-----------|---------------|
| P0 | Happy path | Always — MVP requirement |
| P1 | Obvious failure modes | MVP if time permits |
| P2 | Edge cases | Stabilize phase |
| P3 | Adversarial inputs | Harden phase |

### 4.4 The Hardening Pass

After MVP is working and stable, apply full governance:

**Hardening Checklist:**
- [ ] Council review of design
- [ ] Edge case analysis and handling
- [ ] Security review (if applicable)
- [ ] Performance requirements met
- [ ] Governance surface protections verified
- [ ] Documentation complete
- [ ] Rollback/compensation procedures defined
- [ ] Promotion from sandbox to production location

**Council Review Scope:**

Council reviews the working system, not the proposed system. Review packets should include:
- Evidence of working MVP (test results, demo output)
- Proposed hardening additions
- Risk analysis for gaps between MVP and production

---

## 5. Interaction With Council Protocol

### 5.1 When Council Review Is Required

| Stage | Council Review |
|-------|----------------|
| Spike | Not required (sandbox) |
| MVP (sandbox, non-governance) | Not required |
| MVP (touches governance surfaces) | Required before merge |
| Stabilize | Not required |
| Harden | Required before production designation |

### 5.2 Council Review For Hardening

When submitting for hardening review, the packet should include:

1. **Working MVP evidence** — Test results, execution logs
2. **Gap analysis** — What MVP lacks vs. production requirements
3. **Proposed hardening** — Specific additions for each gap
4. **Risk assessment** — What could go wrong, likelihood, mitigation

Council reviews what exists and what should be added, not theoretical architecture.

### 5.3 Incremental Hardening

Large systems should be hardened incrementally:

1. MVP of full loop (minimal governance)
2. Council review → Harden component A
3. Council review → Harden component B
4. ...
5. Council review → Full production designation

Each increment is a working system. No increment is "governance for future features."

### 5.4 CEO Override Authority

The CEO retains full authority to:

1. **Terminate spikes** — At any time, for any reason
2. **Promote MVP directly to Harden** — If urgency warrants, bypassing Stabilize
3. **Demote hardened systems to Stabilize** — If regressions appear
4. **Grant sandbox extensions** — If spike time box proves insufficient
5. **Require immediate Council review** — For any capability at any stage

CEO authority is invariant and not constrained by this protocol.

### 5.5 Governance Surface Definition

Per GEMINI.md Article XIII §4, **governance surfaces** include:

- `docs/00_foundations/`
- `docs/01_governance/`
- `runtime/governance/`
- `GEMINI.md`
- Any file matching `*Constitution*.md`
- Any file matching `*Protocol*.md`

Work touching these surfaces requires Plan Artefact approval (no spike exception) and triggers CT-1 for Council review.

---

## 6. Anti-Patterns

### 6.1 Specification Without Implementation

**Symptom:** 20-page design doc, zero lines of code.  
**Problem:** No validation that design is feasible.  
**Fix:** Spike the riskiest assumption before writing the spec.

### 6.2 Premature Hardening

**Symptom:** Comprehensive error handling for code paths never executed.  
**Problem:** Effort spent on hypotheticals, not reality.  
**Fix:** Add hardening only after MVP proves the path is real.

### 6.3 Governance Theater

**Symptom:** Full council review for exploratory prototype.  
**Problem:** Process optimized for compliance, not learning.  
**Fix:** Reserve council review for hardening phase.

### 6.4 Big Bang Integration

**Symptom:** 5 components developed in parallel, integrated at the end.  
**Problem:** Integration failures discovered late, debugging is hard.  
**Fix:** Build and integrate incrementally. Each increment runs end-to-end.

### 6.5 Gold Plating

**Symptom:** Features nobody asked for, edge cases that never occur.  
**Problem:** Effort spent on low-value polish.  
**Fix:** Ship MVP, wait for real feedback, add features that matter.

### 6.6 Sandbox Escape

**Symptom:** Spike code deployed to production locations without hardening.  
**Problem:** Experimental work bypasses governance.  
**Fix:** Sandbox locations are enforced. Promotion requires hardening pass.

---

## 7. Application To Autonomous Build Loop

### 7.1 Current State

The Autonomous Build Loop Architecture v0.3 is a hardened specification for a system that has never run. This inverts the correct order.

### 7.2 Correct Sequence

**Phase 1: Spike (1-2 days)**
- Question: Can we execute design→review→build→commit without manual routing?
- Success: One backlog task completes with CEO observing.
- Location: `spikes/build_loop_poc/`

**Phase 2: MVP (3-5 days)**
- Minimal orchestration wiring
- Basic logging (no hash chains)
- Happy path only
- CEO as manual kill switch
- Location: `sandbox/build_loop_mvp/`

**Phase 3: Stabilize (1-2 weeks)**
- Add error handling for observed failure modes
- Add tests for paths that broke during MVP
- Run 10-20 tasks supervised
- Location: Remains in sandbox

**Phase 4: Harden (2-4 weeks)**
- Council review of working system
- Add v0.3 requirements incrementally:
  - Governance baseline verification
  - Compensation procedures
  - Hash chain evidence
  - Crash recovery
  - Kill switch automation
- Location: Promote to `runtime/orchestration/` upon Council approval

### 7.3 v0.3 As Roadmap, Not Prerequisite

v0.3 defines the destination. It should not block the journey.

Each v0.3 requirement becomes a hardening work item after MVP proves the core loop works. Council reviews validate that hardening is correctly applied to a working system.

---

## 8. Success Metrics

### 8.1 Cycle Time

Measure time from "idea" to "running code":
- Spike: < 1 day
- MVP: < 1 week
- Hardening: Varies by scope

If cycle time exceeds these bounds, examine for anti-patterns.

### 8.2 Test Coverage Progression

| Stage | Coverage Target |
|-------|-----------------|
| Spike | 0% (disposable code) |
| MVP | >50% of happy paths |
| Stabilize | >80% of exercised paths |
| Harden | >90% including edge cases |

### 8.3 Governance Debt Tracking

Maintain a list of "hardening debt" — gaps between MVP and production requirements. Each item should have:
- Description
- Risk if unaddressed
- Estimated effort to address
- Target phase

Debt is acceptable. Untracked debt is not.

### 8.4 Metrics Tracking

Metrics are tracked in `docs/11_admin/METRICS.md` or programme dashboard when established.

---

## 9. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.2 | 2026-01-08 | Claude | Added: §2.3 Development Sandbox, §2.4 GEMINI.md Reconciliation, §2.5 Council Protocol Reconciliation, §4.1 Review Packet requirements, §5.4 CEO Override Authority, §5.5 Governance Surface Definition, §6.6 Sandbox Escape anti-pattern. Updated subordination chain. |
| 0.1 | 2026-01-08 | Claude | Initial draft |

---

**END OF DOCUMENT**
```

---

### File: artifacts/council_reviews/CCP_Design_Principles_Protocol_v0.2.md

```markdown
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
```

---

**END OF REVIEW PACKET**
