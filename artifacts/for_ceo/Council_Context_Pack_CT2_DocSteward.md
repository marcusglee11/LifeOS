# Council Context Pack — CT-2 DOC_STEWARD Activation

```yaml
# CCP YAML Header (Machine-Discernable) — Council Protocol v1.1 §4
council_run:
  aur_id: "AUR_20260105_CT2_DOCSTEWARD"
  aur_type: "governance"
  change_class: "new"
  touches:
    - "tier_activation"
    - "prompts"
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
  # COMPUTED: touches includes "tier_activation" → M2_FULL

model_plan_v1:
  topology: "MONO"
  models:
    primary: "Gemini 2.5 Pro"
    adversarial: "Gemini 2.5 Pro"
    implementation: "Gemini 2.5 Pro"
    governance: "Gemini 2.5 Pro"
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

---

## 0. AUR Inventory

| AUR ID | Path | SHA256 |
|--------|------|--------|
| `AUR_20260105_CT2_DOCSTEWARD` | `artifacts/for_ceo/CT2_Activation_Packet_DocSteward_G3.md` | `B9A6AF3627170EAFFE4F1A5B5BF03BCEBF6A5C14DE81B4224BBD3ACDE6E4732F` |

---

## 1. Objective & Success Criteria

**Objective**: Conduct a binding Full Council review (M2_FULL) to determine whether the DOC_STEWARD role should be activated for INDEX_UPDATE missions under the specified constraints.

**Success Criteria**:
1. Council produces a consolidated verdict: Accept / Go with Fixes / Reject
2. All material claims in reviewer outputs include `REF:` citations
3. Contradiction Ledger is produced (mandatory for M2)
4. Co-Chair challenge pass is executed
5. Council Run Log is completed

---

## 2. Scope Boundaries

**In Scope**:
- Ratification of `DOC_STEWARD_Constitution_v1.0.md`
- Approval of `Document_Steward_Protocol_v1.0.md` (Section 10: Automated Interface)
- Activation of DOC_STEWARD role for `INDEX_UPDATE` missions only

**Out of Scope**:
- Expansion to other mission types (code/refactor)
- Enablement of live commits (must remain `--dry-run` or monitored until G4)
- Changes to existing manual stewardship rules

---

## 3. Invariants (Non-Negotiables)

1. **Fail-Closed**: If any hunk search block is missing, the orchestrator must FAIL
2. **Audit-Grade Ledger**: Full hashes (before/diff/after), raw logs, full findings
3. **True Post-Change Verification**: `git apply` to temp workspace + semantic checks on result
4. **CEO Control**: No autonomous commits without explicit CEO approval
5. **Evidence Gating**: All claims require `REF:` citations per Protocol v1.1 §2.2

---

## 4. Execution Instructions

### 4.1 Mode & Topology
- **Mode**: M2_FULL (triggered by `touches includes "tier_activation"`)
- **Topology**: MONO (single model)
- **Independence Rule**: MONO does not provide seat independence. Therefore:
  - Co-Chair challenge pass is MANDATORY
  - Contradiction Ledger is MANDATORY

### 4.2 Seats to Execute (M2_FULL)
1. Chair (synthesis)
2. Co-Chair (validation + challenge)
3. Architect
4. Alignment
5. Structural & Operational
6. Technical
7. Testing
8. Risk / Adversarial
9. Simplicity
10. Determinism
11. Governance

### 4.3 MONO Run Order
1. Chair pre-flight (validate CCP header)
2. Co-Chair validation (packet audit + prompt blocks)
3. Execute seats sequentially (as separate sections)
4. Chair synthesis + Fix Plan + Contradiction Ledger
5. Co-Chair challenge to synthesis (hallucination hunt)
6. Chair finalises Council Run Log

---

## 5. Document Inventory (Stable Ordering by Path)

| Path | Document Name | SHA256 |
|------|---------------|--------|
| `docs/02_protocols/AI_Council_Procedural_Spec_v1.0.md` | AI_Council_Procedural_Spec_v1.0.md | `51B99074CEAF66E0424D884FB2EF36874E58EA7BABB4E70B081593492A389F15` |
| `docs/02_protocols/Council_Context_Pack_Schema_v0.2.md` | Council_Context_Pack_Schema_v0.2.md | `7B2E25139C4FEEC330FB15B0B9F457F4BFC3DA83DC46100AAEF34E22AB4AC9D3` |
| `docs/02_protocols/Council_Protocol_v1.1.md` | Council_Protocol_v1.1.md | `CE38823FE66163B67B7481EF89EB6BAB83CC011A9A515C60AEC14B300767E819` |
| `docs/09_prompts/v1.2/chair_prompt_v1.2.md` | chair_prompt_v1.2.md | `6A6E6DC2585A5527C69C8D5B138CB234D203FCB102A9B80AA10A843AB2F561B1` |
| `docs/09_prompts/v1.2/cochair_prompt_v1.2.md` | cochair_prompt_v1.2.md | `307E2845F5A6C148522DE8FDDA68D1BE28E61B72CA8D5D6986AB263788F4216F` |
| `docs/09_prompts/v1.2/reviewer_alignment_v1.2.md` | reviewer_alignment_v1.2.md | `CA9F92779D2FAD246FB72251CA1545E75B377F67D200A4C515418990E07FFAE7` |
| `docs/09_prompts/v1.2/reviewer_architect_v1.2.md` | reviewer_architect_v1.2.md | `6DEBFE4DC87FF54FD4022B01DFE4707F926D0B365DD690061E3B46E257A942DC` |
| `docs/09_prompts/v1.2/reviewer_determinism_v1.2.md` | reviewer_determinism_v1.2.md | `9F110363EBA779EBE07767A30BEB83CA8D26733C912C6C92F8420D46123F8690` |
| `docs/09_prompts/v1.2/reviewer_governance_v1.2.md` | reviewer_governance_v1.2.md | `D3102BEA99A4F744660C58967F9E1B90DB047D17927C32CC62C537FF05555D31` |
| `docs/09_prompts/v1.2/reviewer_l1_unified_v1.2.md` | reviewer_l1_unified_v1.2.md | `22F4438A4F815A91C86E5CD05B3CAC816CD47DE053989E9275C6095801BD6925` |
| `docs/09_prompts/v1.2/reviewer_risk_adversarial_v1.2.md` | reviewer_risk_adversarial_v1.2.md | `B9B90FB268F7AB8BA114901AD82B322C025F1AF4BF6EAB0E0059305B00B2A5DE` |
| `docs/09_prompts/v1.2/reviewer_simplicity_v1.2.md` | reviewer_simplicity_v1.2.md | `5D4AE23EA3A96BAB3E4DB0DF921C8A623CD4B0E42C451B1C7E470748FC53D19D` |
| `docs/09_prompts/v1.2/reviewer_structural_operational_v1.2.md` | reviewer_structural_operational_v1.2.md | `D1B7030E9C0953F07025B3EAD73798AE7459A547F934F32547DEBAF2C0826653` |
| `docs/09_prompts/v1.2/reviewer_technical_v1.2.md` | reviewer_technical_v1.2.md | `20B53D07D9DACF3DF0148D797D98EF5AAEA386BAD43A348998DD2EF1451C247A` |
| `docs/09_prompts/v1.2/reviewer_testing_v1.2.md` | reviewer_testing_v1.2.md | `6E8B0620CD1DD2D4C5499F31CFB704D98B1BE51C1264CF1CFDAF20938E9EA6BE` |

---

## 6. Council Protocol v1.1 (Excerpt: L1–L100)

> REF: `docs/02_protocols/Council_Protocol_v1.1.md#L1-L100`

```markdown
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
1. Provide high-quality reviews, ideation, and advice using explicit lenses ("seats").
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

---

## 2. Non‑negotiable invariants

### 2.1 Determinism and auditability
- Every council run must produce a **Council Run Log** with:
  - AUR identifier(s) and hash(es) (when available),
  - selected mode and topology,
  - model plan (which model ran which seats, even if "MONO"),
  - a synthesis verdict and explicit fix plan.

### 2.2 Evidence gating
- Any *material* claim (i.e., claim that influences verdict, risk rating, or fix plan) must include an explicit AUR reference.
- Claims without evidence must be labelled **ASSUMPTION** and must not be used as the basis for a binding verdict or fix, unless explicitly accepted by the CEO.

### 2.3 Template compliance
- Seat outputs must follow the required output schema (Section 7).
- The Chair must reject malformed outputs and request correction.

### 2.4 Human control (StepGate)
- The council does not infer "go". Any gating or irreversible action requires explicit CEO approval in the relevant StepGate, if StepGate is in force.
```

---

## 7. Reviewer Output Template (from Protocol v1.1 §7)

> REF: `docs/02_protocols/Council_Protocol_v1.1.md#L241-L261`

Every seat output **MUST** be structured as follows:

```markdown
### 1) Verdict
One of: **Accept / Go with Fixes / Reject**

### 2) Key Findings (3–10 bullets)
- Each bullet MUST include at least one `REF:` citation to the AUR.
- Prefer findings that materially change the verdict or Fix Plan.

### 3) Risks / Failure Modes (as applicable)
- Each item MUST include `REF:` or be labeled **ASSUMPTION**.
- For **ASSUMPTION**, include: what evidence would resolve it.

### 4) Fixes (prioritised)
- Use IDs `F1`, `F2`, ...
- Each fix MUST include:
  - **Impact** (what it prevents/enables),
  - **Minimal change** (smallest concrete action),
  - **REF:** citation(s).

### 5) Open Questions (if any)
- Only questions that block an evidence-backed verdict/fix.

### 6) Confidence
Low | Medium | High

### 7) Assumptions
Explicit list; do not hide assumptions in prose.
```

**Reference Format** (use one of):
- `REF: <AUR_ID>:<file>:§<section>`
- `REF: <AUR_ID>:<file>:#Lx-Ly`
- `REF: git:<commit>:<path>#Lx-Ly`

---

## 8. Role Prompt Inventory (v1.2)

All prompts located at `docs/09_prompts/v1.2/`:

| Role | File | Purpose |
|------|------|---------|
| **Chair** | `chair_prompt_v1.2.md` | Governs process integrity; synthesizes verdict + Fix Plan |
| **Co-Chair** | `cochair_prompt_v1.2.md` | Validates CCP; hallucination backstop; challenge pass |
| **Architect** | `reviewer_architect_v1.2.md` | Structural coherence, module boundaries, evolvability |
| **Alignment** | `reviewer_alignment_v1.2.md` | Goal fidelity, control surfaces, escalation paths |
| **Structural & Operational** | `reviewer_structural_operational_v1.2.md` | Lifecycle semantics, runbooks, failure handling |
| **Technical** | `reviewer_technical_v1.2.md` | Implementation feasibility, integration, maintainability |
| **Testing** | `reviewer_testing_v1.2.md` | Verification/validation adequacy, coverage |
| **Risk / Adversarial** | `reviewer_risk_adversarial_v1.2.md` | Threat models, misuse paths, mitigations |
| **Simplicity** | `reviewer_simplicity_v1.2.md` | Complexity reduction, CEO bottleneck minimization |
| **Determinism** | `reviewer_determinism_v1.2.md` | Reproducibility, auditability, side-effect control |
| **Governance** | `reviewer_governance_v1.2.md` | Authority chain compliance, amendment hygiene |
| **L1 Unified** | `reviewer_l1_unified_v1.2.md` | Fast-mode single reviewer (M0_FAST only) |

---

## 9. CT-2 Rubric for Activation Decisions

Per Council Protocol v1.1 §2, the council must evaluate:

1. **Evidence gating** (§2.2): Does the activation packet include REF citations for all material claims?
2. **Invariant compliance** (§2.1): Does the proposal preserve LifeOS invariants?
3. **Safety**: Are fail-closed mechanisms proven?
4. **Determinism**: Are hashes verifiable? Are outputs reproducible?
5. **Scope boundaries**: Are non-goals explicit?

**CT-2 Decision Question**: Should the DOC_STEWARD role be activated for INDEX_UPDATE missions under the specified constraints?

---

## 10. Council Run Log Template

```yaml
council_run_log:
  aur_id: "AUR_20260105_CT2_DOCSTEWARD"
  mode: "M2_FULL"
  topology: "MONO"
  models_used:
    - role: "Chair"
      model: "Gemini 2.5 Pro"
    - role: "CoChair"
      model: "Gemini 2.5 Pro"
    - role: "Architect"
      model: "Gemini 2.5 Pro"
    - role: "Alignment"
      model: "Gemini 2.5 Pro"
    - role: "StructuralOperational"
      model: "Gemini 2.5 Pro"
    - role: "Technical"
      model: "Gemini 2.5 Pro"
    - role: "Testing"
      model: "Gemini 2.5 Pro"
    - role: "RiskAdversarial"
      model: "Gemini 2.5 Pro"
    - role: "Simplicity"
      model: "Gemini 2.5 Pro"
    - role: "Determinism"
      model: "Gemini 2.5 Pro"
    - role: "Governance"
      model: "Gemini 2.5 Pro"
  date: "2026-01-05"
  verdict: "PENDING"
  key_decisions: []
  fixes: []
  contradictions: []
  notes:
    bootstrap_used: false
    override_rationale: null
```

---

## Pack Metadata

- **Pack SHA256**: `D7059EA9EF3E17EB48D9F08C245FC2E68F4B12E3AA026FD0DF12DAD7820DF427`
- **Generated by**: Antigravity (Stewardship Mission)
- **Date**: 2026-01-05

---

*END OF COUNCIL CONTEXT PACK*
