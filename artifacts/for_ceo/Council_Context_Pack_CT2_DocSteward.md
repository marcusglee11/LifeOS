# Council Context Pack — CT-2 DOC_STEWARD Activation

**Purpose**: Binding Full Council Review for CT-2 DOC_STEWARD Activation
**Date**: 2026-01-05
**Target AUR**: [CT2_Activation_Packet_DocSteward_G3.md](file:///c:/Users/cabra/Projects/LifeOS/artifacts/for_ceo/CT2_Activation_Packet_DocSteward_G3.md)

---

## 1. Document Inventory (Stable Ordering by Path)

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

## 2. Council Protocol v1.1 (Excerpt: L1–L100)

```markdown
1: # Council Protocol v1.1 (Amendment)
2: 
3: **System**: LifeOS Governance Hub  
4: **Status**: Proposed for Canonical Promotion  
5: **Effective date**: 2026-01-05 (upon CEO promotion)  
6: **Amends**: Council Protocol v1.0  
7: **Change type**: Constitutional amendment (CEO-only)
8: 
9: ---
10: 
11: ## 0. Purpose and authority
12: 
13: This document defines the binding constitutional procedure for conducting **Council Reviews** within LifeOS.
14: 
15: **Authority**
16: - This protocol is binding across all projects, agents, and models operating under the LifeOS governance system.
17: - Only the CEO may amend this document.
18: - Any amendment must be versioned, auditable, and explicitly promoted to canonical.
19: 
20: **Primary objectives**
21: 1. Provide high-quality reviews, ideation, and advice using explicit lenses ("seats").
22: 2. When practical, use diversified AI models to reduce correlated error and improve the efficient frontier of review quality vs. cost.
23: 3. Minimise human friction while preserving auditability and control.
24: 
25: ---
26: 
27: ## 1. Definitions
28: 
29: **AUR (Artefact Under Review)**  
30: The specific artefact(s) being evaluated (document, spec, code, plan, ruling, etc.).
31: 
32: **Council Context Pack (CCP)**  
33: A packet containing the AUR and all run metadata needed to execute a council review deterministically.
34: 
35: **Seat**  
36: A defined reviewer role/lens with a fixed output schema.
37: 
38: **Mode**  
39: A rigor profile selected via deterministic rules: M0_FAST, M1_STANDARD, M2_FULL.
40: 
41: **Topology**  
42: The execution layout: MONO (single model sequential), HYBRID (chair/co-chair + some external), DISTRIBUTED (per-seat external).
43: 
44: ---
45: 
46: ## 2. Non‑negotiable invariants
47: 
48: ### 2.1 Determinism and auditability
49: - Every council run must produce a **Council Run Log** with:
50:   - AUR identifier(s) and hash(es) (when available),
51:   - selected mode and topology,
52:   - model plan (which model ran which seats, even if "MONO"),
53:   - a synthesis verdict and explicit fix plan.
54: 
55: ### 2.2 Evidence gating
56: - Any *material* claim (i.e., claim that influences verdict, risk rating, or fix plan) must include an explicit AUR reference.
57: - Claims without evidence must be labelled **ASSUMPTION** and must not be used as the basis for a binding verdict or fix, unless explicitly accepted by the CEO.
58: 
59: ### 2.3 Template compliance
60: - Seat outputs must follow the required output schema (Section 7).
61: - The Chair must reject malformed outputs and request correction.
62: 
63: ### 2.4 Human control (StepGate)
64: - The council does not infer "go". Any gating or irreversible action requires explicit CEO approval in the relevant StepGate, if StepGate is in force.
65: 
66: ---
67: 
68: ## 3. Inputs (mandatory)
69: 
70: Every council run MUST begin with a complete CCP containing:
71: 
72: 1. **AUR package**
73:    - AUR identifier(s) (file names, paths, commits if applicable),
74:    - artefact contents attached or linked,
75:    - any supporting context artefacts (optional but explicit).
76: 
77: 2. **Council objective**
78:    - what is being evaluated (e.g., "promote to canonical", "approve build plan", "stress-test invariants"),
79:    - success criteria.
80: 
81: 3. **Scope boundaries**
82:    - what is in scope / out of scope,
83:    - any non‑negotiable constraints ("invariants").
84: 
85: 4. **Run metadata (machine‑discernable)**
86:    - the CCP YAML header (Section 4).
87: 
88: The Chair must verify all four exist prior to initiating reviews.
89: 
90: ---
91: 
92: ## 4. Council Context Pack (CCP) header schema (machine‑discernable)
93: 
94: The CCP MUST include a YAML header with the following minimum keys:
95: 
96: ```yaml
97: council_run:
98:   aur_id: "AUR_YYYYMMDD_<slug>"
99:   aur_type: "governance|spec|code|doc|plan|other"
100:   change_class: "new|amend|refactor|hygiene|bugfix"
```

---

## 3. AI Council Procedural Spec v1.0 (Excerpt: L1–L100)

```markdown
1: # AI Council — Procedural Specification v1.0
2: 
3: **System**: LifeOS Governance Hub  
4: **Status**: Proposed for Canonical Promotion (operational layer)  
5: **Effective date**: 2026-01-05 (upon CEO promotion)  
6: **Scope**: Runbook for executing Council Protocol v1.1
7: 
8: ---
9: 
10: ## 1. Purpose
11: 
12: This document operationalises **Council Protocol v1.1**. It specifies how to:
13: - assemble a Council Context Pack (CCP),
14: - select mode/topology deterministically,
15: - run council reviews under MONO, HYBRID, or DISTRIBUTED topologies,
16: - enforce evidence gating and output templates,
17: - produce audit-ready Council Run Logs.
18: 
19: ---
20: 
21: ## 2. Inputs
22: 
23: You need:
24: 1. AUR artefact(s) (files, diffs, or pasted content).
25: 2. CCP header YAML (machine-discernable).
26: 3. Seat prompt artefacts (Chair, Co-Chair, reviewers).
27: 
28: If canonical artefacts are unavailable, use **BOOTSTRAP CCP** (Protocol §9).
29: 
30: ---
31: 
32: ## 3. CCP assembly (deterministic)
33: 
34: ### 3.1 CCP structure
35: A CCP is a single packet containing:
36: 
37: 1) YAML header (required)  
38: 2) AUR inventory (required)  
39: 3) Objective + scope boundaries (required)  
40: 4) Attachments or embedded content (required)  
41: 5) Execution instructions (topology + prompts)  
42: 6) Output collection plan (where seat outputs go)  
43: 7) Council Run Log template (blank, to fill)
44: 
45: ---
46: 
47: ## 4. Mode selection (mechanical)
48: 
49: Apply `mode_selection_rules_v1` from CCP header:
50: - If override provided, record rationale.
51: - Otherwise compute mode.
52: 
53: Operational guideline:
54: - M0_FAST: L1 Unified only.
55: - M1_STANDARD: Chair + Co-Chair + 3–5 key seats.
56: - M2_FULL: Chair + Co-Chair + all canonical seats (9).
57: 
58: ---
59: 
60: ## 5. Topology selection (mechanical)
61: 
62: ### 5.1 MONO topology (single-model run)
63: Use when:
64: - copy/paste friction must be minimal, or
65: - external models are unavailable, or
66: - you are doing an initial pass before distributing.
67: 
68: **Important**: MONO does not create independence. Therefore:
69: - For M1/M2, you must run the Co‑Chair **challenge pass** as a separate pass (even if same model).
70: - Produce a Contradiction Ledger.
71: 
72: #### MONO run order (recommended)
73: 1) Chair pre-flight (assemble CCP, validate header)
74: 2) Co-Chair validation (packet audit + prompt blocks)
75: 3) Execute seats sequentially (as separate sections)
76: 4) Chair synthesis + Fix Plan + Contradiction Ledger
77: 5) Co-Chair challenge to synthesis (hallucination hunt)
78: 6) Chair finalises Council Run Log
79: 
80: ### 5.2 HYBRID topology (chair/co-chair + selective external seats)
81: Use when:
82: - you want some independence, but not full distribution.
83: 
84: Recommended externalisation:
85: - Risk/Adversarial seat (independent model)
86: - Governance seat (independent model)
87: - Technical/Testing seats (implementation-focused model)
88: 
89: Chair/Co-Chair remain on `models.primary`.
90: 
91: ### 5.3 DISTRIBUTED topology (per-seat external)
92: Use when:
93: - stakes are high (often M2),
94: - you want maximum diversification.
95: 
96: Rule of thumb:
97: - at minimum, put Risk or Governance on a different model family for independence when practical.
98: 
99: ---
100: 
```

---

## 4. Reviewer Output Template (from Protocol v1.1 §7)

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

## 5. Role Prompt Inventory (v1.2)

All prompts located in `docs/09_prompts/v1.2/`:

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

## 6. CT-2 Rubric for Activation Decisions

Per Council Protocol v1.1 §2, the council must evaluate:

1. **Evidence gating**: Does the activation packet include REF citations for all material claims?
2. **Invariant compliance**: Does the proposal preserve LifeOS invariants?
3. **Safety**: Are fail-closed mechanisms proven?
4. **Determinism**: Are hashes verifiable? Are outputs reproducible?
5. **Scope boundaries**: Are non-goals explicit?

**CT-2 Decision Question**: Should the DOC_STEWARD role be activated for INDEX_UPDATE missions under the specified constraints?

---

## Pack Metadata

- **Pack SHA256**: `D6494E66CCDB7DC0DDF94BCEE6DC25942FC668B120F41CC9E143E6030DA8C162`
- **Generated by**: Antigravity (Stewardship Mission)
- **Date**: 2026-01-05 12:45 UTC+11

---

*END OF COUNCIL CONTEXT PACK*
