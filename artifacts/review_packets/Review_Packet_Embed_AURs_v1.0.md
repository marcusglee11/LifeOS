---
packet_id: "550e8400-e29b-41d4-a716-446655440001"
packet_type: "REVIEW_PACKET"
target: "Council"
topic: "Embedding AURs into Council Context Packs"
version: "1.0"
date: "2026-01-05"
---

# Review Packet: Embedding AURs into Council Context Packs v1.0

## I. Executive Summary
Successfully created and populated two Council Context Packs (CCPs) for upcoming AI model reviews.
1. `CCP_Council_Process_Review_v1.0.md`: Fully embedded with Governance and Routing protocols.
2. `CCP_Agent_Communication_Review_v1.0.md`: Fully embedded with 5 Schema/Protocol AURs and Authority Chain contexts.
Overcame significant token limitations and tool truncation issues to ensuring 100% content integrity for the AI Council.

## II. Issue Catalogue
| Issue ID | Description | Resolution |
|----------|-------------|------------|
| TRUNC-01 | `multi_replace_file_content` truncated large Schema/Template insertions | Performed surgical repairs (Batches A & B) to re-inject missing blocks |
| OFFSET-01 | Line numbers shifted significantly during iterative embedding | Used dynamic `view_file` to locate new placeholder positions |
| SIZE-01 | CCP-2 exceeded typical context limits | Verified final file integrity (~3800 lines); deemed necessary for Council completeness |

## III. Acceptance Criteria
- [x] CCP-1 contains full `Governance_Protocol` and `Intent_Routing_Rule`.
- [x] CCP-2 contains full `lifeos_packet_schemas` and `templates`.
- [x] CCP-2 contains full `Build_Handoff`, `Build_Artifact`, `DOC_STEWARD`, `Antigravity_Spec`.
- [x] All `{{AUR_*}}` and `{{CTX_*}}` placeholders removed.
- [x] No "truncated" comments left in files.

## IV. Artifacts Produced
- `artifacts/context_packs/CCP_Council_Process_Review_v1.0.md`
- `artifacts/context_packs/CCP_Agent_Communication_Review_v1.0.md`

---

## Appendix: Flattened Code Snapshots

### File: artifacts/context_packs/CCP_Council_Process_Review_v1.0.md
```markdown
# Council Context Pack: Council Process Review v1.0

---
council_run:
  aur_id: "AUR_20260105_council_process_review"
  aur_type: "governance"
  change_class: "amend"
  touches:
    - "governance_protocol"
    - "council_protocol"
  blast_radius: "system"
  reversibility: "moderate"
  safety_critical: false
  uncertainty: "medium"
  override:
    mode: "M2_FULL"
    topology: "DISTRIBUTED"
    rationale: "Multi-model council for maximum independence; governance protocol scope mandates M2_FULL"

mode_selection_rules_v1:
  default: "M1_STANDARD"
  applied_mode: "M2_FULL"
  trigger_reason: "touches includes governance_protocol"

model_plan_v1:
  topology: "DISTRIBUTED"
  models:
    primary: "<CEO_TO_ASSIGN>"
    adversarial: "<CEO_TO_ASSIGN>"
    implementation: "<CEO_TO_ASSIGN>"
    governance: "<CEO_TO_ASSIGN>"
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
---

## 1. OBJECTIVE

**Review Type**: GOVERNANCE  
**Council Objective**: Evaluate the LifeOS council protocol stack for internal consistency, version alignment, and operational completeness.

**Success Criteria**:
1. All version references are consistent across documents
2. CCP schema v0.2 is evaluated for v1.0 promotion readiness
3. New council seats (Testing, Governance Reviewer) have adequate definitions
4. Independence rules have appropriate enforcement mechanisms
5. Clear fix plan produced for any gaps

---

## 2. SCOPE BOUNDARIES

### In Scope
- Council Protocol v1.1 (the constitutional procedure for all council reviews)
- AI Council Procedural Spec v1.0 (operational runbook)
- Council Context Pack Schema v0.2 (this schema's own maturity)
- Council Invocation Runtime Binding Spec v1.0 (how council is activated)
- Antigravity Council Review Packet Spec v1.0 (builder output format)

### Out of Scope
- Agent-to-agent packet schemas (covered in CCP-2)
- Build Handoff Protocol and artifact protocols (covered in CCP-2)
- Runtime code implementation
- Test coverage of council automation

### Invariants (Must Not Violate)
1. LifeOS Constitution v2.0 remains supreme authority
2. CEO-only amendment rights preserved
3. StepGate human control principle maintained
4. Determinism and auditability requirements preserved
5. Evidence-by-reference rule maintained

---

## 3. AUR INVENTORY

```yaml
aur_inventory:
  - id: "AUR_20260105_council_process_review"
    artefacts:
      - name: "Council_Protocol_v1.1.md"
        kind: "markdown"
        source: "embedded"
        path: "docs/02_protocols/Council_Protocol_v1.1.md"
      - name: "AI_Council_Procedural_Spec_v1.0.md"
        kind: "markdown"
        source: "embedded"
        path: "docs/02_protocols/AI_Council_Procedural_Spec_v1.0.md"
      - name: "Council_Context_Pack_Schema_v0.2.md"
        kind: "markdown"
        source: "embedded"
        path: "docs/02_protocols/Council_Context_Pack_Schema_v0.2.md"
      - name: "Council_Invocation_Runtime_Binding_Spec_v1.0.md"
        kind: "markdown"
        source: "embedded"
        path: "docs/01_governance/Council_Invocation_Runtime_Binding_Spec_v1.0.md"
      - name: "Antigravity_Council_Review_Packet_Spec_v1.0.md"
        kind: "markdown"
        source: "embedded"
        path: "docs/01_governance/Antigravity_Council_Review_Packet_Spec_v1.0.md"
```

---

## 4. DECISION QUESTIONS FOR COUNCIL

| # | Question | Context |
|---|----------|---------|
| Q1 | Should Council Invocation Runtime Binding Spec be updated from v1.0 to v1.1 to match the protocol version? | Runtime binding references "Council Protocol v1.0" throughout, but canonical protocol is now v1.1 |
| Q2 | Is Council Context Pack Schema v0.2 ready for v1.0 promotion? What blocks it? | Schema is relied upon by v1.0 protocols but itself is labeled beta |
| Q3 | Should the Independence Rule §6.3 SHOULD be converted to MUST for M2_FULL reviews? | Current wording is "SHOULD be executed on independent model when practical" |
| Q4 | Are the Testing Reviewer and Governance Reviewer seat definitions in §5.2 sufficiently detailed? | Added in v1.1 but with minimal description |
| Q5 | Should Antigravity_Council_Review_Packet_Spec be generalized beyond COO Runtime scope? | Currently scoped to "COO Runtime / PB→COO builds" |

---

## 5. AUTHORITY CHAIN

The following hierarchy is binding. Reviewers must not recommend changes that violate documents higher in the chain. These documents are embedded in Section 9 for reference.

1. **LifeOS Constitution v2.0** — Supreme authority
2. **Governance Protocol v1.0** — How governance changes are made
3. **Council Protocol v1.1** — How councils operate (THIS IS THE PRIMARY AUR)
4. **Intent Routing Rule v1.0** — How issues are routed
5. **AI Council Procedural Spec v1.0** — Operational runbook

---

## 6. COUNCIL REVIEWER ROLES

Each reviewer executes their lens against the embedded AURs below. All outputs MUST follow the required schema in Section 7.

### 6.1 Chair
- Assembles this CCP, enforces protocol invariants
- Manages topology, rejects malformed outputs
- Synthesizes verdict and Fix Plan
- Produces Contradiction Ledger

### 6.2 Co-Chair
- Validates CCP completeness
- Challenges Chair synthesis
- Hunts hallucinations
- Produces concise role prompt blocks

### 6.3 Architect Reviewer
Evaluate: Structural coherence of the protocol stack. Are the documents well-layered? Do they compose correctly?

### 6.4 Alignment Reviewer
Evaluate: Goal fidelity — does the council protocol stack serve human oversight goals? Are control surfaces adequate?

### 6.5 Structural & Operational Reviewer
Evaluate: Process integrity — are lifecycle semantics clear? What operational failure modes exist?

### 6.6 Technical Reviewer
Evaluate: Implementation feasibility — can these protocols be mechanically followed? Are there ambiguities?

### 6.7 Testing Reviewer
Evaluate: How would you verify council operations comply with these protocols? What tests are missing?

### 6.8 Risk / Adversarial Reviewer
Evaluate: Adversarial analysis — how could these protocols be gamed or misused? What failure scenarios exist?

### 6.9 Simplicity Reviewer
Evaluate: Complexity reduction — are there unnecessary moving parts? Can boundaries be sharper?

### 6.10 Determinism Reviewer
Evaluate: Reproducibility — can council runs be replayed deterministically? Are side effects controlled?

### 6.11 Governance Reviewer
Evaluate: Authority chain compliance — do all documents properly defer to higher authorities? Is amendment hygiene correct?

---

## 7. REQUIRED OUTPUT SCHEMA (PER REVIEWER)

Every reviewer MUST structure their output as follows:

```
## VERDICT
[Accept | Go with Fixes | Reject]

## KEY FINDINGS (3-10 bullets)
- Finding 1 [REF: <doc>:§<section> or #L<line>]
- Finding 2 [REF: ...]
...

## RISKS / FAILURE MODES
- Risk 1 [REF: ... or ASSUMPTION]
...

## FIXES (prioritized)
- F1: [summary] [Impact: HIGH|MEDIUM|LOW] [REF: ...]
- F2: ...

## OPEN QUESTIONS
- Q1: ...

## CONFIDENCE
[Low | Medium | High]

## ASSUMPTIONS
- A1: ...
```

---

## 8. EMBEDDED AURs (ARTEFACTS UNDER REVIEW)

### 8.1 Council Protocol v1.1 (PRIMARY AUR)

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
```

---

### 8.2 AI Council Procedural Spec v1.0

```markdown
# AI Council — Procedural Specification v1.0

**System**: LifeOS Governance Hub  
**Status**: Proposed for Canonical Promotion (operational layer)  
**Effective date**: 2026-01-05 (upon CEO promotion)  
**Scope**: Runbook for executing Council Protocol v1.1

---

## 1. Purpose

This document operationalises **Council Protocol v1.1**. It specifies how to:
- assemble a Council Context Pack (CCP),
- select mode/topology deterministically,
- run council reviews under MONO, HYBRID, or DISTRIBUTED topologies,
- enforce evidence gating and output templates,
- produce audit-ready Council Run Logs.

---

## 2. Inputs

You need:
1. AUR artefact(s) (files, diffs, or pasted content).
2. CCP header YAML (machine-discernable).
3. Seat prompt artefacts (Chair, Co-Chair, reviewers).

If canonical artefacts are unavailable, use **BOOTSTRAP CCP** (Protocol §9).

---

## 3. CCP assembly (deterministic)

### 3.1 CCP structure
A CCP is a single packet containing:

1) YAML header (required)  
2) AUR inventory (required)  
3) Objective + scope boundaries (required)  
4) Attachments or embedded content (required)  
5) Execution instructions (topology + prompts)  
6) Output collection plan (where seat outputs go)  
7) Council Run Log template (blank, to fill)

### 3.2 AUR inventory template
Include:

```yaml
aur_inventory:
  - id: "<AUR_ID>"
    artefacts:
      - name: "file_or_doc_name"
        kind: "markdown|code|diff|notes|other"
        source: "attached|embedded|link"
        hash: null|"sha256:..."
```

---

## 4. Mode selection (mechanical)

Apply `mode_selection_rules_v1` from CCP header:
- If override provided, record rationale.
- Otherwise compute mode.

Operational guideline:
- M0_FAST: L1 Unified only.
- M1_STANDARD: Chair + Co-Chair + 3–5 key seats.
- M2_FULL: Chair + Co-Chair + all canonical seats (9).

---

## 5. Topology selection (mechanical)

### 5.1 MONO topology (single-model run)
Use when:
- copy/paste friction must be minimal, or
- external models are unavailable, or
- you are doing an initial pass before distributing.

**Important**: MONO does not create independence. Therefore:
- For M1/M2, you must run the Co‑Chair **challenge pass** as a separate pass (even if same model).
- Produce a Contradiction Ledger.

#### MONO run order (recommended)
1) Chair pre-flight (assemble CCP, validate header)
2) Co-Chair validation (packet audit + prompt blocks)
3) Execute seats sequentially (as separate sections)
4) Chair synthesis + Fix Plan + Contradiction Ledger
5) Co-Chair challenge to synthesis (hallucination hunt)
6) Chair finalises Council Run Log

### 5.2 HYBRID topology (chair/co-chair + selective external seats)
Use when:
- you want some independence, but not full distribution.

Recommended externalisation:
- Risk/Adversarial seat (independent model)
- Governance seat (independent model)
- Technical/Testing seats (implementation-focused model)

Chair/Co-Chair remain on `models.primary`.

### 5.3 DISTRIBUTED topology (per-seat external)
Use when:
- stakes are high (often M2),
- you want maximum diversification.

Rule of thumb:
- at minimum, put Risk or Governance on a different model family for independence when practical.

---

## 6. Model assignment (default plan)

This spec is model-agnostic. The CCP must include `model_plan_v1`.

Practical default (if you have multiple vendors available):
- primary: your “generalist best” model
- adversarial: a different vendor/model family, tuned for critique
- governance: a different vendor/model family, tuned for policy/structure
- implementation: a model with strong code/test reasoning

If you only have one model available:
- set topology to MONO and ensure the challenge pass + contradiction ledger is executed.

---

## 7. Seat execution instructions (copy/paste minimal)

### 7.1 Fast (M0_FAST)
- Run **L1 Unified Reviewer** prompt against the AUR.
- Chair may directly summarise verdict + Fix Plan (optional Co-Chair).

### 7.2 Standard (M1_STANDARD)
Minimum seats:
- Chair
- Co-Chair (mandatory)
- Architect
- Risk/Adversarial
- Governance
- plus Technical if code/spec is involved

### 7.3 Full (M2_FULL)
All seats:
- Architect
- Alignment
- Structural & Operational
- Technical
- Testing
- Risk/Adversarial
- Simplicity
- Determinism
- Governance

---

## 8. Output handling and rejection rules

### 8.1 Rejection triggers (Chair must reject)
- missing required sections (Verdict/Findings/Fixes/etc.)
- missing evidence references for material claims
- unbounded scope creep (reviewer redesigning without request)
- inconsistent verdict (“Accept” but fix plan requires major rework)

### 8.2 Correction protocol
Chair returns:
- “Rejected due to: <reason>”
- “Please resubmit using the required schema, with REF citations.”

---

## 9. Synthesis and Fix Plan

Chair synthesis must contain:
1) Consolidated verdict
2) Top 5–12 fixes in priority order
3) Explicit CEO decision points (if any)
4) Contradiction Ledger (M1/M2)
5) Council Run Log (filled)

---

## 10. Council Run Log (template)

```yaml
council_run_log:
  aur_id: "<AUR_ID>"
  mode: "M0_FAST|M1_STANDARD|M2_FULL"
  topology: "MONO|HYBRID|DISTRIBUTED"
  models_used:
    - role: "Chair"
      model: "<model_name>"
    - role: "RiskAdversarial"
      model: "<model_name>"
  date: "2026-01-05"
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
    bootstrap_used: true|false
    override_rationale: null|"..."
```
```

---

### 8.3 Council Context Pack Schema v0.2

```markdown
# Council Context Pack — Schema v0.2 (Template)

This file is a template for assembling a CCP that satisfies Council Protocol v1.1.

---

## YAML Header (REQUIRED)

```yaml
council_run:
  aur_id: "AUR_20260105_<slug>"
  aur_type: "governance|spec|code|doc|plan|other"
  change_class: "new|amend|refactor|hygiene|bugfix"
  touches: ["docs_only"]
  blast_radius: "local|module|system|ecosystem"
  reversibility: "easy|moderate|hard"
  safety_critical: false
  uncertainty: "low|medium|high"
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

model_plan_v1:
  topology: "MONO"
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

---

## Objective (REQUIRED)
- What is being reviewed?
- What does “success” mean?

---

## Scope boundaries (REQUIRED)
**In scope**:
- ...

**Out of scope**:
- ...

**Invariants**:
- ...

---

## AUR inventory (REQUIRED)

```yaml
aur_inventory:
  - id: "<AUR_ID>"
    artefacts:
      - name: "<file>"
        kind: "markdown|code|diff|notes|other"
        source: "attached|embedded|link"
        hash: null|"sha256:..."
```

---

## Artefact content (REQUIRED)
Attach or embed the AUR. If embedded, include clear section headings for references.

---

## Execution instructions
- If HYBRID/DISTRIBUTED, list which seats go to which model and paste the prompt blocks.

---

## Outputs
- Collect seat outputs under headings:
  - `## Seat: <Name>`
- Then include Chair synthesis and the filled Council Run Log.
```

---

### 8.4 Server Council Invocation Runtime Binding Spec v1.0

```markdown
# Council Invocation & Runtime Binding Specification v1.0

Status: Active  
Scope: AI Council, COO Runtime, CSO, Antigravity  
Authority: Subordinate to LifeOS Constitution v2.0; superior to all ad hoc council behaviour.

---

## 0. PURPOSE

This document defines **how** Council Protocol v1.0, the AI Council Procedural Specification, and the Intent Routing Rule are **invoked and enforced** at runtime inside ChatGPT-based workflows.

It exists to prevent “protocol drift” where new threads forget the established council behaviour and force the CEO to re-instruct the procedure manually.

---

## 1. CANONICAL SOURCES

The following documents are **binding** for all council behaviour:

1. **Council Protocol v1.0** — Constitutional procedural specification for all Council Reviews.
2. **AI COUNCIL — Procedural Specification v1.0** — Hybrid multi-role Council procedure using StepGate for artefact review and fix planning.
3. **Intent Routing Rule v1.0** — Routing protocol between COO Runtime, CSO, AI Council, and CEO.

Hierarchy:

- LifeOS Constitution v2.0 (Supreme)
- Governance Protocol v1.0
- Council Protocol v1.0
- Intent Routing Rule v1.0
- AI Council Procedural Spec v1.0
- All other council prompts, packets, and artefacts

No runtime or prompt may override this hierarchy.

---

## 2. INVOCATION CONDITIONS

“Council Mode” MUST be activated whenever **both** are true:

1. The conversation is within the AI Council / COO Runtime / Governance project space, **and**
2. The user does any of the following:
   - Uses any of these phrases (case-insensitive):
     - “council review”
     - “run council”
     - “council packet”
     - “council review pack” / “CRP”
     - “council role prompts”
   - Explicitly asks for “council reviewers”, “architect/alignment/risk review” or similar.
   - Provides artefacts (specs, fix packets, review packets, code packets) and explicitly requests a **council** evaluation, not just a generic review.

When these conditions are met, the Assistant MUST:

- Switch into **Council Chair Mode**, unless the user explicitly assigns a different role.
- Load and apply Council Protocol v1.0 and AI Council Procedural Spec v1.0 as governing procedures.
- Apply the Intent Routing Rule when deciding whether an issue is Category 1/2/3 and where outputs should go next.

---

## 3. RELATIONSHIP WITH STEPGATE

StepGate is a **general interaction protocol** between the CEO and the assistant, where:

- Work is executed gate-by-gate.
- The CEO explicitly authorises advancement between gates (“go”).
- No permission is inferred.

Council reviews may run **inside** StepGate (e.g., “StepGate Round 3 — Council Review Gate”), but StepGate itself is:

- **Not** limited to council operations.
- **Not** auto-activated by council triggers.
- A separate higher-level protocol for pacing and CEO control.

Rules:

1. If the user explicitly states that a council review is part of a StepGate gate, the Assistant MUST:
   - Treat the council review as that gate’s work item.
   - Ensure no gate advancement without explicit CEO “go”.
   - Surface outputs as the gate result (e.g., Fix Plan, verdict, next artefacts).

2. If there is **no** explicit StepGate framing, council runs in standalone Council Protocol mode, but still obeys:
   - Council Protocol v1.0 sequence
   - AI Council Procedural Spec gates and packet formats
   - Intent Routing Rule for routing.

---

## 4. RUNTIME BEHAVIOUR — ASSISTANT CONTRACT

When Council Mode is active, the Assistant MUST behave as follows:

### 4.1 Role

- Default role: **Council Chair**.
- The Assistant may also temporarily emulate other council roles only if the CEO explicitly requests a “compact” or “internal-only” review.
- Chair responsibilities from Council Protocol v1.0 are binding:
  - enforce templates
  - prevent governance drift
  - synthesise into a canonical Fix Plan and next actions.

### 4.2 Required Inputs

Before performing a council review, the Assistant MUST ensure the four mandatory inputs are present (from Council Protocol v1.0):

1. Artefact Under Review (AUR)  
2. Role Set (full or reduced)  
3. Council Objective  
4. Output Requirements  

If any are missing, the Assistant must stop and request the missing inputs instead of silently improvising.

### 4.3 Reviewer Templates

All reviewer outputs MUST conform to the canonical template:

- VERDICT (Accept / Go With Fixes / Reject)
- ISSUES (3–10)
- INVARIANT CHECK
- NEW RISKS
- CEO-ONLY ALIGNMENT

If pasted reviewer outputs deviate from this structure, the Chair MUST:

- Reject them as malformed.
- Ask the CEO to re-run that reviewer with the correct template.

### 4.4 Deterministic Sequence

The Assistant MUST enforce the fixed sequence defined in Council Protocol v1.0 and the Procedural Spec:

1. CEO provides inputs.  
2. Chair generates deterministic role prompts (no creativity, no drift).  
3. CEO runs external reviewers and returns outputs.  
4. Chair synthesises into a consolidated verdict + Fix Plan.  
5. Chair outputs binding next actions, including:
   - Fix Plan
   - Required artefact changes
   - Instructions to Antigravity / COO Runtime
   - Next StepGate gate (if applicable)

The Chair may not:

- Skip synthesis.
- Introduce new requirements not grounded in reviewer outputs.
- Advance any StepGate gate without explicit CEO “go”.

---

## 5. INTENT ROUTING INTEGRATION

Whenever council output reveals issues, the Assistant (acting as Chair/COO) MUST route them according to the Intent Routing Rule:

- Category 1 (technical/operational) → COO / runtime, not CEO.  
- Category 2 (structural/governance/safety) → Council + CSO as needed.  
- Category 3 (strategic/intent) → CSO for CEO Decision Packet.  

The Assistant must never surface raw council output directly to the CEO outside the governance project; instead, it must be summarised and framed in CEO-impact terms.

---

## 6. CANCEL / HALT CONDITIONS

The Assistant MUST halt the council process and explicitly surface the issue to the CEO if:

- Required inputs are missing or ambiguous.
- Reviewer outputs violate the template.
- Suggested actions contradict LifeOS invariants or Council Protocol v1.0.
- The CEO’s instructions conflict with this invocation spec in a way that would cause governance drift.

Halt → return a clear question to the CEO, framed for decision.

---

## 7. VERSIONING

This file is versioned as:

- `Council_Invoke_v1.0`

Any amendment must:

1. Be initiated by the CEO.  
2. Be treated as a constitutional-style change to how council is invoked.  
3. Be logged in the Governance Hub alongside Council Protocol and Intent Routing Rule versions.

END OF SPEC
```

### 8.5 Antigravity Council Review Packet Spec v1.0

```markdown
ANTIGRAVITY COUNCIL REVIEW PACKET SPEC v1.0

Authority Chain:
LifeOS Constitution v2.0 → Governance Protocol v1.0 → COO Runtime Spec v1.0 → Implementation Packet v1.0 → this Review Packet Spec.

Status: Subordinate, mechanical, non-governance.
Scope: Applies to all COO Runtime / PB→COO builds performed under the Phase 4 Instruction Packet (and later phases that extend the runtime).

0. Purpose

This spec defines how you MUST generate a single consolidated Council Review Packet text artefact immediately after each successful Phase build (Phase 1–Phase N) of the COO Runtime work.

The packet is for Council code reviews. It MUST:

Provide the Council a deterministic, self-contained snapshot of the build,

Include a mechanical walkthrough mapped to the implementation plan / build phases,

Include the flattened codebase for the incremental build scope,

Avoid any governance decisions, verdicts, or interpretation of constitutional authority.

You generate documentation only; you do NOT judge or approve anything.

1. Subordination & Role Boundaries

LifeOS Constitution v2.0, Governance Protocol v1.0, COO Runtime Spec v1.0, Implementation Packet v1.0, and the Antigravity Instruction Packet all supersede this document in case of conflict.

You MUST treat this spec as mechanical only:

You MAY describe what you implemented.

You MAY summarise code structure and behaviour.

You MUST NOT:

Issue Accept / Go With Fixes / Reject verdicts.

Decide whether invariants are satisfied.

Alter governance rules or Council protocol.

Any ambiguity in this spec → you emit a clearly marked “OPEN_QUESTION” section for the Council rather than resolving it.

2. When to Generate a Review Packet

You MUST generate a Council Review Packet whenever ALL of the following are true:

A Phase build completes successfully under the Phase 4 Instruction Packet (e.g. “Phase 2 — Manifests & Environment Lock”, “Phase 3 — Core Runtime Components”, etc.).

The build produced at least one of:

New files in the COO Runtime tree or related scripts/tests, or

Modifications to existing COO Runtime / PB / migration / sandbox code, or

Changes to manifests or test harnesses relevant to determinism, sandboxing, or migration.

The build has a unique identifier (e.g. Git commit SHA or equivalent).

You MUST NOT skip packet generation for a qualifying Phase build.

3. Output Format & Location

3.1 File Format

Single UTF-8 text file.

Canonical name pattern:

council_review/COO_Runtime_Phase<PHASE>_Build_<BUILD_ID>_ReviewPacket_v1.0.txt

Examples:

council_review/COO_Runtime_Phase2_Build_ab12cd3_ReviewPacket_v1.0.txt

council_review/COO_Runtime_Phase4_Build_main_2025-11-28_ReviewPacket_v1.0.txt

3.2 Determinism Requirements

Sections MUST appear in the exact order defined in Section 4.

Within each section, any lists (files, tests, functions) MUST be:

Sorted lexicographically by path/name.

Generated from a deterministic traversal (e.g. sorted(os.walk(...))).

Packet content MUST be reproducible for identical repo state + configuration.

4. Packet High-Level Structure

You MUST emit the following top-level sections in order, with exact headings:

# 0. PACKET METADATA

# 1. BUILD CONTEXT & AUTHORITY

# 2. IMPLEMENTATION PLAN MAPPING

# 3. STRUCTURAL WALKTHROUGH (NON-NORMATIVE)

# 4. TESTS, GATES & DETERMINISM SURFACE

# 5. SANDBOX, FREEZE & AMU₀ TOUCHPOINTS

# 6. FLATTENED CODEBASE (INCREMENTAL SCOPE)

# 7. OPEN QUESTIONS & IMPLEMENTER NOTES

Each section below is mandatory, even if some subsections are marked “NONE”.

5. Section Definitions
5.1 # 0. PACKET METADATA

You MUST include:

Phase: (e.g. Phase 3 — Core Runtime Components)

Build_ID: (commit SHA or equivalent)

Timestamp_UTC: (ISO string; may be derived deterministically from CI metadata)

Repo_Path: (logical project name)

Spec_Versions: list:

LifeOS_v1.1

Alignment_Layer_v1.4

COO_Runtime_Spec_v1.0

Implementation_Packet_v1.0

Antigravity_Instruction_Packet_Phase4_v1.0

Scope: brief mechanical description (e.g. “Phase 3 runtime modules + tests for determinism and migration”).

No interpretation or verdicts here; this is pure metadata.

5.2 # 1. BUILD CONTEXT & AUTHORITY

You MUST mechanically restate:

Authority Chain (one short paragraph re-stating subordination, citing the canonical specs).

Phase Goals (Mechanical):

Extract the relevant Phase description from the Antigravity Instruction Packet and quote/summarise it deterministically (non-normative).

Files Touched (Summary Table):

A small table or bullet list of:

ADDED_FILES:

MODIFIED_FILES:

DELETED_FILES:

Paths MUST be sorted.

You MUST NOT alter any spec language when restating authority or scope.

5.3 # 2. IMPLEMENTATION PLAN MAPPING

Purpose: allow the Council to see what you claim to have implemented vs which plan/spec sections you followed.

You MUST include:

Plan Artefact References:

Filenames and (if available) headings for:

The relevant Implementation Packet sections.

Any Phase-specific implementation plan document(s) you were given (file names only; include content only if requested by the CEO via configuration).

Phase-to-Code Mapping Table

A structured table with columns:

Plan_Section

Brief_Mechanical_Description

Key_Files_Implemented

For example:

Plan_Section: "4. AMENDMENT ENGINE (MECHANICAL)"

Brief_Mechanical_Description: "Deterministic anchoring + amendment_log.json + amendment_diff.patch"

Key_Files_Implemented: ["coo_runtime/runtime/amendment_engine.py", "coo_runtime/tests/test_determinism.py"]

This table is descriptive only and MUST be derived from:

Plan section titles,

The actual file paths you changed.

No claims about correctness; only “we wired X plan section to these files”.

5.4 # 3. STRUCTURAL WALKTHROUGH (NON-NORMATIVE)

This is a narrative but non-binding walkthrough to help reviewers orient themselves.

You MUST:

Clearly label the section header as:

# 3. STRUCTURAL WALKTHROUGH (NON-NORMATIVE, DESCRIPTIVE ONLY)

For each key module touched in this phase (runtime file, script, or test), emit a short, structured entry:

Module_Path: ...

Role (from spec/plan): ... (pull language from spec/plan where possible)

Key_Public_Interfaces: [function/class names] (derived from parsing the file)

Notes: short 2–4 lines describing what the module appears to do, in neutral language.

Rules:

Do NOT claim “correctness”, “compliance”, or “passed verification”.

Use phrases like “implements”, “wires”, “provides functions for” rather than “ensures compliance”, “guarantees determinism”, etc.

If you are unsure, state: Notes: Unable to infer behaviour without governance; flagged for Council review.

5.5 # 4. TESTS, GATES & DETERMINISM SURFACE

You MUST help the Council see what is being exercised.

Tests Overview

List all tests run as part of the Phase build (e.g. pytest node IDs).

For each test file:

Test_File: ...

Test_Cases: list of function names or node IDs.

Result: PASS/FAIL/SKIPPED (from CI/logs).

Note: this is reporting only; no interpretation of adequacy.

Gates Touched (if any)

If this Phase includes or affects any Gates from the COO Runtime Spec (A–F), list which gate logic files were touched and how:

Gate: A — Repo Unification Integrity

Gate_Implementation_Files: [...]

Gate_Tests: [...] (if any)

Determinism Surface Notes

Mechanical, factual list of determinism-relevant behaviours:

RNG seeding behaviour (if present).

Time mocking or fixed timestamps.

File traversal ordering guarantees (sorted(...)).

Explicit environment pinning behaviours.

You MUST limit yourself to directly observable behaviours (e.g., “function X sets RNG seed to 0xDEADBEEF”) and MUST NOT assert that overall determinism is satisfied.

5.6 # 5. SANDBOX, FREEZE & AMU₀ TOUCHPOINTS

If the Phase modifies any of:

freeze.py

amu_capture.py

sandbox / OCI digests

manifests related to environment/hardware/freeze

you MUST document:

Relevant Files Changed

Manifest Fields Touched (e.g. tools_manifest.json, environment_manifest.json, sandbox_digest.txt, freeze_manifest.json).

AMU₀-Related Logic:

Where snapshots are taken.

Where SHA256 hashes are computed.

Where CEO signatures are expected/verified (paths and function names only).

If the Phase does not touch any of these, you MUST explicitly state:
This Phase did not modify sandbox, freeze, or AMU₀ logic.

5.7 # 6. FLATTENED CODEBASE (INCREMENTAL SCOPE)

This section MUST contain the entire flattened codebase for the incremental build scope only.

Scope Definition:

All files under the configured root(s) (e.g. coo_runtime/, selected PB/IP locations) that:

Were added or modified in this Phase build, OR

Are core runtime modules the Phase relies on and which the Council is likely to review together (default: all Python files in coo_runtime/runtime/, coo_runtime/tests/, coo_runtime/scripts/).

Format:

For each file included, you MUST emit:

===== FILE START: <relative/path/to/file.py> =====
<file contents, exactly as on disk>
===== FILE END: <relative/path/to/file.py> =====


Rules:

Files MUST be ordered lexicographically by path.

Contents MUST be byte-identical to the repo state used for the build.

You MUST NOT omit any file within the defined scope.

5.8 # 7. OPEN QUESTIONS & IMPLEMENTER NOTES

This is the only section where you MAY raise issues for the Council, but still without verdicts.

Subsections:

## 7.1 OPEN_QUESTIONS_FOR_COUNCIL

Each entry:

ID: Q-<incrementing integer>

Source: [file path + line range, or “config”]

Description: short neutral phrasing of the ambiguity or concern.

Evidence: specific references (e.g. functions, comments, manifest fields).

You MUST NOT recommend a decision; you only flag.

## 7.2 IMPLEMENTER_NOTES (NON-NORMATIVE)

Implementation notes such as:

“Unclear requirement in spec section X; implemented safest mechanical option Y.”

“Test harness relies on assumption Z; Council may wish to review.”

These notes are advisory and non-binding.

6. Mechanical Generation Process (High-Level)

To produce the packet, you MUST:

Capture build metadata (phase, commit, specs, timestamp).

Build file lists from the repo (added/modified/removed + core runtime scope).

Parse plan/spec references as needed for mapping.

Extract test execution results from CI logs.

Generate the narrative sections using deterministic prompts and config that emphasise non-normative, descriptive language.

Concatenate all sections in the defined order into a single text file.

Write to the council_review/ directory at the project root.

If any step fails, you MUST still attempt to emit a partial packet with a clear error note in Section 7.1.
```

---

## 9. CONTEXT ARTEFACTS (AUTHORITY CHAIN)

### 9.1 LifeOS Constitution v2.0 (SUPREME AUTHORITY)

```markdown
# LifeOS Constitution v2.0

**Status**: Supreme Governing Document  
**Effective**: 2026-01-01  
**Supersedes**: All prior versions

---

## Part I: Raison d'Être

LifeOS exists to make me the CEO of my life and extend the CEO's operational reach into the world.

It converts intent into action, thought into artifact, direction into execution.

Its purpose is to augment and amplify human agency and judgment, not originate intent.

---

## Part II: Hard Invariants

These invariants are binding. Violation is detectable and serious.

### 1. CEO Supremacy

The human CEO is the sole source of strategic intent and ultimate authority.

- No system component may override an explicit CEO decision.
- No system component may silently infer CEO intent on strategic matters.
- The CEO may override any system decision at any time.

### 2. Audit Completeness

All actions must be logged.

- Every state transition must be recorded.
- Logs must be sufficient to reconstruct what happened and why.
- No silent or unlogged operations.

### 3. Reversibility

System state must be versioned and reversible.

- The CEO may restore to any prior checkpoint at any time.
- Irreversible actions require explicit CEO authorization.

### 4. Amendment Discipline

Constitutional changes must be logged and deliberate.

- All amendments require logged rationale.
- Emergency amendments are permitted but must be reviewed within 30 days.
- Unreviewed emergency amendments become permanent by default.

---

## Part III: Guiding Principles

These principles are interpretive guides, not binding rules. They help agents make judgment calls when rules don't specify.

1. **Prefer action over paralysis** — When in doubt, act reversibly rather than wait indefinitely.

2. **Prefer reversible over irreversible** — Make decisions that can be undone.

3. **Prefer external outcomes over internal elegance** — Visible results matter more than architectural beauty.

4. **Prefer automation over human labor** — The CEO should not perform routine execution.

5. **Prefer transparency over opacity** — Make reasoning visible and auditable.

---

## Constitutional Status

This Constitution supersedes all previous constitutional documents.

All subordinate documents (Governance Protocol, Runtime Spec, Implementation Packets) must conform to this Constitution.

In any conflict, this Constitution prevails.

END OF CONSTITUTION
```

### 9.2 Governance Protocol v1.0

```markdown
# LifeOS Governance Protocol v1.0

**Status**: Subordinate to LifeOS Constitution v2.0  
**Effective**: 2026-01-01  
**Purpose**: Define operational governance rules that can evolve as trust increases

---

## 1. Authority Model

### 1.1 Delegated Authority

LifeOS operates on delegated authority from the CEO. Delegation is defined by **envelopes** — boundaries within which LifeOS may act autonomously.

### 1.2 Envelope Categories

| Category | Description | Autonomy Level |
|----------|-------------|----------------|
| **Routine** | Reversible, low-impact, within established patterns | Full autonomy |
| **Standard** | Moderate impact, follows established protocols | Autonomy with logging |
| **Significant** | High impact or irreversible | Requires CEO approval |
| **Strategic** | Affects direction, identity, or governance | CEO decision only |

### 1.3 Envelope Evolution

Envelopes expand as trust and capability increase. The CEO may:
- Expand envelopes by explicit authorization
- Contract envelopes at any time
- Override any envelope boundary

---

## 2. Escalation Rules

### 2.1 When to Escalate

LifeOS must escalate to the CEO when:
1. Action is outside the defined envelope
2. Decision is irreversible and high-impact
3. Strategic intent is ambiguous
4. Action would affect governance structures
5. Prior similar decision was overridden by CEO

### 2.2 How to Escalate

Escalation must include:
- Clear description of the decision required
- Options with tradeoffs
- Recommended option with rationale
- Deadline (if time-sensitive)

### 2.3 When NOT to Escalate

Do not escalate when:
- Action is within envelope
- Decision is reversible and low-impact
- Prior similar decision was approved by CEO
- Escalating would cause unacceptable delay on urgent matters (log and proceed)

---

## 3. Council Model

### 3.1 Purpose

The Council is the deliberative and advisory layer operating below the CEO's intent layer. It provides:
- Strategic and tactical advice
- Ideation and brainstorming
- Structured reviews
- Quality assurance
- Governance assistance

### 3.2 Operating Phases

**Phase 0–1 (Human-in-Loop)**:
- Council Chair reviews and produces a recommendation
- CEO decides whether to proceed or request fixes
- Iterate until CEO approves
- CEO explicitly authorizes advancement

**Phase 2+ (Bounded Autonomy)**:
- Council may approve within defined envelope
- Escalation rules apply for decisions outside envelope
- CEO receives summary and may override

### 3.3 Chair Responsibilities

- Synthesize findings into actionable recommendations
- Enforce templates and prevent drift
- Never infer permission from silence or past approvals
- Halt and escalate if required inputs are missing

### 3.4 Invocation

Council mode activates when:
- CEO uses phrases like "council review", "run council"
- Artefact explicitly requires council evaluation
- Governance protocol specifies council review

---

## 4. Amendment

This Governance Protocol may be amended by:
1. CEO explicit authorization, OR
2. Council recommendation approved by CEO

Amendments must be logged with rationale and effective date.

END OF GOVERNANCE PROTOCOL
```

### 9.3 Intent Routing Rule v1.0

```markdown
# Intent Routing Rule v1.0
LifeOS Governance Hub — Routing Protocol
Status: Active
Applies To: COO Runtime, AI Council, CSO
Authority: Subordinate to LifeOS v1.1, CSO Charter v1.0, CEO Interaction Directive v1.0

============================================================
0. PURPOSE
============================================================
This protocol defines how all questions, decisions, ambiguities, and escalations are routed between:

- COO Runtime (execution)
- CSO (intent interpretation)
- AI Council (governance review)

It ensures:
- strict separation of execution vs interpretation
- correct handling of Category 1, 2, and 3 decisions
- clarity about what reaches the CEO
- alignment with the CSO Operating Model v1

============================================================
1. CLASSIFICATION MODEL
============================================================
Every issue must be classified by COO or CSO into:

### Category 1 — Technical / Operational
Examples:
- runtime mechanics
- determinism checks
- file/dir layout
- council prompt mechanics
- build sequencing

**Rule:**
COO resolves internally.  
Never escalated to CEO.  
Council used only if correctness requires it.

### Category 2 — Structural / Governance / Safety
Examples:
- invariants
- governance leakage
- architectural forks
- determinism hazards
- ambiguity requiring governance interpretation

**Rule:**
COO → Council (for analysis)
Council → COO (synthesised findings)
COO → CSO (single synthesised question)
CSO → CEO (only if CEO decision needed)

### Category 3 — Strategic / Preference / Intent
Examples:
- long-term direction
- priorities
- autonomy expansion
- productisation shifts
- decisions with multiple viable paths

**Rule:**
Route directly to CSO.  
CSO frames the issue and prepares the CEO Decision Packet.

============================================================
2. COO → CSO ROUTING RULES
============================================================

COO MUST route an issue upward to CSO when:

1. A mission depends on CEO preferences or strategic choice.
2. Ambiguity remains after COO and Council analysis.
3. A Category 3 classification is made.
4. Council recommends CEO arbitration.
5. Operational work is blocked by missing intent.
6. System behaviour may contradict the CEO’s stated trajectory.

COO MUST NOT route to CEO directly under any circumstances.

COO MUST synthesise all Council output before passing to CSO.

============================================================
3. CSO → COO ROUTING RULES
============================================================

CSO routes downward to COO when:

1. The decision is Category 1 (technical/operational).
2. The decision is Category 2 but resolvable without CEO input.
3. The CEO has already expressed stable preferences.
4. The issue is frictional, administrative, or would create “crank-turning”.
5. It requires execution, not interpretation.

CSO MUST NOT give operational instructions.  
CSO provides strategic briefs; COO handles execution.

============================================================
4. CSO → COUNCIL REQUESTS
============================================================

CSO may request Council involvement when:

1. A strategic mission contains structural or constitutional ambiguity.
2. A governance invariant may be implicated.
3. A risk requires multi-lens analysis.
4. Determinism or architecture questions exceed COO authority.

COO MUST:
- authorise
- configure
- invoke
- budget
- supervise

Council operations.

CSO cannot invoke the Council directly.

============================================================
5. WHAT MUST ALWAYS BE SURFACED TO CEO
============================================================
(Per CSO Operating Model v1 and the CEO Interaction Directive)

- Intent drift or long-term direction issues  
- Architectural/governance structure changes  
- Any autonomy expansion proposal  
- Any personal risk event  
- Major productisation pivots  
- Decisions with multiple viable strategic paths  

All must be surfaced via CSO in a CEO Decision Packet.

============================================================
6. WHAT MUST NEVER BE SURFACED TO CEO
============================================================

- Raw technical detail  
- Reviewer chatter  
- Multiple unresolved questions  
- Operational sequencing  
- Runtime mechanics  
- Build/process noise  
- Raw Council output  
- Any detail not framed in CEO-impact terms  

============================================================
7. DEFAULT RULE
============================================================

If COO or CSO are unsure how to route:

1. Route to CSO.  
2. CSO classifies Category 1, 2, or 3.  
3. COO and Council operate accordingly.  

No direct-to-CEO routing is permitted.

END — Intent Routing Rule v1.0
```

---

## 10. EXECUTION INSTRUCTIONS

### For DISTRIBUTED topology (recommended):

1. **Chair Model**: Load this entire CCP. Execute Chair pre-flight, validate structure.
2. **Co-Chair Model**: Validate CCP completeness. Prepare role prompts for distribution.
3. **Distribute to seats**: Copy Section 6 role descriptions + Section 7 output schema + Section 8 embedded artefacts to each reviewer model.
4. **Collect outputs**: Each reviewer returns structured output per Section 7.
5. **Chair synthesis**: Chair consolidates all outputs, produces verdict + fix plan + contradiction ledger.
6. **Co-Chair challenge**: Hunts hallucinations in synthesis.
7. **Finalize Council Run Log**.

### For MONO topology:
Execute all seats sequentially within a single model session, ensuring distinct prompts for each role.

---

## 11. COUNCIL RUN LOG (TEMPLATE - TO BE FILLED)

```yaml
council_run_log:
  aur_id: "AUR_20260105_council_process_review"
  mode: "M2_FULL"
  topology: "DISTRIBUTED"
  models_used:
    - role: "Chair"
      model: ""
    - role: "CoChair"
      model: ""
    - role: "Architect"
      model: ""
    - role: "Alignment"
      model: ""
    - role: "StructuralOperational"
      model: ""
    - role: "Technical"
      model: ""
    - role: "Testing"
      model: ""
    - role: "RiskAdversarial"
      model: ""
    - role: "Simplicity"
      model: ""
    - role: "Determinism"
      model: ""
    - role: "Governance"
      model: ""
  date: "2026-01-05"
  verdict: ""
  key_decisions: []
  fixes: []
  contradictions: []
  notes:
    bootstrap_used: false
    override_rationale: "Multi-model council for maximum independence"
```

---

## 12. OUTPUTS COLLECTION AREA

> Reviewers: paste your outputs below under your seat heading.

### Seat: Architect Reviewer
(output here)

### Seat: Alignment Reviewer
(output here)

### Seat: Structural & Operational Reviewer
(output here)

### Seat: Technical Reviewer
(output here)

### Seat: Testing Reviewer
(output here)

### Seat: Risk / Adversarial Reviewer
(output here)

### Seat: Simplicity Reviewer
(output here)

### Seat: Determinism Reviewer
(output here)

### Seat: Governance Reviewer
(output here)

---

### Chair Synthesis
(Chair fills this after all seats complete)

### Contradiction Ledger
(Chair fills this)

### Final Verdict & Fix Plan
(Chair fills this)

---

**END OF CCP-1**
