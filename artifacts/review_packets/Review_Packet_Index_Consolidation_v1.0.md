# Review Packet — Index Consolidation

**Mission**: Resolving Index Inconsistency  
**Date**: 2026-01-02  
**Author**: Antigravity

## Summary
Consolidated all documentation references to use `docs/INDEX.md` as the single source of truth, eliminating the ambiguous `INDEX_v1.1.md` reference found in meta-documents. This aligns with the `Document_Steward_Protocol_v1.0.md`.

## Issue Catalogue
1. **Inconsistency**: `STEWARD_ARTEFACT_MISSION_v1.0.md` and `REVERSION_PLAN_v1.0.md` referenced `docs/INDEX_v1.1.md` while the protocol and actual file are `docs/INDEX.md`.
2. **Resolution**: Updated all references to point to `docs/INDEX.md`.

## Proposed Resolutions
- **[MODIFY]** `docs/10_meta/STEWARD_ARTEFACT_MISSION_v1.0.md`
- **[MODIFY]** `docs/10_meta/REVERSION_PLAN_v1.0.md`
- **[MODIFY]** `docs/03_runtime/README_Recursive_Kernel_v0.1.md`
- **[MODIFY]** `docs/10_meta/REVERSION_EXECUTION_LOG_v1.0.md`

## Implementation Guidance
Review the flattened files below to confirm `INDEX_v1.1.md` has been replaced with `INDEX.md`.

## Appendix — Flattened Code Snapshots

### File: docs/10_meta/STEWARD_ARTEFACT_MISSION_v1.0.md
```markdown
# STEWARD_ARTEFACT_MISSION_v1.0

## Description
Persist a canonical LifeOS artefact into the repo, update registry/index, commit, and sync to the brain mirror for ChatGPT.

## Inputs
- `key` (string): Registry key (e.g., "programme_charter")
- `title` (string): Human-readable filename base (e.g., "PROGRAMME_CHARTER_v1.0")
- `type` (enum string): "governance" | "runtime" | "template" | "council" | "alignment" | "other"
- `track` (enum string): "core" | "fuel" | "plumbing"
- `relative_repo_path` (string): Path under docs (e.g., "00_foundations/PROGRAMME_CHARTER_v1.0.md")
- `version` (string): Version string (e.g., "1.0")
- `content` (string): Full markdown content of the doc
- `status` (string, optional): Default "active"

## Environment
- `LIFEOS_REPO_ROOT`: Root of the LifeOS git repository.
- `LIFEOS_BRAIN_MIRROR_ROOT`: Root of the Google Drive mirror.

## Steps

### 1. Resolve Paths
- Compute `repo_root`, `brain_root`, `docs_root`.
- `registry_path` = `docs/00_foundations/CANONICAL_REGISTRY.yaml`
- `index_path` = `docs/INDEX.md` (or current index)

### 2. Write Artefact
- Write `content` to `docs/<relative_repo_path>`.
- Ensure parent directories exist.

### 3. Update Index
- Read `index_path`.
- Insert entry into "## Canonical Artefacts" (or appropriate section manifest).
- Format: `- [{title}]({relative_repo_path}) — {type}/{track} v{version}`

### 4. Upsert Registry
- Read `registry_path`.
- Update/Create `artefacts.<key>`:
    - `title`: input.title
    - `type`: input.type
    - `track`: input.track
    - `version`: input.version
    - `status`: input.status
    - `repo_path`: input.relative_repo_path
    - `drive_path`: input.relative_repo_path
    - `updated_at`: current_timestamp

### 5. Git Commit & Push
- `git add docs`
- `git commit -m "chore: steward {key} v{version}"`
- `git push`

### 6. Sync to Brain
- Run `python docs/scripts/sync_to_brain.py`

### 7. Summary
- Emit summary confirming stewardship and sync.
```

### File: docs/10_meta/REVERSION_PLAN_v1.0.md
```markdown
# REVERSION_PLAN_v1.0.md

LifeOS Phase 1 — Reversioning & Deprecation Audit  
Version: v1.0  
Status: Gate 2 — Planning Artefact (no changes executed at time of writing)  
Author: Assistant (under CEO direction)  

---

## 0. Inputs & Invariants

### 0.1. Source paths

- **Authoritative tree (only source of truth for docs):**  
  `C:\Users\cabra\Projects\LifeOS\docs\`

- **Non-authoritative but in-scope for audit (stragglers / legacy):**
  - `C:\Users\cabra\Projects\LifeOS\` (outside `/docs`)
  - `C:\Users\cabra\Projects\COOProject\`
  - `C:\Users\cabra\Projects\governance-hub\`

### 0.2. CEO policy decisions (locked)

1. `/docs` is **always authoritative**; COOProject copies are non-authoritative.
2. All fix packs (R6.x and similar) are **deprecated** and must be archived; none become canonical.
3. Strategic/CSO/Concept docs are treated **per-file**; if duplicated or superseded they are deprecated/archived.
4. Auxiliary folders under `/docs` (`Governance`, `CommunicationsProtocols`, `Runtime`, `Specs`, `pipelines`, etc.) are **deprecated and will be archived wholesale**.

### 0.3. Phase 1 goals

- Reversion all filenames across `/docs` to follow the `_vX.Y` convention.
- Normalise naming conventions (underscores, hyphens, capitalisation).
- Audit for deprecated/straggler docs across old project folders (COOProject, governance-hub, LifeOS root).
- Move deprecated files into `/docs/99_archive/` or eliminate them after confirmation.
- Update the Documentation Index from `INDEX_v1.0.md` to `INDEX.md`.
- Identify structural inconsistencies requiring cleanup before Phase 2 and Phase 3.
- Complete a formal Reversioning Execution Log for auditability.

This plan describes **what must happen**. No changes are applied by this document itself.

---

## 1. Classification Model

Each markdown artefact in scope is classified as:

- **CANONICAL_ACTIVE**  
  Lives in `/docs/00–10/` in v1.1 regime; must exist with `_vX.Y.md` naming.

- **CANONICAL_ARCHIVE**  
  Canonical but historical; moved into `/docs/99_archive/` with clean names.

- **DUPLICATE_SHADOW**  
  Non-authoritative copy of something canonical in `/docs`; may remain in external repos but is not source of truth.

- **LEGACY_STRUCTURE**  
  Folder clusters pre-dating the `00–10` tree (for example `/docs/Governance`); to be swept wholesale into `/docs/99_archive/legacy_structures/`.

- **META_RUNTIME**  
  Operational/meta docs (`TASKS`, `governance_digest`, etc.); stay in `/docs/10_meta/` but get versioned filenames.

- **OUT_OF_SCOPE_PHASE1**  
  Non-markdown, dependencies, or third-party files (`.txt` prompt zips, venv licences, etc.); recorded but untouched.

---

## 2. Structural Changes inside `/docs`

### 2.1. Root-level files and folders

Current at Phase 1 start:

- Files:
  - `docs/DocumentAudit_MINI_DIGEST1.md`
  - `docs/INDEX_v1.0.md`
- Folders:
  - `00_foundations/`
  - `01_governance/`
  - `02_alignment/`
  - `03_runtime/`
  - `04_project_builder/`
  - `05_agents/`
  - `06_user_surface/`
  - `07_productisation/`
  - `08_manuals/`
  - `09_prompts/`
  - `10_meta/`
  - `99_archive/`
  - Auxiliary legacy folders:
    - `CommunicationsProtocols/`
    - `Governance/`
    - `pipelines/`
    - `Runtime/`
    - `Specs/`

#### 2.1.1. Root-level files

1. **DocumentAudit_MINI_DIGEST1.md**

- Classification: `META_RUNTIME` (ad-hoc audit record), but obsolete.
- Action:

  - Move from: `docs/DocumentAudit_MINI_DIGEST1.md`  
    To:       `docs/99_archive/DocumentAudit_MINI_DIGEST1_v1.0.md`

2. **INDEX_v1.0.md**

- Classification: `CANONICAL_ACTIVE` (historical index).
- Action:

  - Leave `INDEX_v1.0.md` unchanged.
  - Create `INDEX.md` at Gate 3 based on this plan.

---

### 2.2. Strict Enforcement Folders (00–06)

#### 2.2.1. `/docs/00_foundations/`

Current:

- `Architecture_Skeleton.md`

Action:

- Rename to: `Architecture_Skeleton_v1.0.md`  
  (`CANONICAL_ACTIVE`)

---

#### 2.2.2. `/docs/01_governance/`

Current:

- `Antigravity_Council_Review_Packet_Spec_v1.0.md`
- `COO_Expectations_Log.md`
- `COO_Operating_Contract_v1.0.md`
- `Council_Invocation_Runtime_Binding_Spec_v1.0.md`

Actions:

- `Antigravity_Council_Review_Packet_Spec_v1.0.md` — unchanged, `CANONICAL_ACTIVE`.
- `COO_Operating_Contract_v1.0.md` — unchanged, `CANONICAL_ACTIVE`.
- Rename `COO_Expectations_Log.md` → `COO_Expectations_Log_v1.0.md` (`CANONICAL_ACTIVE`).
- `Council_Invocation_Runtime_Binding_Spec_v1.0.md` — already conformant.

---

#### 2.2.3. `/docs/02_alignment/`

Current:

- `Alignment_Layer_v1.4.md`
- `LifeOS_Alignment_Layer_v1.0.md`

Actions:

- Both filenames already conform. No renames.
- Classification:
  - `Alignment_Layer_v1.4.md` — `CANONICAL_ACTIVE`.
  - `LifeOS_Alignment_Layer_v1.0.md` — `CANONICAL_ARCHIVE` (earlier baseline) but remains in 02 for now.

---

#### 2.2.4. `/docs/03_runtime/`

Current:

- `COO_Runtime_Core_Spec_v1.0.md`
- `COO_Runtime_Implementation_Packet_v1.0.md`
- `COO_Runtime_Spec_Index_v1.0.md`
- `COO_Runtime_Spec_v1.0.md`
- `COO_Runtime_V1.1_Clean_Build_Spec.md`
- `WALKTHROUGH.md`

Actions:

1. Normalise clean-build spec:

- `COO_Runtime_V1.1_Clean_Build_Spec.md` →  
  `COO_Runtime_Clean_Build_Spec_v1.1.md`  
  (`CANONICAL_ACTIVE`)

2. Normalise walkthrough:

- `WALKTHROUGH.md` →  
  `COO_Runtime_Walkthrough_v1.0.md`  
  (`META_RUNTIME` but stored in 03_runtime)

3. Classification overview:

- `COO_Runtime_Core_Spec_v1.0.md` — `CANONICAL_ACTIVE`
- `COO_Runtime_Spec_v1.0.md` — `CANONICAL_ACTIVE`
- `COO_Runtime_Implementation_Packet_v1.0.md` — `CANONICAL_ACTIVE`
- `COO_Runtime_Spec_Index_v1.0.md` — `CANONICAL_ACTIVE`
- `COO_Runtime_Clean_Build_Spec_v1.1.md` — `CANONICAL_ACTIVE`
- `COO_Runtime_Walkthrough_v1.0.md` — `META_RUNTIME`

---

#### 2.2.5. `/docs/04_project_builder/`

Current:

- `Antigravity_Implementation_Packet_v0.9.7.md`
- `ProjectBuilder_Spec_v0.9_FinalClean.md`

Actions:

1. `Antigravity_Implementation_Packet_v0.9.7.md` — unchanged, `CANONICAL_ACTIVE`.

2. `ProjectBuilder_Spec_v0.9_FinalClean.md` →  
   `ProjectBuilder_Spec_v0.9_FinalClean_v1.0.md`  
   (`CANONICAL_ACTIVE` — doc version 1.0 over build rev 0.9).

---

#### 2.2.6. `/docs/05_agents/`

Current:

- `COO_Agent_Mission_Orchestrator_Arch_v0.7_Aligned.md`

Action:

- Rename → `COO_Agent_Mission_Orchestrator_Arch_v0.7_Aligned_v1.0.md`  
  (`CANONICAL_ACTIVE` — doc v1.0 over arch rev 0.7).

---

#### 2.2.7. `/docs/06_user_surface/`

Current:

- `COO_Runtime_V1.1_User_Surface_StageB_TestHarness.md`

Action:

- Rename → `COO_Runtime_User_Surface_StageB_TestHarness_v1.1.md`  
  (`CANONICAL_ACTIVE`)

---

### 2.3. Soft Enforcement Folders (07–10)

#### 2.3.1. `/docs/07_productisation/`

Current:

- Empty before Phase 1.

Action (see 3.3 below):

- Introduce `Productisation_Brief_v1.0.md` moved from repo root.

---

#### 2.3.2. `/docs/08_manuals/`

Current:

- `Governance_Runtime_Manual_v1.0.md`  

Action:

- None. Already conformant.

---

#### 2.3.3. `/docs/09_prompts/`

Current key `.md` files:

- `v1.0/initialisers/master_initialiser_v1.0.md`
- `v1.0/initialisers/master_initialiser_universal_v1.0.md`
- `v1.0/protocols/capability_envelope_chatgpt_v1.0.md`
- `v1.0/protocols/capability_envelope_gemini_v1.0.md`
- `v1.0/protocols/discussion_protocol_v1.0.md`
- `v1.0/protocols/stepgate_protocol_v1.0.md`
- `v1.0/roles/chair_prompt_v1.0.md`
- `v1.0/roles/cochair_prompt_v1.0.md`
- `v1.0/roles/reviewer_architect_alignment_v1.0.md`
- `v1.0/roles/reviewer_l1_unified_v1.0.md`
- `v1.0/system/capability_envelope_universal_v1.0.md`
- `v1.0/system/modes_overview_v1.0.md`

Action:

- All filenames already conform; no renames.  
- This tree is the **canonical prompt library**.

Note: `Gemini System Prompt (v1.0).txt` remains as `.txt` and is out-of-scope for Phase 1.

---

#### 2.3.4. `/docs/10_meta/`

Current:

- `CODE_REVIEW_STATUS.md`
- `governance_digest.md`
- `IMPLEMENTATION_PLAN.md`
- `Review_Packet_Reminder.md`
- `TASKS.md`

Actions:

- `CODE_REVIEW_STATUS.md` → `CODE_REVIEW_STATUS_v1.0.md`
- `governance_digest.md` → `governance_digest_v1.0.md`
- `IMPLEMENTATION_PLAN.md` → `IMPLEMENTATION_PLAN_v1.0.md`
- `Review_Packet_Reminder.md` → `Review_Packet_Reminder_v1.0.md`
- `TASKS.md` → `TASKS_v1.0.md`

All classified as `META_RUNTIME`.

Phase 1 artefacts themselves (`REVERSION_PLAN_v1.0.md`, `DEPRECATION_AUDIT_v1.0.md`, `REVERSION_EXECUTION_LOG_v1.0.md`) will also live here after Gate 3.

---

### 2.4. Archive Folder (`/docs/99_archive/`)

Current:

- `Antigravity_Implementation_Packet_v0.9.6.md`
- `ARCHITECTUREold.md`
- `COO_Runtime_Core_Spec_v0.5.md`

Actions:

- `Antigravity_Implementation_Packet_v0.9.6.md` — unchanged, `CANONICAL_ARCHIVE`.
- `COO_Runtime_Core_Spec_v0.5.md` — unchanged, `CANONICAL_ARCHIVE`.
- `ARCHITECTUREold.md` → `ARCHITECTUREold_v0.1.md` (`CANONICAL_ARCHIVE` early sketch).

---

### 2.5. Legacy Auxiliary Folders

By CEO decision, the following are **LEGACY_STRUCTURE** and must be archived wholesale:

- `docs/CommunicationsProtocols/`
- `docs/Governance/`
- `docs/pipelines/`
- `docs/Runtime/`
- `docs/Specs/`

Actions:

1. Create `docs/99_archive/legacy_structures/`.

2. Move each folder into it, preserving internal structure:

- `docs/CommunicationsProtocols/` → `docs/99_archive/legacy_structures/CommunicationsProtocols/`
- `docs/Governance/` → `docs/99_archive/legacy_structures/Governance/`
- `docs/pipelines/` → `docs/99_archive/legacy_structures/pipelines/`
- `docs/Runtime/` → `docs/99_archive/legacy_structures/Runtime/`
- `docs/Specs/` → `docs/99_archive/legacy_structures/Specs/`

Note: All specs within these directories are thereby deprecated for Phase 1 and later require explicit re-promotion if they are to be used.

---

## 3. Stragglers in LifeOS Root (outside `/docs`)

Markdown artefacts under `C:\Users\cabra\Projects\LifeOS\` outside `docs\`:

- `Concept\Distilled Opus Abstract.md`
- `Concept\Opus LifeOS Audit Prompt and Response.md`
- `Concept\Opus LifeOS Audit Prompt 2 and Response.md`
- `CSO Strategic Layer\ChatGPTProjectPrimer.md`
- `CSO Strategic Layer\CSO_Operating_Model_v1.md`
- `CSO Strategic Layer\FULL STRATEGY AUDIT PACKET v1.md`
- `CSO Strategic Layer\Intent Routing Rule v1.0.md`
- `Productisation\PRODUCTISATION BRIEF v1.md`
- `README.md` (top-level)

### 3.1. Concept folder

All Concept docs are treated as **external analysis** and archived.

Actions:

- `Concept/Distilled Opus Abstract.md` →  
  `docs/99_archive/concept/Distilled_Opus_Abstract_v1.0.md`

- `Concept/Opus LifeOS Audit Prompt and Response.md` →  
  `docs/99_archive/concept/Opus_LifeOS_Audit_Prompt_and_Response_v1.0.md`

- `Concept/Opus LifeOS Audit Prompt 2 and Response.md` →  
  `docs/99_archive/concept/Opus_LifeOS_Audit_Prompt_2_and_Response_v1.0.md`

Classification: all `CANONICAL_ARCHIVE`.

---

### 3.2. CSO Strategic Layer

All CSO Strategic Layer docs are treated as historical and archived.

Actions:

- `CSO Strategic Layer/ChatGPTProjectPrimer.md` →  
  `docs/99_archive/cso/ChatGPT_Project_Primer_v1.0.md`

- `CSO Strategic Layer/CSO_Operating_Model_v1.md` →  
  `docs/99_archive/cso/CSO_Operating_Model_v1.0.md`

- `CSO Strategic Layer/FULL STRATEGY AUDIT PACKET v1.md` →  
  `docs/99_archive/cso/Full_Strategy_Audit_Packet_v1.0.md`

- `CSO Strategic Layer/Intent Routing Rule v1.0.md` →  
  `docs/99_archive/cso/Intent_Routing_Rule_v1.0.md`

Classification: all `CANONICAL_ARCHIVE`.

The folder `CSO Strategic Layer` itself becomes empty and can be deleted or left empty.

---

### 3.3. Productisation

- `Productisation/PRODUCTISATION BRIEF v1.md`

Action:

- Move to canonical productisation folder:

  - `docs/07_productisation/Productisation_Brief_v1.0.md`

Classification: `CANONICAL_ACTIVE`.

---

### 3.4. README.md

- `README.md` remains at repo root as the Git-facing summary.

Action:

- No move or rename in Phase 1.  
- Guidance: README should reference `docs/INDEX.md` after Phase 1.

---

## 4. governance-hub Audit Plan

Repository:

- `C:\Users\cabra\Projects\governance-hub\`

Key markdown structures:

- `prompts/v1.0/initialisers/`
- `prompts/v1.0/protocols/`
- `prompts/v1.0/roles/`
- `prompts/v1.0/system/`

These largely mirror `/docs/09_prompts/v1.0/`.

### 4.1. Canonical status

- All governance-hub prompt `.md` files are `DUPLICATE_SHADOW` of `/docs/09_prompts/v1.0/...`.
- `.zip` bundles (`governance_hub_prompt_library_v1.0.zip`, `prompt_library_v1.0_full.zip`) are `BUILD_ARTEFACT`.

### 4.2. Phase 1 actions

- No filesystem moves or renames in governance-hub.
- `DEPRECATION_AUDIT_v1.0.md` will record them as shadow copies and non-canonical.

---

## 5. COOProject Audit Plan

Repository:

- `C:\Users\cabra\Projects\COOProject\`

High-level clusters (per scan) include:

- `AICouncilReview/ReviewArtefacts/...`
- `coo-agent/council_review/...`
- `coo-agent/docs/governance/...`
- `coo-agent/docs/project_builder/...`
- `coo-agent/docs/specs/...`
- `coo-agent/impl/...`
- `coo-agent/legacy_archive/...`
- `coo-agent/prompts/...`
- `Spec/...`
- `Ideas&Planning/...`
- Various root-level markdown files and venv-related licences.

### 5.1. Canonical status

By CEO policy:

- `/docs` is canonical; COOProject is not.
- All COOProject `.md` files are one of:

  - `FIX_PACK`
  - `REVIEW_PACKET`
  - `SPEC_SHADOW`
  - `IMPLEMENTATION_PACKET`
  - `PLANNING_NOTE`
  - `PROMPT_SHADOW`
  - `THIRDPARTY_LICENSE`

### 5.2. Phase 1 actions

- **No** files are moved into `/docs` from COOProject in Phase 1.
- All COOProject artefacts remain in-place.
- `DEPRECATION_AUDIT_v1.0.md` will classify them at a high level as non-canonical.

### 5.3. Notable candidates for Phase 2+

Some COOProject files may later be promoted (in Phase 2+) into `/docs`, for example:

- `coo-agent/docs/specs/LifeOS_v1.1Core_Specification.md`
- `coo-agent/docs/specs/DEMO_APPROVAL_V1 — Deterministic Hybrid Approval Flow.md`

Promotion requires:

1. Explicit CEO decision.
2. Import into `/docs` with `_vX.Y` naming.
3. Inclusion in `INDEX_v1.X` as canonical.

Phase 1 does not perform this promotion; it only records the possibility.

---

## 6. INDEX Generation Plan

At Gate 3, `INDEX.md` will be generated to reflect:

1. **Foundations — 00**  
   - `Architecture_Skeleton_v1.0.md`

2. **Governance — 01**  
   - `Antigravity_Council_Review_Packet_Spec_v1.0.md`
   - `COO_Expectations_Log_v1.0.md`
   - `COO_Operating_Contract_v1.0.md`
   - `Council_Invocation_Runtime_Binding_Spec_v1.0.md`

3. **Alignment — 02**  
   - `Alignment_Layer_v1.4.md`
   - `LifeOS_Alignment_Layer_v1.0.md` (marked as earlier baseline)

4. **Runtime — 03**  
   - `COO_Runtime_Core_Spec_v1.0.md`
   - `COO_Runtime_Spec_v1.0.md`
   - `COO_Runtime_Implementation_Packet_v1.0.md`
   - `COO_Runtime_Spec_Index_v1.0.md`
   - `COO_Runtime_Clean_Build_Spec_v1.1.md`
   - `COO_Runtime_Walkthrough_v1.0.md`

5. **Project Builder — 04**  
   - `Antigravity_Implementation_Packet_v0.9.7.md`
   - `ProjectBuilder_Spec_v0.9_FinalClean_v1.0.md`

6. **Agents — 05**  
   - `COO_Agent_Mission_Orchestrator_Arch_v0.7_Aligned_v1.0.md`

7. **User Surface — 06**  
   - `COO_Runtime_User_Surface_StageB_TestHarness_v1.1.md`

8. **Productisation — 07**  
   - `Productisation_Brief_v1.0.md`

9. **Manuals — 08**  
   - `Governance_Runtime_Manual_v1.0.md`

10. **Prompts — 09**  
    - All `v1.0` prompt sets under `09_prompts/v1.0/...`

11. **Meta — 10**  
    - All `_v1.0` meta docs plus Phase 1 artefacts:
      - `REVERSION_PLAN_v1.0.md`
      - `DEPRECATION_AUDIT_v1.0.md`
      - `REVERSION_EXECUTION_LOG_v1.0.md`

12. **Archive — 99**  
    - General archive docs
    - `concept/`, `cso/`, `legacy_structures/`

`INDEX.md` is generated after the filesystem operations, based on this plan.

---

## 7. Execution Overview (for Gate 3)

Phase 1 execution is implemented via two PowerShell scripts:

1. **Phase1_Reversion_Renames.ps1**

   - Renames inside `/docs` only.
   - Applies all filename changes described in Section 2.

2. **Phase1_Reversion_Moves.ps1**

   - Moves:
     - Concept and CSO docs into `/docs/99_archive/...`
     - Productisation brief into `/docs/07_productisation/`
     - Legacy auxiliary folders into `/docs/99_archive/legacy_structures/`
     - Root `DocumentAudit_MINI_DIGEST1.md` into `/docs/99_archive/`

Execution logging:

- Every successful or skipped operation is logged in `REVERSION_EXECUTION_LOG_v1.0.md` by the operator.
- Any manual corrections are also logged there.

---

## 8. Gate 2 Approval

This document is the **canonical reversioning and deprecation plan** for Phase 1.

- It defines all expected renames and moves.
- It defines how external repositories are classified.
- It defines the target state summarised in `INDEX.md`.

Once the CEO is satisfied, they approve Gate 2 by instructing:

> `go (Gate 3)`

which authorises the generation of scripts, the execution log template, the full deprecation audit, and the new index.
```

### File: docs/03_runtime/README_Recursive_Kernel_v0.1.md
```markdown
# Recursive Kernel v0.1

## Overview
The Recursive Kernel is a self-improvement loop for LifeOS. In v0.1, it is limited to **safe domains** (docs) and provides a scaffold for Planning, Building, Verifying, and Gating.

## How to Run
From the repository root:

\`\`\`bash
python -m recursive_kernel.runner
\`\`\`

## Behavior
1. **Plan**: Loads `config/recursive_kernel_config.yaml` and checks `config/backlog.yaml` for `todo` tasks in `safe_domains` (currently `docs`, `tests_doc`).
2. **Build**: Executes the task. Currently supports `rebuild_index` for `docs`, which regenerates `docs/INDEX.md` based on valid markdown files in `docs/`.
3. **Verify**: Runs the configured `test_command` (default: `pytest`).
4. **Gate**: Evaluates the risk of changes.
   - Low risk (docs only, small diff) -> `AUTO_MERGE` (Simulated)
   - High risk -> `HUMAN_REVIEW`
5. **Log**: Writes a JSON report to `logs/recursive_runs/`.

## Logs
Check `logs/recursive_runs/` for execution details. Each run generates a timestamped JSON file.
```

### File: docs/10_meta/REVERSION_EXECUTION_LOG_v1.0.md
```markdown
# REVERSION_EXECUTION_LOG_v1.0.md

LifeOS Phase 1 — Reversioning & Deprecation Audit  
Execution Log for Gate 3 Operations  

---

## 1. Purpose and Instructions

This log records the **actual execution** of Phase 1 scripts:

- `Phase1_Reversion_Renames.ps1`
- `Phase1_Reversion_Moves.ps1`

and any **manual adjustments** you perform afterwards.

For each run:

1. Record:
   - Timestamp
   - Script name
   - Outcome (SUCCESS / PARTIAL / FAILED)
   - Short notes if needed.
2. For any warnings or errors:
   - Add a row to the “Exceptions” table with details.
3. For any manual corrections:
   - Add a row to the “Manual Adjustments” table.

This document becomes the audit trail for what actually happened on disk.

---

## 2. Script Runs

Use this table to log each time you run a script related to Phase 1.

### 2.1. Summary of Script Executions

| Run ID | Timestamp (local)       | Script Name                    | Outcome  | Notes                                  |
|--------|-------------------------|--------------------------------|----------|----------------------------------------|
| 1      |                         | Phase1_Reversion_Renames.ps1  |          |                                        |
| 2      |                         | Phase1_Reversion_Moves.ps1    |          |                                        |

(Add rows if you re-run any script.)

**Suggested usage:**  
Fill these rows immediately after each script completes.

---

## 3. Operation Exceptions

Record any deviations from the plan here: missing files, unexpected paths, manual corrections required due to warnings.

### 3.1. Exceptions Table

| ID | Timestamp         | Operation Type | Old Path                                      | New Path                                      | Outcome         | Notes                                        |
|----|-------------------|----------------|-----------------------------------------------|-----------------------------------------------|-----------------|----------------------------------------------|
| 1  |                   | RENAME/MOVE    |                                               |                                               | WARNING/ERROR   |                                              |

Guidance:

- **Operation Type**: RENAME, MOVE, DELETE, or RENAME/MOVE.
- **Outcome**: WARNING (non-fatal) or ERROR (failed operation).
- If a file was missing (for example, already manually adjusted), note that explicitly.

---

## 4. Manual Adjustments (Post-Script)

If you perform manual filesystem operations after or instead of using the scripts, record them here.

### 4.1. Manual Adjustments Table

| ID | Timestamp         | Action Type          | Old Path                                      | New Path                                      | Reason                                     |
|----|-------------------|----------------------|-----------------------------------------------|-----------------------------------------------|--------------------------------------------|
| 1  |                   | MOVE/RENAME/DELETE   |                                               |                                               |                                            |

Guidance:

- **Action Type**: MOVE, RENAME, DELETE, or composite like MOVE+RENAME.
- **Reason**: e.g., “Corrected earlier path error”, “Adjusted naming for clarity”, etc.

---

## 5. Phase 1 Completion Checklist

When you believe Phase 1 has been fully executed, use this checklist to verify the state of the `/docs` tree.

### 5.1. Structural Checklist

- [ ] `Phase1_Reversion_Renames.ps1` executed without unhandled errors.  
- [ ] `Phase1_Reversion_Moves.ps1` executed without unhandled errors.  
- [ ] All planned renames in `REVERSION_PLAN_v1.0.md` are reflected on disk.  
- [ ] All planned moves in `REVERSION_PLAN_v1.0.md` are reflected on disk.  
- [ ] `/docs` root contains `INDEX.md`.  
- [ ] Legacy folders exist only under `docs/99_archive/legacy_structures/`.  
- [ ] Concept and CSO docs exist only under `docs/99_archive/concept/` and `docs/99_archive/cso/`.  
- [ ] Productisation brief exists at `docs/07_productisation/Productisation_Brief_v1.0.md`.  
- [ ] `docs/10_meta/` contains:
  - `CODE_REVIEW_STATUS_v1.0.md`
  - `governance_digest_v1.0.md`
  - `IMPLEMENTATION_PLAN_v1.0.md`
  - `Review_Packet_Reminder_v1.0.md`
  - `TASKS_v1.0.md`
  - `REVERSION_PLAN_v1.0.md`
  - `DEPRECATION_AUDIT_v1.0.md`
  - `REVERSION_EXECUTION_LOG_v1.0.md`  
- [ ] No unexpected markdown files remain outside `/docs` (excluding repo-level `README.md`).

---

## 6. CEO Sign-off

Once the checklist above is complete and you are satisfied that the filesystem matches the Phase 1 plan and `INDEX.md`, sign off here.

### 6.1. Sign-off Block

- **Name:**  
- **Date:**  
- **Statement:**  

> I confirm that Phase 1 — Reversioning & Deprecation Audit has been executed according to REVERSION_PLAN_v1.0, and that the `/docs` tree is now the sole canonical documentation tree for LifeOS. All deprecated and legacy artefacts have been either archived under `docs/99_archive/` or left in external repositories as explicitly non-canonical.
```
