# LifeOS Design Principles Protocol

**Version:** v1.1  
**Status:** Canonical  
**Date:** 2026-01-08  
**Author:** Claude (Execution Partner)  
**Canonical Path:** `docs/02_protocols/LifeOS_Design_Principles_Protocol_v1.1.md`

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
2. **Are explicitly marked as experimental** — Permitted locations (exhaustive list):
   - `runtime/experimental/`
   - `spikes/`
   - `sandbox/`
3. **Can be deleted without triggering governance alerts** — Sandbox code may be deleted without governance alerts, PROVIDED:
   - Spike Declaration lives in `artifacts/spikes/<YYYYMMDD>_<short_slug>/SPIKE_DECLARATION.md`
   - Lightweight Review Packet (with proof_evidence) lives in `artifacts/spikes/<YYYYMMDD>_<short_slug>/REVIEW_PACKET.md`
   - Evidence files (logs, test outputs) are preserved in `artifacts/spikes/<YYYYMMDD>_<short_slug>/evidence/`
   
   > These durable artefact locations are NOT part of the deletable sandbox.
4. **Do NOT trigger Document Steward Protocol** — Files in sandbox locations are exempt from `INDEX.md` updates and corpus regeneration until promoted

> [!IMPORTANT]
> Sandbox locations provide a "proving ground" where full governance protocol does not apply until the capability seeks production status.

### 2.4 GEMINI.md Reconciliation (Plan Artefact Gate)

This protocol establishes the **Spike Declaration** as the authorized Plan Artefact format for Spike Mode, consistent with GEMINI.md Article XVIII (Lightweight Stewardship). It is not an exception for governance-surface work.

**Spike Mode:**

For time-boxed explorations (≤3 days), agents MUST use a **Spike Declaration** as the Plan Artefact:

```markdown
## Spike Declaration
**Question:** [Single question to answer]
**Time Box:** [Duration: 2 hours / 1 day / 3 days]
**Success Criteria:** [Observable result]
**Sandbox Location:** [Path within permitted sandbox — see §2.3]
```

**Conditions:**
- Spike Declaration MUST be recorded **before execution** at: `artifacts/spikes/<YYYYMMDD>_<short_slug>/SPIKE_DECLARATION.md`
- Work must remain within declared sandbox location (§2.3 permitted roots only)
- CEO retains authority to cancel at any time
- Upon spike completion, a Lightweight Review Packet is required (see §4.1)

> [!CAUTION]
> **Spike Mode is prohibited for governance surfaces.** If work touches any path listed in §5.5, full Plan Artefact (implementation_plan.md) and Council review are required. No spike exception applies.

### 2.5 Council Protocol Reconciliation (CT-1 Trigger)

Council Protocol v1.2 CT-1 triggers on "new capability introduction." This protocol clarifies:

1. **MVP work in sandbox locations does NOT trigger CT-1** — Exploratory work is not a capability until it seeks production status
2. **Integration with governance surfaces triggers CT-1** — See §2.5.1 for definition
3. **Council reviews working systems** — Hardening reviews evaluate running code with test evidence, not theoretical architectures

#### 2.5.1 Definition: Integration with Governance Surfaces

"Integration with governance surfaces" means ANY of the following:

- **Importing/calling** governance-controlled modules or functions
- **Reading/writing** governance-controlled files or paths at runtime
- **Staging/merging** changes that touch governance surfaces (per §5.5)
- **Promoting** capability into `runtime/` or `docs/` paths outside sandbox roots (§2.3)

This definition is consistent with §5.5 (Governance Surface Definition).

### 2.6 Output-First Default

Work may start without council review when ALL of the following conditions are met:

1. **Sandbox confinement** — Work remains in permitted sandbox locations (§2.3)
2. **Non-governance scope** — Work does not touch governance surfaces (§5.5)
3. **One-Command Proof** — Produces a runnable artefact that executes via one command/script (§4.2.1)
4. **Evidence captured** — Output log, exit code, and artefact path are recorded per §4.1

> [!IMPORTANT]
> Output-First does not mean "governance-free." It means governance follows proof. The capability must prove it works before it receives governance attention.

### 2.7 Governance as Promotion/Hardening Gate

Council/CT-1 review is required ONLY on explicit triggers:

| Trigger | Description | CT-1? |
|---------|-------------|-------|
| **Promotion into governed paths** | Moving code/docs from sandbox to production-designated locations | Yes |
| **Governance surface touch** | Any change to governance-controlled docs/policies/schemas (§5.5) | Yes |
| **Runtime surface wiring** | Wiring capability into governed runtime surfaces | Yes |
| **Integration** | Import/call/read/write/stage/merge into governance-controlled paths (§2.5.1) | Yes |

**Explicit Non-Triggers:**
- Working in sandbox locations — NOT a trigger
- MVP development with no governance touches — NOT a trigger
- Spike exploration with captured evidence — NOT a trigger

> [!CAUTION]
> Ambiguity alone is NOT a council trigger unless it creates a governance boundary bypass. If uncertain whether work crosses a boundary, confer with CEO; do not escalate to full council as default.

### 2.8 No Paper Without Mechanization

Any governance requirement introduced during review must satisfy ONE of:

1. **Mechanized enforcement** — Enforced by a script, CI gate, or audit tool (`pytest`, `validate_closure_bundle.py`, etc.)
2. **Step replacement** — Deletes or replaces an existing manual step (net ≤ 0 human steps)

Requirements failing both conditions are **non-binding guidance (P2 max)** and must not block promotion or hardening.

**Rationale:** Governance that only exists on paper creates compliance theater without safety benefit.

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

### 3.6 Simplicity Counterweight

Any recommendation that increases human steps or introduces new policy surfaces is non-compliant unless it:

1. **States the explicit trade** — What is being deleted or automated
2. **Yields net ≤ 0 human-step delta** — New burden must not exceed removed burden

This applies to:
- Council review recommendations
- Fix plan items
- New governance requirements

> [!NOTE]
> This principle is enforced via Complexity Budget Accounting in council outputs (Council Protocol §7.3).

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
4. **Next steps** — If proceeding, what MVP scope is proposed
5. **Evidence (mandatory fields):**

```yaml
proof_evidence:
  command: "<exact command to run spike/MVP>"
  exit_code: <integer>
  output_log: "<path to log file OR inline excerpt>"
  error_log: "<path to error log OR 'none'>"
  artifact_path: "<path where runnable code/demo lives>"
  test_command: "<pytest command or equivalent, OR 'none' for spikes>"
  test_result: "pass | fail | skip | none"
```

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
- [ ] Runs end-to-end via a single command/script with no interactive input (for its scope)
- [ ] Produces observable output
- [ ] Has at least one happy-path test
- [ ] Tests are executable via `pytest` or equivalent without environment surgery
- [ ] Has basic error handling (fails loudly, not silently)
- [ ] Is documented in a README or inline comments
- [ ] Remains within sandbox until hardening

#### 4.2.1 One-Command Proof Gate (MVP Reality Check)

An MVP is not "real" unless it satisfies the **One-Command Proof Gate**:

1. **Runs end-to-end via ONE command/script** — No interactive input, no manual steps
2. **Evidence captured** — Required fields:

```yaml
proof_evidence:
  command: "<exact command used>"
  exit_code: <integer>
  output_log: "<path to log file>"
  artifact_path: "<path to runnable artifact>"
  test_command: "<pytest command or equivalent>"
  test_result: "pass | fail | skip"
```

3. **At least one automated happy-path test** — Executed via `pytest` or equivalent, results captured

**Gate enforcement:**
- MVP promotion requests lacking proof_evidence are returned without review
- Gate is mechanized: proof_evidence schema is validated before council intake

> [!TIP]
> The proof gate prevents "governance for vaporware" — reviewer time is only spent on capabilities that demonstrably work.

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

> [!IMPORTANT]
> At least one failing happy-path test must exist before MVP code is considered started.

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
5. **Governance debt enumeration** — From §8.3, with risk assessment and proposed closure plan

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

| Stage | Coverage Gate | Optional % Target |
|-------|---------------|-------------------|
| Spike | No tests required (disposable code) | 0% |
| MVP | Covers all user-visible outcomes (happy path) with runnable test(s) | >50% |
| Stabilize | Covers all exercised paths observed in supervised runs | >80% |
| Harden | Adds edge/adversarial cases relevant to real failures | >90% |

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
|---------|------|--------|--------|
| 1.1 | 2026-01-08 | Claude | **Output-First Governance**: Added §2.6 Output-First Default, §2.7 Governance as Promotion/Hardening Gate, §2.8 No Paper Without Mechanization, §3.6 Simplicity Counterweight, §4.2.1 One-Command Proof Gate. Updated §2.3 evidence preservation, §4.1 proof_evidence schema. |
| 1.0 | 2026-01-08 | Claude | **Canonical Promotion**: Promoted to v1.0 after Council approval. |
| 0.2.1 | 2026-01-08 | Claude | **Council GO_WITH_FIXES applied**: §2.3 sandbox loophole closed (removed pattern rule); §2.4 reframed as compliant format (not exception) + governance prohibition + deterministic path; §2.5.1 added integration definition; §4.1 mandatory evidence fields; §4.2 single-command + test execution requirements; §4.3 TDD gate; §5.2 governance debt requirement; §8.2 outcome-based coverage gates. |
| 0.2 | 2026-01-08 | Claude | Added: §2.3 Development Sandbox, §2.4 GEMINI.md Reconciliation, §2.5 Council Protocol Reconciliation, §4.1 Review Packet requirements, §5.4 CEO Override Authority, §5.5 Governance Surface Definition, §6.6 Sandbox Escape anti-pattern. Updated subordination chain. |
| 0.1 | 2026-01-08 | Claude | Initial draft |

---

**END OF DOCUMENT**
