# DEPRECATION_AUDIT_v1.0.md

LifeOS Phase 1 — Reversioning & Deprecation Audit  
Scope: `/docs`, LifeOS root, COOProject, governance-hub  

---

## 1. Purpose

This audit records all **deprecations**, **archivals**, and **non-canonical** artefacts identified and formalised during Phase 1.

Deprecation means:

- The artefact is no longer canonical for the active LifeOS documentation tree.
- It has either been:
  - moved under `/docs/99_archive/`, or
  - left in an external repository and explicitly marked non-canonical.

---

## 2. Internal LifeOS Deprecations

### 2.1. Root-level `/docs` artefacts

| Path (old)                          | New Location                                      | Status    | Notes                                  |
|------------------------------------|---------------------------------------------------|-----------|----------------------------------------|
| docs/DocumentAudit_MINI_DIGEST1.md | docs/99_archive/DocumentAudit_MINI_DIGEST1_v1.0.md| ARCHIVED  | Old ad-hoc mini audit snapshot.        |

### 2.2. `99_archive` additions and normalisations

| Path (new)                                         | Status    | Notes                                           |
|----------------------------------------------------|----------|-------------------------------------------------|
| docs/99_archive/ARCHITECTUREold_v0.1.md           | ARCHIVED | Early architecture sketch, superseded.          |
| docs/99_archive/Antigravity_Implementation_Packet_v0.9.6.md | ARCHIVED | Older Antigravity implementation packet. |
| docs/99_archive/COO_Runtime_Core_Spec_v0.5.md     | ARCHIVED | Early runtime core spec.                        |
| docs/99_archive/DocumentAudit_MINI_DIGEST1_v1.0.md| ARCHIVED | See above.                                      |

All other files under `docs/99_archive/` and `docs/99_archive/legacy_structures/` are non-canonical by definition for v1.1.

### 2.3. Concept folder (LifeOS root)

All Concept docs are deprecated and archived.

| Old Path                                              | New Path                                                    | Status   | Notes                           |
|-------------------------------------------------------|-------------------------------------------------------------|----------|---------------------------------|
| Concept/Distilled Opus Abstract.md                    | docs/99_archive/concept/Distilled_Opus_Abstract_v1.0.md     | ARCHIVED | External analysis summary.      |
| Concept/Opus LifeOS Audit Prompt and Response.md      | docs/99_archive/concept/Opus_LifeOS_Audit_Prompt_and_Response_v1.0.md | ARCHIVED | External audit, round 1. |
| Concept/Opus LifeOS Audit Prompt 2 and Response.md    | docs/99_archive/concept/Opus_LifeOS_Audit_Prompt_2_and_Response_v1.0.md | ARCHIVED | External audit, round 2. |

### 2.4. CSO Strategic Layer (LifeOS root)

All CSO Strategic Layer docs are deprecated in favour of newer governance and alignment artefacts.

| Old Path                                              | New Path                                                   | Status   | Notes                          |
|-------------------------------------------------------|------------------------------------------------------------|----------|--------------------------------|
| CSO Strategic Layer/ChatGPTProjectPrimer.md           | docs/99_archive/cso/ChatGPT_Project_Primer_v1.0.md         | ARCHIVED | Historical primer.             |
| CSO Strategic Layer/CSO_Operating_Model_v1.md         | docs/99_archive/cso/CSO_Operating_Model_v1.0.md            | ARCHIVED | Earlier CSO model.             |
| CSO Strategic Layer/FULL STRATEGY AUDIT PACKET v1.md  | docs/99_archive/cso/Full_Strategy_Audit_Packet_v1.0.md     | ARCHIVED | Historical strategy audit.     |
| CSO Strategic Layer/Intent Routing Rule v1.0.md       | docs/99_archive/cso/Intent_Routing_Rule_v1.0.md            | ARCHIVED | Superseded routing draft.      |

### 2.5. Legacy `/docs` structures

The following folder clusters are now deprecated and archived under `docs/99_archive/legacy_structures/`:

| Old Path                      | New Path                                               | Status    | Notes                                                        |
|-------------------------------|--------------------------------------------------------|----------|--------------------------------------------------------------|
| docs/CommunicationsProtocols/ | docs/99_archive/legacy_structures/CommunicationsProtocols/ | ARCHIVED | Pre–Phase 1 communications protocol cluster.          |
| docs/Governance/             | docs/99_archive/legacy_structures/Governance/         | ARCHIVED | Legacy governance tree; many specs superseded elsewhere.     |
| docs/pipelines/              | docs/99_archive/legacy_structures/pipelines/          | ARCHIVED | Previous pipeline definitions and sketches.                  |
| docs/Runtime/                | docs/99_archive/legacy_structures/Runtime/            | ARCHIVED | Older runtime material duplicated elsewhere.                 |
| docs/Specs/                  | docs/99_archive/legacy_structures/Specs/              | ARCHIVED | Legacy spec tree superseded by the 00–10 structure.          |

These folders remain available for historical reference and selective re-promotion in Phase 2+, but are not canonical for Phase 1 output.

---

## 3. External Repositories

### 3.1. governance-hub

**Repository root:** `C:\Users\cabra\Projects\governance-hub\`

#### 3.1.1. Prompt library duplication

The governance-hub prompt folders mirror the canonical prompt library:

- `prompts/v1.0/initialisers/`
- `prompts/v1.0/protocols/`
- `prompts/v1.0/roles/`
- `prompts/v1.0/system/`

**Status: `DUPLICATE_SHADOW`**

Canonical sources are:

- `docs/09_prompts/v1.0/...`

Zipped prompt bundles:

- `governance_hub_prompt_library_v1.0.zip`
- `prompt_library_v1.0_full.zip`

**Status: `BUILD_ARTEFACT` (non-source)**

**Phase 1 action:** No moves or deletions.  
**Phase 2 suggestion:** Regenerate zips from `/docs/09_prompts/v1.0/` as needed, and optionally remove duplicated `.md` copies in governance-hub to avoid drift.

---

### 3.2. COOProject

**Repository root:** `C:\Users\cabra\Projects\COOProject\`  

COOProject contains:

- Fix packs and review packets (`AICouncilReview/ReviewArtefacts`, `coo-agent/council_review`).
- Spec shadows and implementation packets (`coo-agent/docs/specs`, `Spec/`).
- Planning notes and hygiene reports (`Ideas&Planning/`, `coo-agent/repository_hygiene_report.md`, etc.).
- Prompt shadows (`coo-agent/prompts/`).
- Third-party licence files under virtual environments.

#### 3.2.1. Canonical status

For Phase 1:

- All COOProject `.md` files are **non-canonical** relative to `/docs`.
- They are classified at a high level as:

  - `FIX_PACK` — runtime and demo fix packets (R6.x, v1.1, etc.).
  - `REVIEW_PACKET` — council/system reviews and acceptance packets.
  - `SPEC_SHADOW` — specs that have conceptual equivalents in `/docs`.
  - `IMPLEMENTATION_PACKET` — implementation packets for runtime, demos, or builder.
  - `PLANNING_NOTE` — gap maps, hygiene reports, snapshots, status reports.
  - `PROMPT_SHADOW` — prompts that are not the canonical prompt library.
  - `THIRDPARTY_LICENSE` — licence documents from dependencies.

#### 3.2.2. Phase 1 filesystem actions

- No COOProject files are moved or renamed by Phase 1.
- COOProject serves as a **development history** repository.

#### 3.2.3. Examples (non-exhaustive but representative)

| Example Path (COOProject)                                              | Type                | Status         | Notes                                        |
|------------------------------------------------------------------------|---------------------|----------------|----------------------------------------------|
| AICouncilReview/ReviewArtefacts/COO Runtime v1.0 — R6.5 FIX PACK.md    | FIX_PACK            | NON_CANONICAL  | Runtime fix packet; history only.            |
| coo-agent/council_review/COO_Runtime_V1.1_StageB_Review_Packet.md      | REVIEW_PACKET       | NON_CANONICAL  | Council review of Stage B implementation.    |
| coo-agent/docs/specs/Alignment_Layer_v1.4.md                           | SPEC_SHADOW         | NON_CANONICAL  | Shadow of canonical alignment spec in `/docs`.|
| coo-agent/docs/specs/LifeOS_v1.1Core_Specification.md                  | SPEC_SHADOW         | NON_CANONICAL  | Candidate for future promotion.              |
| coo-agent/impl/IMPLEMENTATION_PACKET_v1.0.md                           | IMPLEMENTATION_PACKET| NON_CANONICAL | Implementation detail; not a core spec.      |
| Ideas&Planning/COO_Project_Phase3_Status_Report.md                     | PLANNING_NOTE       | NON_CANONICAL  | Planning/status only.                        |
| coo-agent/prompts/coo/system.md                                       | PROMPT_SHADOW       | NON_CANONICAL  | Prompt, not canonical library.               |
| coo-agent/venv/.../LICENSE.md                                         | THIRDPARTY_LICENSE  | NON_CANONICAL  | Dependency licence; outside LifeOS docs.     |

A full, line-by-line COOProject map is available from the underlying tree scan (`COOProject_DocTree_Scan_v1.0.txt`), but that scan itself is considered a tooling artefact, not part of the canonical docs.

---

## 4. Policy Summary

After Phase 1:

- `/docs` is the **only canonical documentation tree**.
- Anything under `/docs/99_archive/` is **deprecated** or purely historical.
- Anything under `/docs/99_archive/legacy_structures/` is a legacy layout that must not be used as a source of truth.
- Any artefact that lives only in COOProject or governance-hub is **non-canonical** unless explicitly imported into `/docs` in a future phase.
- Phase 2+ may promote selected external artefacts into `/docs` using strict `_vX.Y` naming and explicit index entries.
