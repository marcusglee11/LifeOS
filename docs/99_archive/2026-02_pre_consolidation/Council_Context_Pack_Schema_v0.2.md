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

