---
council_run:
  aur_id: "AUR_20260106_OpenCode_DocSteward_CT2_Phase2"
  aur_type: "governance"
  change_class: "new"
  touches: ["tier_activation", "docs_only", "governance_protocol"]
  blast_radius: "system"
  reversibility: "moderate"
  safety_critical: true
  uncertainty: "low"
  override:
    mode: null 
    topology: null
    rationale: null

mode_selection_rules_v1:
  default: "M2_FULL"

model_plan_v1:
  topology: "MONO"
  models:
    primary: "gemini-1.5-pro-002"
    adversarial: "gemini-1.5-pro-002"
    implementation: "gemini-1.5-pro-002"
    governance: "gemini-1.5-pro-002"
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

# CCP: OpenCode Steward Activation (CT-2 Phase 2)

## Objective
Activate OpenCode as the **Phase 2 Document Steward**, authorizing human-triggered autonomous modification of the `docs/` tree.

## Scope Boundaries

### [EMBEDDED] OpenCode_Steward_Scope_Boundaries.yaml
```yaml
scope_definition:
  role: "primary_document_steward"
  phase: "2_human_triggered"
  
  allowlist_surfaces:
    - path: "docs/**"
      permissions: ["create", "read", "update", "delete"]
      constraints: "must_update_index"
    - path: "docs/INDEX.md"
      permissions: ["read", "update"]
    - path: "docs/LifeOS_Strategic_Corpus.md"
      permissions: ["read", "update(regenerate)"]
    - path: "artifacts/review_packets/**"
      permissions: ["create"]
    - path: "artifacts/evidence/opencode_steward_certification/**"
      permissions: ["read"]

  denylist_surfaces:
    - path: "docs/00_foundations/**"
      action: "modify"
      exception: "explicit_user_override_only"
    - path: "config/**"
      action: "any"
    - path: "scripts/**"
      action: "modify"
    - path: "**/*.py"
      action: "modify"
    - path: "GEMINI.md"
      action: "modify"
      
  excluded_behaviors:
    - "git_push_without_review"
    - "autonomous_packet_ingestion"
    - "modifying_code_logic"
    - "modifying_system_prompts"
```

## Operational Interface

The Phase 2 steward operates via the **CLI Interface**:

1.  **Trigger**: User runs `python scripts/opencode_ci_runner.py --task "<Instruction>"`
2.  **Execution**: OpenCode server (running on port 62585) receives the prompt, executes tool calls, and returns strict output.
3.  **Output Capture**: All modifications are staged in git. `opencode_ci_runner.py` logs outcome.
4.  **Review Packet**: For missions involving >1 file or governance changes, OpenCode MUST produce a `Review_Packet_<Name>_vX.Y.md`.

## Rollback Runbook

### [EMBEDDED] Steward_Rollback_Runbook.md

**Condition**: OpenCode produces hallucinatory content, destructive deletions, or adheres to non-stochastic formatting.

**Procedure**:

1.  **Kill Switch**:
    ```powershell
    taskkill /IM opencode.exe /F
    # OR stop the 'opencode serve' terminal
    ```

2.  **Revert Last Mission**:
    ```powershell
    git reset --hard HEAD~1
    ```
    *If staged but not committed*: `git restore .` and `git clean -fd`.

3.  **Revoke Authority**:
    - Update `docs/11_admin/LIFEOS_STATE.md` setting `Current Build Agent` back to `Antigravity`.
    - Delete `AGENTS.md` (or rename to `AGENTS.md.disabled`).

4.  **Incident Report**:
    - Create `artifacts/incidents/INCIDENT_<Date>_OpenCode_Failure.md` with logs.

5.  **Verification**:
    - Confirm OpenCode process is stopped.
    - Run `git status` to verify working directory is clean.
    - Run `git log -1` to confirm HEAD is at the expected commit (pre-incident).

## Evidence Reference
## Evidence Reference
- **Certification Report**: `artifacts/evidence/opencode_steward_certification/CERTIFICATION_REPORT_v1_4.json`
  - **SHA-256**: `5ffa02ded22723fddbd383982dc653b32a10f149f9e0737d8f78c1828182a0ee`
- **Enforcement Runner**: `scripts/opencode_ci_runner.py`
  - **SHA-256**: `b40bcec1f0b2c08416b18cded7f64fbed545b9a5862ebc97c1f49667698f961a`
- **Verification Harness**: `scripts/run_certification_tests.py`
  - **SHA-256**: `24ae855b0234b4d23b9229b880895de41840e309df7993e4edf392d0b90de7bd`
- **Compliance Status**: 13/13 passed (v1.4 suite). Strict Isolation Enforced (P0.1). Symlink Defense Verified (P1.2). Archive Removed (P1.1).
