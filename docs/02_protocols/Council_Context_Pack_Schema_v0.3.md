# Council Context Pack — Schema v0.3 (Template)

This file is a template for assembling a CCP that satisfies Council Protocol v1.2.

---

## Promotion Criteria (v0.3 → v1.0)

This schema may be promoted to v1.0 when the following are satisfied:

1. **Mode selection test suite**: Automated tests covering all `mode_selection_rules_v1` logic paths with input YAML → expected mode verification
2. **Template validation test**: Parser that validates CCP structure against required sections
3. **REF parsing test**: Parser that extracts and validates REF citations in all three permitted formats
4. **Adversarial review**: At least one council review of the schema itself with Governance and Risk seats on independent models

Status: [ ] Mode selection tests  [ ] Template validation  [ ] REF parsing  [ ] Adversarial review

---

## YAML Header (REQUIRED)

```yaml
council_run:
  aur_id: "AUR_20260106_<slug>"
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
- What does "success" mean?

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
        hash: "sha256:..." # SHOULD be populated per AI_Council_Procedural_Spec §3.2
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

---

## Amendment record

**v0.3 (2026-01-06)** — Fix Pack AUR_20260105_council_process_review:
- F7: Added Promotion Criteria section with v1.0 requirements
- Updated to reference Council Protocol v1.2
- Updated example date to 2026-01-06
