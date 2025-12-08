# LifeOS Documentation Index v1.1

**Location:** `/docs/INDEX_v1.1.md`  
**Scope:** Post–Phase 1 Reversioning & Deprecation state  
**Status:** Canonical index for `/docs` tree  

---

## 1. Overview

Phase 1 of the LifeOS Reversioning & Deprecation Audit:

- Normalised filenames to follow the `_vX.Y` convention where applicable.
- Archived legacy structures and outdated strategy/concept documents.
- Ensured `/docs` is the **only authoritative document tree**.
- Established a clean baseline for Phase 2+ structural and governance work.

All paths below are **relative to** `C:\Users\cabra\Projects\LifeOS\docs\`.

---

## 2. Foundations — `00_foundations/`

- `00_foundations/Architecture_Skeleton_v1.0.md`  
  High-level structural overview of the LifeOS architecture.

---

## 3. Governance — `01_governance/`

- `01_governance/Antigravity_Council_Review_Packet_Spec_v1.0.md`  
  Specification for Antigravity Council Review Packets.

- `01_governance/COO_Expectations_Log_v1.0.md`  
  Log of expectations and operating assumptions for the COO runtime.

- `01_governance/COO_Operating_Contract_v1.0.md`  
  Contractual definition of COO responsibilities and boundaries.

- `01_governance/Council_Invocation_Runtime_Binding_Spec_v1.0.md`  
  Runtime binding rules for Council Invocation.

> Note: Additional governance specs from previous eras are archived under  
> `99_archive/legacy_structures/Governance/` and are non-canonical for v1.1.

---

## 4. Alignment — `02_alignment/`

- `02_alignment/Alignment_Layer_v1.4.md`  
  Current canonical alignment layer specification.

- `02_alignment/LifeOS_Alignment_Layer_v1.0.md`  
  Earlier alignment baseline; retained for reference (superseded by v1.4).

---

## 5. Runtime — `03_runtime/`

- `03_runtime/COO_Runtime_Core_Spec_v1.0.md`  
  Core specification for the COO Runtime.

- `03_runtime/COO_Runtime_Spec_v1.0.md`  
  Top-level COO Runtime specification.

- `03_runtime/COO_Runtime_Implementation_Packet_v1.0.md`  
  Implementation packet for COO Runtime v1.0.

- `03_runtime/COO_Runtime_Spec_Index_v1.0.md`  
  Index of COO Runtime specification documents.

- `03_runtime/COO_Runtime_Clean_Build_Spec_v1.1.md`  
  Clean build specification for the v1.1 runtime.

- `03_runtime/COO_Runtime_Walkthrough_v1.0.md`  
  Narrative walkthrough of runtime behaviour and flows.

- `03_runtime/LifeOS_Recursive_Improvement_Architecture_v0.2.md`  
  Architecture for governed, recursive self-improvement of the runtime.

---

## 6. Project Builder — `04_project_builder/`

- `04_project_builder/Antigravity_Implementation_Packet_v0.9.7.md`  
  Antigravity implementation packet integrated into LifeOS.

- `04_project_builder/ProjectBuilder_Spec_v0.9_FinalClean_v1.0.md`  
  Canonical project builder specification, final-clean v0.9, doc version 1.0.

---

## 7. Agents — `05_agents/`

- `05_agents/COO_Agent_Mission_Orchestrator_Arch_v0.7_Aligned_v1.0.md`  
  Mission orchestrator architecture for the COO Agent (arch rev 0.7).

---

## 8. User Surface — `06_user_surface/`

- `06_user_surface/COO_Runtime_User_Surface_StageB_TestHarness_v1.1.md`  
  Specification + test harness for the v1.1 user surface (Stage B).

---

## 9. Productisation — `07_productisation/`

- `07_productisation/Productisation_Brief_v1.0.md`  
  High-level brief for productisation of LifeOS and related components.

---

## 10. Manuals — `08_manuals/`

- `08_manuals/Governance_Runtime_Manual_v1.0.md`  
  Manual describing the governance runtime and its operational usage.

---

## 11. Prompt Library — `09_prompts/`

Canonical prompt library at `09_prompts/v1.0/`.

### 11.1. Initialisers — `09_prompts/v1.0/initialisers/`

- `master_initialiser_v1.0.md`  
- `master_initialiser_universal_v1.0.md`  

  Core system initialiser prompts for models.

> Note: `Gemini System Prompt (v1.0).txt` is retained as a text artefact and may be
> migrated or versioned in a later prompts-focused phase.

### 11.2. Protocols — `09_prompts/v1.0/protocols/`

- `capability_envelope_chatgpt_v1.0.md`  
- `capability_envelope_gemini_v1.0.md`  
- `discussion_protocol_v1.0.md`  
- `stepgate_protocol_v1.0.md`  

### 11.3. Roles — `09_prompts/v1.0/roles/`

- `chair_prompt_v1.0.md`  
- `cochair_prompt_v1.0.md`  
- `reviewer_architect_alignment_v1.0.md`  
- `reviewer_l1_unified_v1.0.md`  

### 11.4. System — `09_prompts/v1.0/system/`

- `capability_envelope_universal_v1.0.md`  
- `modes_overview_v1.0.md`  

---

## 12. Meta — `10_meta/`

- `10_meta/CODE_REVIEW_STATUS_v1.0.md`  
  Current status of code review activities.

- `10_meta/governance_digest_v1.0.md`  
  Digest of recent governance changes and decisions.

- `10_meta/IMPLEMENTATION_PLAN_v1.0.md`  
  Implementation planning document for upcoming work.

- `10_meta/Review_Packet_Reminder_v1.0.md`  
  Helper/reminder for generating and using review packets.

- `10_meta/TASKS_v1.0.md`  
  Task list and operational to-do register.

- `10_meta/REVERSION_PLAN_v1.0.md`  
  Full Gate 2 reversioning plan describing all renames, moves, and archivals.

- `10_meta/DEPRECATION_AUDIT_v1.0.md`  
  Detailed record of deprecated, archived, and non-canonical artefacts.

- `10_meta/REVERSION_EXECUTION_LOG_v1.0.md`  
  Execution log template and records for Phase 1 filesystem operations.

---

## 13. Archive — `99_archive/`

### 13.1. General Archive

- `99_archive/Antigravity_Implementation_Packet_v0.9.6.md`  
- `99_archive/ARCHITECTUREold_v0.1.md`  
- `99_archive/COO_Runtime_Core_Spec_v0.5.md`  
- `99_archive/DocumentAudit_MINI_DIGEST1_v1.0.md`  

These are retained for historical context and are **non-canonical** for v1.1.

### 13.2. Concept — `99_archive/concept/`

- Distilled and Opus-based external analyses of LifeOS architecture and strategy.

### 13.3. CSO — `99_archive/cso/`

- Historical CSO operating model, strategy audit packets, and primers.
- Superseded by newer governance and strategy materials.

### 13.4. Legacy Structures — `99_archive/legacy_structures/`

Contains pre–Phase 1 folder clusters:

- `CommunicationsProtocols/`
- `Governance/`
- `pipelines/`
- `Runtime/`
- `Specs/`

These represent older organisational regimes. They are not canonical and will be selectively mined in Phase 2+ for promotion into the 00–10 structure.

---

## 14. Cross-Repository Notes

### 14.1. COOProject

- All markdown artefacts in `COOProject` are **non-canonical** relative to `/docs`.  
- Many represent:
  - Fix packs (`R6.x`), review packets, and implementation notes.
  - Project builder spec lineages and audit reports.
- They are referenced in `DEPRECATION_AUDIT_v1.0.md` as external artefacts.

### 14.2. governance-hub

- `governance-hub\prompts\v1.0\...` contains **shadow copies** of the canonical prompt library in `/docs/09_prompts/v1.0/`.
- Zipped prompt bundles (`*_prompt_library_v1.0*.zip`) are treated as build artefacts, not source.

---

## 15. Diff Summary (Phase 1 -> v1.1)

A high-level summary of key changes:

- Many unversioned files received `_v1.0` (or `_v0.1` for very early sketches).
- Runtime and user-surface specs renamed to consistent `_v1.X` form.
- Legacy `Governance`, `Specs`, `Runtime`, `CommunicationsProtocols`, and `pipelines` folders moved under `99_archive/legacy_structures/`.
- Concept and CSO strategic-layer documents moved into `99_archive` and re-versioned.
- Productisation brief moved into `07_productisation/` and versioned.
- Phase 1 audit and execution artefacts added under `10_meta/`.

For precise operation-by-operation details, see `REVERSION_EXECUTION_LOG_v1.0.md` and `DEPRECATION_AUDIT_v1.0.md`.
