# LifeOS Design Principles Protocol

**Version:** v0.1  
**Status:** Draft — For CEO Review  
**Date:** 2026-01-08  
**Author:** Claude (Execution Partner)  
**Intended Placement:** `docs/01_governance/LifeOS_Design_Principles_Protocol_v0.1.md`

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

### 2.2 Scope

This protocol applies to:

- New capability development (features, systems, integrations)
- Architectural exploration
- Prototypes and proofs of concept

This protocol does NOT override:

- Existing governance surface protections
- Council authority for production deployments
- CEO authority invariants

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
| **Prove** | Does it work at all? | Minimal — CEO oversight only |
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
```

**Rules:**
- Spikes produce code, not documents
- Spike code is disposable — it exists to learn, not to ship
- Spikes end with a decision: proceed, pivot, or abandon

**Example:**
```
Question: Can we invoke OpenCode programmatically via HTTP?
Time box: 2 hours
Success criteria: Python script that sends prompt, receives response
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

**MVP Exclusions (defer to Harden phase):**
- Edge case handling
- Performance optimization
- Comprehensive error recovery
- Audit logging
- Governance compliance

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
| Spike | Not required |
| MVP (non-governance) | Not required |
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

---

## 7. Application To Autonomous Build Loop

### 7.1 Current State

The Autonomous Build Loop Architecture v0.3 is a hardened specification for a system that has never run. This inverts the correct order.

### 7.2 Correct Sequence

**Phase 1: Spike (1-2 days)**
- Question: Can we execute design→review→build→commit without manual routing?
- Success: One backlog task completes with CEO observing.

**Phase 2: MVP (3-5 days)**
- Minimal orchestration wiring
- Basic logging (no hash chains)
- Happy path only
- CEO as manual kill switch

**Phase 3: Stabilize (1-2 weeks)**
- Add error handling for observed failure modes
- Add tests for paths that broke during MVP
- Run 10-20 tasks supervised

**Phase 4: Harden (2-4 weeks)**
- Council review of working system
- Add v0.3 requirements incrementally:
  - Governance baseline verification
  - Compensation procedures
  - Hash chain evidence
  - Crash recovery
  - Kill switch automation

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

Maintain a list of "hardening debt" — gaps between MVP and v0.3 requirements. Each item should have:
- Description
- Risk if unaddressed
- Estimated effort to address
- Target phase

Debt is acceptable. Untracked debt is not.

---

## 9. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-01-08 | Claude | Initial draft |

---

**END OF DOCUMENT**
