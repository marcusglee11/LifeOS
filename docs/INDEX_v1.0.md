# LifeOS Documentation Index — v1.0

This index describes **all authoritative documentation** for the LifeOS governance system, COO Runtime, Project Builder, Alignment Layer, Council, and productisation stack.

All documents listed here live under:

```text
/LifeOS/docs/
```

Anything **outside** this directory or located in `/99_archive/` is **non-authoritative**, unless explicitly promoted in a later indexed version.

---

## 00 — Foundations

Location: `/LifeOS/docs/00_foundations/`

| File | Purpose |
|------|---------|
| **LifeOS_Core_Spec_v0.3.1.md** | Early constitutional + operational spec for LifeOS. |
| **LifeOS_Full_Spec_v0.3.2.md** | Mid-evolution full specification. |
| **LifeOS_Full_Spec_v1.0.md** | Latest full-form LifeOS core specification. |
| **Architecture_Skeleton.md** | Conceptual architecture skeleton for LifeOS. |

---

## 01 — Governance

Location: `/LifeOS/docs/01_governance/`

### 1.1 Constitution & Amendment Framework

| File | Purpose |
|------|---------|
| **LifeOS_Constitution_v1.1.md** | Canonical constitutional document. |
| **Governance_Index_v1.0.md** | Top-level governance map. |
| **Identity_Continuity_Rules_v1.0.md** | Identity, continuity, and persona stability rules. |
| **Constitutional_Amendment_Protocol_v1.0.md** | How formal amendments occur. |
| **Constitutional_Amendment_Bundle_Takeoff_Activation_v1.0.md** | Amendment bundle and activation mechanism. |
| **Constitutional_Integration_Bundle_v1.0.md** | Integration of amendment suites. |

### 1.2 Judiciary

| File | Purpose |
|------|---------|
| **Judiciary_Core_Spec_v1.0.md** | Global judiciary specification for LifeOS. |
| **Judiciary_Runtime_Integration_v1.0.md** | How the COO runtime integrates with the judiciary. |

### 1.3 COO Governance

| File | Purpose |
|------|---------|
| **COO_Operating_Contract_v1.0.md** | Formal governance contract defining COO behaviour and obligations. |
| **COO_Expectations_Log.md** | Living log of CEO–COO preferences for operational style. |

### 1.4 Council & Routing

| File | Purpose |
|------|---------|
| **Council_Invocation_Runtime_Binding_Spec_v1.0.md** | Rules for activating Council Mode, Chair responsibilities, binding sequence. |
| **Antigravity_Council_Review_Packet_Spec_v1.0.md** | Council review protocol for Antigravity packets. |

---

## 02 — Alignment

Location: `/LifeOS/docs/02_alignment/`

| File | Purpose |
|------|---------|
| **LifeOS_Alignment_Layer_v1.0.md** | Consolidation alignment between LifeOS, PB Spec, Antigravity. |
| **Alignment_Layer_v1.4.md** | Hardened alignment layer governing PB→COO migration, determinism, AMU₀, replay/rollback contract. |

---

## 03 — Runtime (COO Execution Engine)

Location: `/LifeOS/docs/03_runtime/`

| File | Purpose |
|------|---------|
| **COO_Runtime_Core_Spec_v1.0.md** | Primary COO Runtime Specification (formerly COOSpecv1.0Final.md). |
| **COO_Runtime_Spec_v1.0.md** | Additional runtime contract from the v1.0 spec family. |
| **COO_Runtime_Implementation_Packet_v1.0.md** | Engineering contract for implementing Runtime v1.0. |
| **COO_Runtime_Spec_Index_v1.0.md** | Runtime-level canonical index for v1.0-era documents. |
| **COO_Runtime_V1.1_Clean_Build_Spec.md** | Project structure + clean environment definition for Runtime v1.1. |
| **Runtime_Subsystem_Builder_Interface_v1.0.md** | Interface between Runtime and Subsystem Builder (Project Builder). |
| **WALKTHROUGH.md** | Internal runtime walkthrough / orientation document. |

---

## 04 — Project Builder (PB) & Antigravity

Location: `/LifeOS/docs/04_project_builder/`

| File | Purpose |
|------|---------|
| **ProjectBuilder_Spec_v0.9_FinalClean.md** | Final clean Project Builder spec (v0.9). |
| **Antigravity_Implementation_Packet_v0.9.7.md** | Current Project Builder implementation contract. |

### Archive (older PB versions)

Located under `/LifeOS/docs/99_archive/`:

- **Antigravity_Implementation_Packet_v0.9.6.md** – Historical PB implementation packet.  
- **ProjectBuilder_Spec_v0.9_PatchHistory.md** – Historical PB patch trail.

---

## 05 — Agents

Location: `/LifeOS/docs/05_agents/`

| File | Purpose |
|------|---------|
| **COO_Agent_Mission_Orchestrator_Arch_v0.7_Aligned.md** | Architecture for COO-Agent orchestration (COO/Engineer/QA). |

(Additional agent behaviour specs can be added here as the system grows.)

---

## 06 — User Surface / UX / CLI

Location: `/LifeOS/docs/06_user_surface/`

| File | Purpose |
|------|---------|
| **COO_Runtime_V1.1_User_Surface_StageB_TestHarness.md** | Definitive CLI/user-surface spec for the `coo` CLI, Stage B, DEMO V1.1, and product-level tests. |

---

## 07 — Productisation

Location: `/LifeOS/docs/07_productisation/`

| File | Purpose |
|------|---------|
| **Productisation_Brief_v1.md** | Initial externalisation + productisation path brief. |
| **Outward_Facing_Product_Pipeline_v1.md** | External product generation / pipeline spec. |
| **ChatGPT_Project_Primer_v1.0.md** | Strategic primer for ChatGPT-based project execution. |

---

## 08 — Manuals

Location: `/LifeOS/docs/08_manuals/`

| File | Purpose |
|------|---------|
| **Governance_Runtime_Manual_v1.0.md** | Operational manual: StepGate, Discussion Mode, deterministic artefacts, council roles, and runtime governance usage. |
| **Communication_Protocol_v1.md** | Global communication protocol for human–assistant workflows. |
| **Engineer_Manual_v1.0.md** | Engineering manual explaining hierarchy, precedence, versioning rules, and editing workflows. |

---

## 09 — Prompts

Location: `/LifeOS/docs/09_prompts/`

| Folder | Purpose |
|--------|---------|
| **v1.0/** | Full prompt library imported from governance-hub. |
| `v1.0/protocols/` | StepGate, Discussion Mode, Deterministic Artefact Protocol. |
| `v1.0/roles/` | Council roles – Chair, Co-Chair, L1, Architect/Alignment, etc. |
| `v1.0/system/` | System initialisers. |
| `v1.0/initialisers/` | Model-specific initialisation envelopes. |

---

## 10 — Meta

Location: `/LifeOS/docs/10_meta/`

| File | Purpose |
|------|---------|
| **COO_Project_Phase3_Status_Report.md** | System status snapshot at the end of Phase 3. |
| **CODE_REVIEW_STATUS.md** | Code review ledger. |
| **IMPLEMENTATION_PLAN.md** | Runtime/Project Builder/COO implementation plan. |
| **TASKS.md** | Task ledger. |
| **governance_digest.md** | Governance summarisation and commentary. |
| **Review_Packet_Reminder.md** | Operational reminder / documentation guidance. |
| **COO_Clean_Build_Readme.md** | Imported from ChatGPTStartingFiles; historical readme for the clean build setup. |

---

## 99 — Archive (Non-Authoritative)

Location: `/LifeOS/docs/99_archive/`

| File | Purpose |
|------|---------|
| **COO_Runtime_Core_Spec_v0.5.md** | Historical COOSpec version (superseded by v1.0). |
| **Antigravity_Implementation_Packet_v0.9.6.md** | Older PB implementation packet (superseded by v0.9.7). |
| **ARCHITECTUREold.md** | Deprecated architecture prior to v0.7-ALIGNED. |
| **ProjectBuilder_Spec_v0.9_PatchHistory.md** | Historical PB spec patch trail. |

> **Rule:** No new engineering work should be based on any document in `/99_archive/`. These files exist for historical context only.

---

## Authority Model (Summary)

When documents overlap, precedence is:

1. **LifeOS Full Spec + Constitution** (`00_foundations`, `01_governance`)  
2. **Alignment Layers** (`02_alignment`) — newer versions (e.g. v1.4) override older (v1.0) where explicitly stated.  
3. **COO Runtime Core Specs** (`03_runtime`) — v1.0 + v1.1 additions.  
4. **Project Builder Spec v0.9 + Antigravity 0.9.7** (`04_project_builder`)  
5. **Agent Orchestrator Architecture** (`05_agents`)  
6. **User Surface Specs** (`06_user_surface`)  
7. **Manuals** (`08_manuals`)  
8. **Meta** (`10_meta`)  
9. **Archive** (`99_archive`) — non-authoritative.

If a lower-level document conflicts with a higher-level one, the higher-level document wins.  
Ambiguities should be escalated via the governance/judiciary process, not silently patched.

---

## Version Footer

- **Index Version:** `INDEX_v1.0`  
- **Applies To Tree:** `/LifeOS/docs` as of the consolidation/migration completed on 2025-12-04.  
- **Change Policy:** Any structural or semantic change that affects document locations, precedence, or authority **must** create a new index version: `INDEX_v1.1`, `INDEX_v2.0`, etc.

When a new `INDEX_vX.Y.md` is created:

1. It must list **all** active documents.  
2. It must explicitly state which index version(s) it supersedes.  
3. The old index file should be moved to `/LifeOS/docs/99_archive/` or clearly marked as superseded.

---

## Diff Template for Future Index Revisions

When you create `INDEX_v1.1.md`, use the template below to record the delta from this version:

```markdown
# LifeOS Documentation Index — v1.1
_Change Log vs INDEX_v1.0_

## 1. New Files Added

- `path/to/new_file_A.md` — short description and reason for addition.
- `path/to/new_file_B.md` — short description and reason for addition.

## 2. Files Removed or Archived

- `path/to/old_file_X.md`  
  - Action: moved to `/docs/99_archive/`  
  - Reason: superseded by `path/to/new_file_Y.md`

## 3. Files Renamed or Relocated

- `old/path/File_OldName.md` → `new/path/File_NewName_v1.1.md`  
  - Reason: clarify purpose / reflect new version / better folder alignment.

## 4. Authority / Precedence Changes

- _Describe any changes to which specs are considered primary, canonical, or superseding._

## 5. Notes for Engineers and Agents

- _Any important operational or behavioural changes that arise from this index update._
```

Use this diff section at the top of each new index version so humans and agents can quickly understand **what changed** without re-reading the full tree.
