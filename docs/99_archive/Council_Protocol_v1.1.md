# Council Protocol v1.1 (Amendment)

**System**: LifeOS Governance Hub  
**Status**: Proposed for Canonical Promotion  
**Effective date**: 2026-01-05 (upon CEO promotion)  
**Amends**: Council Protocol v1.0  
**Change type**: Constitutional amendment (CEO-only)

---

## 0. Purpose and authority

This document defines the binding constitutional procedure for conducting **Council Reviews** within LifeOS.

**Authority**
- This protocol is binding across all projects, agents, and models operating under the LifeOS governance system.
- Only the CEO may amend this document.
- Any amendment must be versioned, auditable, and explicitly promoted to canonical.

**Primary objectives**
1. Provide high-quality reviews, ideation, and advice using explicit lenses (“seats”).
2. When practical, use diversified AI models to reduce correlated error and improve the efficient frontier of review quality vs. cost.
3. Minimise human friction while preserving auditability and control.

---

## 1. Definitions

**AUR (Artefact Under Review)**  
The specific artefact(s) being evaluated (document, spec, code, plan, ruling, etc.).

**Council Context Pack (CCP)**  
A packet containing the AUR and all run metadata needed to execute a council review deterministically.

**Seat**  
A defined reviewer role/lens with a fixed output schema.

**Mode**  
A rigor profile selected via deterministic rules: M0_FAST, M1_STANDARD, M2_FULL.

**Topology**  
The execution layout: MONO (single model sequential), HYBRID (chair/co-chair + some external), DISTRIBUTED (per-seat external).

**Evidence-by-reference**  
A rule that major claims and proposed fixes must cite the AUR via explicit references.

---

## 2. Non‑negotiable invariants

### 2.1 Determinism and auditability
- Every council run must produce a **Council Run Log** with:
  - AUR identifier(s) and hash(es) (when available),
  - selected mode and topology,
  - model plan (which model ran which seats, even if “MONO”),
  - a synthesis verdict and explicit fix plan.

### 2.2 Evidence gating
- Any *material* claim (i.e., claim that influences verdict, risk rating, or fix plan) must include an explicit AUR reference.
- Claims without evidence must be labelled **ASSUMPTION** and must not be used as the basis for a binding verdict or fix, unless explicitly accepted by the CEO.

### 2.3 Template compliance
- Seat outputs must follow the required output schema (Section 7).
- The Chair must reject malformed outputs and request correction.

### 2.4 Human control (StepGate)
- The council does not infer “go”. Any gating or irreversible action requires explicit CEO approval in the relevant StepGate, if StepGate is in force.
    
### 2.5 Closure Discipline (G-CBS)
- **DONE requires Validation**: A "Done" or "Go" ruling is VALID ONLY if accompanied by a G-CBS compliant closure bundle that passes `validate_closure_bundle.py`.
- **No Ad-Hoc Bundles**: Ad-hoc zips are forbidden. All closures must be built via `build_closure_bundle.py`.
- **Max Cycles**: A prompt/closure cycle is capped at 2 attempts. Residual issues must then be waived (with debt record) or blocked.

---

## 3. Inputs (mandatory)

Every council run MUST begin with a complete CCP containing:

1. **AUR package**
   - AUR identifier(s) (file names, paths, commits if applicable),
   - artefact contents attached or linked,
   - any supporting context artefacts (optional but explicit).

2. **Council objective**
   - what is being evaluated (e.g., “promote to canonical”, “approve build plan”, “stress-test invariants”),
   - success criteria.

3. **Scope boundaries**
   - what is in scope / out of scope,
   - any non‑negotiable constraints (“invariants”).

4. **Run metadata (machine‑discernable)**
   - the CCP YAML header (Section 4).

The Chair must verify all four exist prior to initiating reviews.

---

## 4. Council Context Pack (CCP) header schema (machine‑discernable)

The CCP MUST include a YAML header with the following minimum keys:

```yaml
council_run:
  aur_id: "AUR_YYYYMMDD_<slug>"
  aur_type: "governance|spec|code|doc|plan|other"
  change_class: "new|amend|refactor|hygiene|bugfix"
  touches:
    - "governance_protocol"
    - "tier_activation"
    - "runtime_core"
    - "interfaces"
    - "prompts"
    - "tests"
    - "docs_only"
  blast_radius: "local|module|system|ecosystem"
  reversibility: "easy|moderate|hard"
  safety_critical: true|false
  uncertainty: "low|medium|high"
  override:
    mode: null|"M0_FAST"|"M1_STANDARD"|"M2_FULL"
    topology: null|"MONO"|"HYBRID"|"DISTRIBUTED"
    rationale: null|"..."

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
  topology: "MONO|HYBRID|DISTRIBUTED"
  models:
    primary: "<model_name>"
    adversarial: "<model_name>"
    implementation: "<model_name>"
    governance: "<model_name>"
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
```

Notes:
- In MONO topology, `constraints.mono_mode.all_roles_use` governs; `role_to_model` remains required for logging consistency.

---

## 5. Seats (roles) and responsibilities

### 5.1 Council officers
**Chair (mandatory)**
- Assembles CCP, enforces protocol invariants, manages topology, rejects malformed outputs, synthesizes verdict and Fix Plan.

**Co‑Chair (mandatory for M1/M2; optional for M0)**
- Validates CCP completeness, challenges Chair synthesis, hunts hallucinations, and produces concise role prompt blocks for execution.

### 5.2 Reviewer seats (canonical seat map)

**Architect Reviewer**  
Structural coherence and long-horizon architecture.

**Alignment Reviewer**  
Goal fidelity, control surfaces, incentives, human oversight.

**Structural & Operational Reviewer**  
Process integrity, lifecycle semantics, operational failure modes.

**Technical Reviewer**  
Implementation feasibility, integration, maintainability (for code/spec).

**Testing Reviewer (NEW)**  
Test strategy, verification, or validation plan adequacy.

**Risk / Adversarial Reviewer**  
Adversarial analysis, threat models, misuse and failure scenarios.

**Simplicity Reviewer**  
Complexity reduction, sharp boundaries, minimal moving parts.

**Determinism Reviewer**  
Determinism, auditability, reproducibility, side-effect control.

**Governance Reviewer (NEW)**  
Authority chain compliance, amendment hygiene, governance drift detection.

### 5.3 Fast-mode seat
**L1 Unified Reviewer** (permitted in M0_FAST only)  
Single integrated review that combines multiple lenses into one output.

---

## 6. Modes and topologies

### 6.1 Mode selection (binding)
- Mode is chosen deterministically from CCP header rules unless overridden.
- If overridden, the override must include rationale in the CCP header.

### 6.2 Topology selection (binding)
Topology can be:
- **MONO**: single model executes all seats sequentially.
- **HYBRID**: Chair/Co-Chair on one model; selected seats executed externally.
- **DISTRIBUTED**: seats executed externally (per-seat), Chair synthesizes.

### 6.3 Independence rule (hallucination mitigation)
**Critical point**: MONO topology does **not** provide independence between seats.  
Therefore:

- For **M1_STANDARD** and **M2_FULL**:
  1) A **distinct Co‑Chair challenge pass** is mandatory (even if same model).
  2) The Chair must produce a **Contradiction Ledger** (Section 8.3).
- For **M2_FULL**, if any of the following are true:
  - touches includes governance_protocol OR tier_activation OR runtime_core, OR
  - safety_critical == true, OR
  - uncertainty == high and blast_radius != local,
  then at least one of **Risk/Adversarial** or **Governance** seats SHOULD be executed on an independent model (different vendor/model family) when practical.
  - If not practical, the CCP must record: `override.rationale` explaining why independence was not used.

---

## 7. Required output schema (per seat)

Every seat output MUST be structured as follows:

1. **Verdict**: Accept | Go with Fixes | Reject  
2. **Key findings (3–10 bullets)**  
   - Each bullet must include at least one `REF:` citation.
3. **Risks / failure modes (as applicable)**  
   - Each must include `REF:` or explicit **ASSUMPTION**.
4. **Fixes (prioritised)**  
   - Format: `F1`, `F2`, ... with impact and `REF:`.
5. **Open questions (if any)**  
6. **Confidence**: Low | Medium | High  
7. **Assumptions** (explicit list)

### 7.1 Reference format
Use one of:
- `REF: <AUR_ID>:<file>:§<section>`
- `REF: <AUR_ID>:<file>:#Lx-Ly` (if line numbers exist)
- `REF: git:<commit>:<path>#Lx-Ly` (for code)

---

## 8. Council sequence (deterministic)

**Step 0 — CCP Assembly**
- Chair assembles CCP and selects mode/topology per CCP rules.
- Co‑Chair validates CCP (mandatory for M1/M2).

**Step 1 — Seat execution**
- Execute seats according to topology.
- Chair rejects malformed outputs and re-requests.

**Step 2 — Synthesis**
- Chair produces:
  - Consolidated verdict,
  - Fix Plan (prioritised),
  - Decision points requiring CEO input,
  - Contradiction Ledger (mandatory M1/M2).

**Step 3 — CEO decision (if required)**
- CEO accepts/rejects/defers fix plan and any amendments.

**Step 4 — Close-out**
- Council Run Log is finalised and attached to the CCP.

### 8.1 Contradiction Ledger (mandatory in M1/M2)
Chair must list:
- conflicts between seats (e.g., “Architect recommends X; Governance flags authority conflict”),
- resolution approach: evidence-backed choice OR “needs CEO decision”.

---

## 9. Bootstrap clause (to prevent blockage)

If canonical prompt artefacts or canonical governance artefacts cannot be fetched:
- Council may run under a **BOOTSTRAP CCP** that embeds the required prompt snapshots inline.
- The run MUST include a fix item: “Restore canonical artefacts and re-run validation (if required).”
- BOOTSTRAP runs are auditable but are not grounds to claim “canonical compliance” unless the missing canon is restored and validated.

---

## 10. Amendment record (this document)

This v1.1 amendment introduces:
- Machine-discernable CCP header schema (mode + topology + model plan),
- Independence rule for hallucination mitigation,
- New seats: Governance Reviewer and Testing Reviewer,
- Explicit “Bootstrap” clause.

