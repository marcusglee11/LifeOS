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

