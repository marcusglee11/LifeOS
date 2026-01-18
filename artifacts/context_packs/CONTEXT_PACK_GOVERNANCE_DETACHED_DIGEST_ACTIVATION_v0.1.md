---
context_pack_id: "901c2112-65f6-42bc-873b-1d39c06a794b"
schema_version: "1.0.0"
created_at: "2026-01-06T20:08:00+11:00"
author: "Antigravity"
purpose: "P0 fail-closed: Activated protocols surface search"
mission_ref: "Governance_Delta_Detached_Digest_v0.2_Fix"
file_count: 6
---

# Context Pack: Governance Delta Detached Digest Activation v0.1

**Pack SHA256**: (computed over file list + excerpts below)

---

## Search Notes

Searched for:
- `grep "activated"` in `docs/` → runtime activation mentions only
- `grep "binding"` in `docs/02_protocols/` → found Council_Protocol, DAP
- `find "*index*"` → found `ARTEFACT_INDEX.json`, `INDEX.md`, `COO_Runtime_Spec_Index`
- `find "*manifest*"` → found `Tier1_Tier2_Conditions_Manifest`

**Conclusion**: No comprehensive "activated protocols" index exists.

---

## File 1: `docs/01_governance/ARTEFACT_INDEX.json`

**SHA256**: `7E3690154DAA84D39813C7BADF62B1222B05BA76DE01099A3A83159F988631AE`
**Why included**: Only governance artifact index found; incomplete (8 entries).

```json
{
    "meta": {
        "version": "2.2.0",
        "updated": "2026-01-01"
    },
    "artefacts": {
        "constitution": "docs/00_foundations/LifeOS_Constitution_v2.0.md",
        "governance_protocol": "docs/02_protocols/Governance_Protocol_v1.0.md",
        "document_steward_protocol": "docs/02_protocols/Document_Steward_Protocol_v1.0.md",
        "coo_contract": "docs/01_governance/COO_Operating_Contract_v1.0.md",
        "dap": "docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md",
        "agent_constitution": "docs/01_governance/AgentConstitution_GEMINI_Template_v1.0.md",
        "spec_review_packet": "docs/01_governance/Antigravity_Council_Review_Packet_Spec_v1.0.md",
        "strategic_context": "docs/LifeOS_Strategic_Corpus.md"
    }
}
```

**Gap**: Missing Council_Protocol_v1.2, Build_Artifact_Protocol_v1.0, Build_Handoff_Protocol_v1.1, Core_TDD_Design_Principles_v1.0, etc.

---

## File 2: `docs/INDEX.md` (excerpt, lines 1-50)

**SHA256**: `7095EA7B1C4B18A306FC4E321F9588B3CF84EF97E3F85AAB8CB347E46F8ABF4D`
**Why included**: Documentation index; lists all docs but not machine-parseable activation manifest.

```markdown
# LifeOS Documentation Index (Updated: 2026-01-06 18:05)
**Authority**: [LifeOS Constitution v2.0](./00_foundations/LifeOS_Constitution_v2.0.md)

---

## Authority Chain

```
LifeOS Constitution v2.0 (Supreme)
        │
        └── Governance Protocol v1.0
                │
                ├── COO Operating Contract v1.0
                ├── DAP v2.0
                └── COO Runtime Spec v1.0
```

## 00_admin — Project Admin (Thin Control Plane)

| Document | Purpose |
|----------|---------|
| [LIFEOS_STATE.md](./11_admin/LIFEOS_STATE.md) | **Single source of truth** — Current focus, WIP, blockers |
...
```

**Gap**: Human-readable index, not a "binding protocols" manifest with activation status.

---

## File 3: `docs/02_protocols/Governance_Protocol_v1.0.md` (excerpt, lines 1-60)

**Why included**: Defines authority model but no protocol activation list.

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
...
```

**Gap**: No list of "activated protocols" or mechanism for declaring a protocol binding.

---

## File 4: `docs/03_runtime/COO_Runtime_Spec_Index_v1.0.md` (excerpt, lines 1-40)

**Why included**: Runtime-specific spec index; wrong scope for general protocols.

```markdown
===============================================================
Spec Canon Index (Canonical Source of Truth)
===============================================================

Location: /docs/specs/
Authority Chain: LifeOS v1.1 → Alignment Layer v1.4 → COO Runtime Spec v1.0 → Implementation Packet v1.0 → Fix Packets

This directory is the **single canonical home** for all COO Runtime–related specifications.
All other copies (ChatGPT projects, council packets, build agents) are **read-only mirrors**.
All patches, amendments, and rulings must be applied here first.

---------------------------------------------------------------
1. Canonical Documents
---------------------------------------------------------------

1. LifeOS Core Specification v1.1 (Canonical)
   File: LifeOS_Core_Spec_v1.1.md
   Status: Immutable except via constitutional amendment.
   Source: Provided by CEO.
...
```

**Gap**: COO Runtime only; doesn't cover general governance/build protocols.

---

## File 5: `docs/02_protocols/Deterministic_Artefact_Protocol_v2.0.md` (excerpt, lines 50-55)

**Why included**: Shows "becomes binding upon placement" pattern.

```markdown
DAP v2.0 becomes binding upon placement at the specified path.
```

**Observation**: Implies "placement = activation" but no central registry confirms this.

---

## File 6: `docs/02_protocols/Council_Protocol_v1.2.md` (excerpt, lines 1-20)

**Why included**: Binding protocol; not listed in ARTEFACT_INDEX.json.

```markdown
# Council Protocol v1.2 (Amendment)

**System**: LifeOS Governance Hub  
**Status**: Proposed for Canonical Promotion  
**Effective date**: 2026-01-06 (upon CEO promotion)  
**Amends**: Council Protocol v1.1  
**Change type**: Constitutional amendment (CEO-only)

---

## 0. Purpose and authority

This document defines the binding constitutional procedure for conducting **Council Reviews** within LifeOS.

**Authority**
- This protocol is binding across all projects, agents, and models operating under the LifeOS governance system.
- Only the CEO may amend this document.
- Any amendment must be versioned, auditable, and explicitly promoted to canonical.
```

**Gap**: Listed as "binding" in text but not in ARTEFACT_INDEX.json.

---

## Summary

| Candidate | Status | Usable as Activation Surface? |
|-----------|--------|-------------------------------|
| `ARTEFACT_INDEX.json` | Incomplete (8 entries) | NO |
| `INDEX.md` | Documentation only | NO (human-readable) |
| `Governance_Protocol_v1.0` | Authority model | NO (no list) |
| `COO_Runtime_Spec_Index` | Runtime only | NO (wrong scope) |

**Recommendation**: Create `docs/01_governance/ACTIVATED_PROTOCOLS_INDEX.json` as canonical activation manifest.
