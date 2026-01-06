---
council_run:
  aur_id: "AUR_20260106_Core_TDD_Principles_v1.0"
  aur_type: "governance"
  change_class: "new"
  touches:
    - "governance_protocol"
    - "runtime_core"
    - "docs_only"
  blast_radius: "system"
  reversibility: "hard"
  safety_critical: true
  uncertainty: "medium"
  override:
    mode: null
    topology: "MONO"
    rationale: "Defaulting to MONO for self-contained bootstrap execution; Chair may distribute if capable."

mode_selection_rules_v1:
  default: "M1_STANDARD"
  M2_FULL_if_any:
    - touches includes "governance_protocol"
    - touches includes "tier_activation"
    - touches includes "runtime_core"
    - safety_critical == true
    - (blast_radius in ["system","ecosystem"] and reversibility == "hard")
    - (uncertainty == "high" and blast_radius != "local")
  M0_FAST_if_all:
    - aur_type in ["doc","plan","other"]
    - (touches == ["docs_only"] or (touches excludes "runtime_core" and touches excludes "interfaces" and touches excludes "governance_protocol"))
    - blast_radius == "local"
    - reversibility == "easy"
    - safety_critical == false
    - uncertainty == "low"
  operator_override:
    if override.mode != null: "use override.mode"

model_plan_v1:
  topology: "MONO"
  models:
    primary: "current_model"
    adversarial: "current_model_fresh_context"
    implementation: "current_model"
    governance: "current_model"
  role_to_model:
    Chair: "primary"
    CoChair: "primary"
    Architect: "primary"
    Alignment: "primary"
    StructuralOperational: "primary"
    Technical: "implementation"
    Testing: "implementation"
    RiskAdversarial: "adversarial"
    Simplicity: "primary"
    Determinism: "adversarial"
    Governance: "governance"
  constraints:
    mono_mode:
      all_roles_use: "primary"
---

# Council Context Pack: Core TDD Principles v1.0

**Status**: BOOTSTRAP (Embedded Prompts)
**Target**: `docs/02_protocols/Core_TDD_Design_Principles_v1.0.md`

---

## 1. Objective
**Primary**: Ratify the canonical TDD Design Principles for the Core Track.
**Success Criteria**:
1.  Verify the principles provide a verifiable "fail-closed" deterministic envelope.
2.  Ensure no critical governance or risk gaps in the definition.
3.  Approve the document for "Canonical Promotion".

## 2. Scope Boundaries
**In Scope**:
- The text of `Core_TDD_Design_Principles_v1.0.md`.
- Adequacy of the "Enforcement" section (§6).
- Definitions of "Deterministic Envelope" and "Allowlist".

**Out of Scope**:
- Refactoring existing code to meet these principles (that is a separate implementation task).
- Specific CI pipeline configuration (covered by separate Runtime specs), except where referenced by TDD principles.

**Invariants**:
- Must not weaken existing LifeOS Constitution v2.0 requirements.
- Must not introduce non-deterministic dependencies into the Core Track.

---

## 3. Decision Surface (Machine-Usable)
The Chair must produce a **Consolidated Verdict** and **Fix Plan**.
- **Verdict**: `GO`, `GO_WITH_FIXES`, or `NO_GO`.
- **Fixes**: Must be prioritized P0 (Blocking) vs P1 (Non-blocking hygiene) vs P2 (Deferrable).
- **Split-Brain Risk**: If Seats disagree on fundamental facts, the Chair must log a Contradiction and *resolve* it with evidence or flag for CEO.

---

## 4. Execution Instructions (Bootstrap Mode)
Since this is a **BOOTSTRAP** run, all necessary inputs (AUR + Prompts) are embedded below.

**Sequence**:
1.  **Read the AUR** (§5).
2.  **Assume the Role of Chair** using the embedded prompt (§6.1).
3.  **Execute the Review Steps** (M2_FULL) by invoking each Seat using its embedded prompt (§6.3 - §6.11).
    - Note: This is an **M2_FULL** run because `safety_critical=true` and `governance_protocol` is touched.
4.  Synthesize findings into the **Council Run Log** (§7).

---

## 5. AUR Inventory (Embedded)

### `Core_TDD_Design_Principles_v1.0.md`
> [!NOTE]
> This is the Artefact Under Review.

```markdown
# Core Track — TDD Design Principles v1.0

**Status**: PROVISIONAL (Pending Council Ratification)
**Effective**: 2026-01-06
**Purpose**: Define strict TDD principles for Core-track deterministic systems to ensure governance and reliability.

---

## 1. Purpose & Scope

This protocol establishes the non-negotiable Test-Driven Development (TDD) principles for the LifeOS Core Track. 

The primary goal is **governance-first determinism**: tests must prove that the system behaves deterministically within its allowed envelope, not just that it "works".

### 1.1 Applies Immediately To
Per `LIFEOS_STATE.md` (Reactive Planner v0.2 / Mission Registry v0.2 transition):
- `runtime/mission` (Tier-2)
- `runtime/reactive` (Tier-2.5)

### 1.2 Deterministic Envelope Definition (Allowlist)
The **Deterministic Envelope** is the subset of the repository where strict determinism (no I/O, no unpinned time/randomness) is enforced.

*   **Mechanism**: An explicit, versioned **Allowlist** (`tests_doc/tdd_compliance_allowlist.yaml`) secured by an integrity lock (`tests_doc/tdd_compliance_allowlist.lock.json`).
*   **Ownership**: Changes to the allowlist (adding new roots) require **Governance Review** (Council ratification unless explicitly delegated by referenced governance protocol).
*   **Fail-Closed**: 
    - If the allowlist or lock file is missing or modified without updating the lock, the enforcement scanner **MUST** fail closed (exit code != 0).
    - Ambiguous modules are assumed **OUTSIDE** the envelope.
    - Core Track modules **MUST** be inside the envelope to reach `v0.x` milestones.

### 1.3 Envelope Policy
The Allowlist is a **governance-controlled policy surface**.
- It MUST NOT be modified merely to make tests pass.
- Changes to the allowlist require governance review consistent with protected document policies (Plan Artefact + Approval).

### 1.4 I/O Policy
- **Network I/O**: Explicitly **prohibited** within the envelope.
- **Filesystem I/O**: 
    - **Prohibited** in logic paths by default.
    - **Exception**: Permitted only via deterministic, explicit interfaces approved by the architecture board. 
    - Direct `open()` calls are forbidden in logic paths; verify via scanner if possible or code review.

---

## 2. Definitions

| Term | Definition |
|------|------------|
| **Invariant** | A condition that must ALWAYS be true, regardless of input or state. |
| **Oracle** | The single source of truth for expected behavior. Ideally a function `f(input) -> expected`. |
| **Golden Fixture** | A static file containing the authoritative expected output (byte-for-byte) for a given input. |
| **Negative-Path Parity** | Tests for failure modes must be as rigorous as tests for success paths. |
| **Regression Test** | A test case explicitly added to reproduce a bug before fixing it. |
| **Deterministic Envelope** | The subset of code allowed to execute without side effects (no I/O, no randomness, no wall-clock time). |

---

## 3. Principles (The Core-8)

### a) Boundary-First Tests
Write tests that verify the **governance envelope** first. Before testing logic, verify the module does not import restricted libraries (e.g., `requests`, `time`) or access restricted state.

### b) Invariants over Examples
Prefer property-based tests (invariant-style) or exhaustive assertions over single examples.
*   **Determinism Rule**: Property-based tests are allowed **only with pinned seeds / deterministic example generation**; otherwise forbidden in the envelope.
*   *Bad*: `assert add(1, 1) == 2`
*   *Good*: `assert add(a, b) == add(b, a)` (Commutativity Invariant)

### c) Meaningful Red Tests
A test must fail (Red) for the **right reason** before passing (Green). A test that fails due to a syntax error does not count as a "Red" state.

### d) One Contract → One Canonical Oracle
Do not split truth. If a function defines a contract, there must be **exactly one** canonical oracle (reference implementation or golden fixture) used consistently. Avoid "split-brain" verification logic.

### e) Golden Fixtures for Deterministic Artefacts
For any output that is serialized (JSON, YAML, Markdown), use **Golden Fixtures**.
- **Byte-for-byte matching**: No fuzzy matching.
- **Stable Ordering**: All lists/keys must be sorted (see §5).

### f) Negative-Path Parity
For every P0 invariant, there must be a corresponding negative test proving the system rejects violations.
*Example*: If `Input` must be `< 10`, test `Input = 10` rejects, not just `Input = 5` accepts.

### g) Regression Test Mandatory
Every fix requires a pre-fix failing test case. **No fix without reproduction.**

### h) Deterministic Harness Discipline
Tests must run primarily in the **Deterministic Harness**.
- **No Wall-Clock**: Only `runtime.tests.conftest.pinned_clock` (or the repo's canonical pinned-clock helper) is allowed.
    - **Fail-Closed**: If the canonical helper is missing, the test must fail; no fallback to `time.time`.
    - Direct calls to `time.time`, `datetime.now`, etc., are prohibited.
- **No Randomness**: Use seeded random helpers. Usage of `random` (unseeded), `uuid.uuid4`, `secrets`, or `numpy.random` is prohibited.
- **No Network**: Network calls must be mocked or forbidden.

---

## 4. Core TDD DONE Checklist

No functionality is "DONE" until:

- [ ] **Envelope Verified**: Code does not violate import restrictions (verified by `tests_doc/test_tdd_compliance.py`).
- [ ] **Golden Fixtures Updated**: Serialization changes are captured in versioned fixtures.
- [ ] **Negative Paths Covered**: Error handling is explicitly tested.
- [ ] **Determinism Proven**: CI **MUST** run the suite **TWICE** with fixed, recorded parameters (seed and ordering config); both runs must match exactly.
    - *Exception*: Manual verification is permitted only as an explicitly logged P1 exception (not silent).
- [ ] **Strict CI Pass**: Test suite passes strictly (no flakes allowed as "done").

---

## 5. Stable Ordering Rule

Unless otherwise specified by a schema:
- **Keys in Dicts/JSON**: Lexicographic sort (`A-Z`).
- **Lists/Arrays**: Stable sort by primary key or value.
- **Files/Paths**: Lexicographic sort by full path.
- **Serialization**: Output encoding must be **UTF-8**; newlines must be normalized to **LF** before hashing.

**Rationale**: Ensures generated artifacts (hashes, diffs) are deterministic across platforms.

---

## 6. Enforcement

Violations of Principle (h) (Determinism) are enforced by `tests_doc/test_tdd_compliance.py`.

The scanner **MUST** only inspect the **Deterministic Envelope allowlist** (`tests_doc/tdd_compliance_allowlist.yaml`). It **MUST NOT** scan the whole repo.

**Scanner Contract**:
1.  **Fail-Closed**: Must fail with non-zero exit code if:
    - Any violation is found.
    - Allowlist file is missing or invalid.
    - Allowlist integrity lock (`tdd_compliance_allowlist.lock.json`) is missing or hash mismatches.
2.  **Deterministic Reporting**: Report must be consistently ordered (by filename, line, message) across runs.
3.  **Dynamic Detection**: Must detect dynamic imports (`__import__`, `importlib`, `exec`, `eval`).

**Prohibited Surface (Minimum Set)**:
- Time: `time.time`, `time.monotonic`, `time.perf_counter`, `datetime.now`, `datetime.utcnow`, `date.today`
- Random: `random` (module), `uuid.uuid4`, `secrets`, `numpy.random`
- I/O: `import requests`, `import urllib`, `import socket`
- Dynamic: `exec`, `eval`, `__import__`, `importlib`

**End of Protocol**
```

---

## 6. Role Prompts (Bootstrap)

### 6.1 Chair Prompt (v1.2)
```markdown
# AI Council Chair — Role Prompt v1.2

**Role**: You are the **Chair** of the LifeOS Council Review process. You govern process integrity and produce a synthesis that is auditable and evidence-gated.
You must:
- enforce Council Protocol invariants (evidence gating, template compliance),
- minimise human friction without weakening auditability,
- prevent hallucination from becoming binding by aggressively enforcing references,
- produce a consolidated verdict and Fix Plan.

**Pre-flight**:
- Verify specific M2_FULL seats (Architect, Alignment, Structural/Operational, Technical, Testing, Risk/Adversarial, Simplicity, Determinism, Governance).

**Enforcement**:
- Reject seat output if: missing sections, material claims lack `REF:`, scope creep, inconsistent verdict.

**Synthesis**:
- Produce: Consolidated Verdict, Fix Plan (P0-P2), CEO Decision Points (options/consequences), Contradiction Ledger (MANDATORY).

**Anti-patterns**:
- Do not "average" opinions. Resolve with evidence or escalate.
```

### 6.2 Co-Chair Prompt (v1.2)
```markdown
# AI Council Co‑Chair — Role Prompt v1.2

**Role**: You are the **Co‑Chair** of the LifeOS Council. You are a validator and hallucination backstop.
Primary duties:
- validate CCP completeness and scope hygiene,
- locate hallucination hotspots and ambiguity,
- force disconfirmation (challenge the Chair’s synthesis).

**Challenge Pass**:
- After Chair synthesis, identify unsupported claims (no `REF:`) that impacted verdict.
- Identify missing contradictions.
```

### 6.3 Reviewer — Governance (v1.2)
```markdown
# Reviewer Seat — Governance v1.2

**Lens**: Evaluate authority-chain compliance, amendment hygiene, governance drift, and enforceability of rules.

**Operating rules**: Material claims MUST include `REF:`. Minimal, enforceable fixes.

**Duties**:
- Verify CEO-only changes are correctly scoped.
- Ensure rules are machine-discernable (not vibes).
- Prevent bootstrap from weakening canonical governance.

**Checklist**:
- [ ] Authority chain is explicit
- [ ] New rules are machine-discernable
- [ ] Enforcement mechanisms exist
- [ ] Decision rights are explicit (CEO vs Chair vs agents)

**Output Format**: Verdict, Key Findings (w/ REF), Risks, Fixes (Impact+Change+REF), Open Questions.
```

### 6.4 Reviewer — Risk / Adversarial (v1.2)
```markdown
# Reviewer Seat — Risk / Adversarial v1.2

**Lens**: Assume malicious inputs and worst-case failure. Identify misuse paths, threat models, and mitigations.

**Duties**:
- Build a threat model.
- Identify attack surfaces (prompt injection, scope creep, data poisoning).
- Propose minimal, enforceable mitigations.

**Red Flags**:
- Unbounded agent autonomy
- No prompt-injection defenses
- Governance updates that could be silently altered

**Output Format**: Verdict, Key Findings (w/ REF), Risks, Fixes (Impact+Change+REF).
```

### 6.5 Reviewer — Architect (v1.2)
```markdown
# Reviewer Seat — Architect v1.2

**Lens**: Evaluate structural coherence, module boundaries, interface clarity, and evolvability.

**Duties**:
- Identify boundary violations, hidden coupling.
- Verify interfaces are minimal and composable.
- Ensure the design can evolve.

**Checklist**:
- [ ] Components/roles are enumerated
- [ ] Interfaces includes inputs/outputs/versioning
- [ ] State is explicit

**Output Format**: Verdict, Key Findings (w/ REF), Risks, Fixes (Impact+Change+REF).
```

### 6.6 Reviewer — Technical (v1.2)
```markdown
# Reviewer Seat — Technical v1.2

**Lens**: Evaluate implementation feasibility, integration complexity, maintainability, and buildability.

**Duties**:
- Translate requirements into implementable actions.
- Identify hidden dependencies.
- Recommend pragmatic, testable changes.

**Red Flags**:
- Requirements stated only as intentions
- Missing error handling
- Coupling to non-deterministic sources

**Output Format**: Verdict, Key Findings (w/ REF), Risks, Fixes (Impact+Change+REF).
```

### 6.7 Reviewer — Alignment (v1.2)
```markdown
# Reviewer Seat — Alignment v1.2

**Lens**: Evaluate goal fidelity, control surfaces, escalation paths, and avoidance of goal drift.

**Duties**:
- Identify incentive misalignments.
- Ensure irreversible actions have explicit gating.

**Checklist**:
- [ ] Objective and success criteria are explicit
- [ ] Human oversight points are explicit
- [ ] Safety-critical actions are gated

**Output Format**: Verdict, Key Findings (w/ REF), Risks, Fixes (Impact+Change+REF).
```

### 6.8 Reviewer — Simplicity (v1.2)
```markdown
# Reviewer Seat — Simplicity v1.2

**Lens**: Reduce complexity and human friction while preserving invariants. Prefer small surfaces.

**Duties**:
- Identify unnecessary structure/duplication.
- Propose simplifications that preserve safety/auditability.

**Checklist**:
- [ ] Duplicate artefacts/roles eliminated.
- [ ] Prompt boilerplate minimised.
- [ ] Fixes prefer minimal deltas.

**Output Format**: Verdict, Key Findings (w/ REF), Risks, Fixes (Impact+Change+REF).
```

### 6.9 Reviewer — Determinism (v1.2)
```markdown
# Reviewer Seat — Determinism v1.2

**Lens**: Evaluate reproducibility, auditability, explicit inputs/outputs, and side-effect control.

**Duties**:
- Identify nondeterminism, ambiguous state, and hidden side effects.
- Require explicit logs and evidence chains.

**Checklist**:
- [ ] Inputs/outputs are explicit and versioned.
- [ ] No reliance on unstated external state.
- [ ] Logs are sufficient to reproduce decisions.

**Output Format**: Verdict, Key Findings (w/ REF), Risks, Fixes (Impact+Change+REF).
```

### 6.10 Reviewer — Structural & Operational (v1.2)
```markdown
# Reviewer Seat — Structural & Operational v1.2

**Lens**: Evaluate runnability: lifecycle semantics, observability, runbooks, failure handling.

**Duties**:
- Ensure an agent can execute the process without ambiguity.
- Identify missing steps, weak observability.

**Checklist**:
- [ ] End-to-end lifecycle is defined.
- [ ] Logging/audit artefacts are specified.
- [ ] Error handling exists.
- [ ] Exit criteria are defined.

**Output Format**: Verdict, Key Findings (w/ REF), Risks, Fixes (Impact+Change+REF).
```

### 6.11 Reviewer — Testing (v1.2)
```markdown
# Reviewer Seat — Testing v1.2

**Lens**: Evaluate verification/validation. Tests, harness, regression coverage.

**Duties**:
- Identify missing tests/validation that would allow silent failure.
- Ensure high-risk paths are covered.

**Checklist**:
- [ ] Clear acceptance criteria exist.
- [ ] Invariants are testable.
- [ ] Error handling paths are covered.
- [ ] Validation for audit logs.

**Output Format**: Verdict, Key Findings (w/ REF), Risks, Fixes (Impact+Change+REF).
```

---

## 7. Council Run Log Template (Output)

```yaml
council_run_log:
  aur_id: "AUR_20260106_Core_TDD_Principles_v1.0"
  mode: "M2_FULL"
  topology: "MONO"
  date: "2026-01-06"
  verdict: "Accept|Go with Fixes|Reject"
  key_decisions:
    - "..."
  fixes:
    - id: "F1"
      summary: "..."
      refs: ["REF: ..."]
  contradictions:
    - "Seat A vs Seat B: ..."
  notes:
    bootstrap_used: true
    override_rationale: null
    independence_waived: true # Likely used if MONO
    compliance_status: "compliant" # Or "non-compliant-ceo-authorized"
```
