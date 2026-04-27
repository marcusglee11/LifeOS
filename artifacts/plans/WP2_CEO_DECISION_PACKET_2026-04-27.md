# WP2 — CEO Decision Packet: Authority Audit Follow-Up

**Status:** Proposal — decision packet for CEO review
**Owner:** Active COO
**Source:** `docs/audit/LIFEOS_AUTHORITY_AUDIT_RESULT_2026-04-27.md` §H (C-003, C-008, C-009, C-010), §Open Decisions (OD-AUDIT-003, OD-AUDIT-004, OD-AUDIT-006)
**Date:** 2026-04-27
**Branch:** none — decision packet only; no binding changes implemented

---

## Decision 1: G-CBS — ratify, demote, or replace (OD-AUDIT-003, C-008)

### Problem

G-CBS Standard (`docs/02_protocols/G-CBS_Standard_v1.1.md`) is listed as "Protocol" in the audit manifest but has `Draft` status markers. The Council Protocol v1.3 treats the G-CBS closure bundle as gating, but the standard itself says draft/CT-2. This creates a circular dependency: closure requirements reference an unratified standard.

### Options

| Option | Effect | Risk |
|---|---|---|
| **A: Ratify G-CBS** — Promote through required governance process, list in authoritative index, update version to ratified | Removes closure dependency uncertainty; G-CBS becomes fully canonical | Requires Council/CEO process; may expose additional design gaps |
| **B: Demote to draft** — Remove binding G-CBS references from Council Protocol; make G-CBS advisory only | Unblocks closure without ratification; G-CBS stays as reference | Loss of closure-evidence standardisation guidance |
| **C: Replace with minimal closure standard** — Define a lightweight closure-evidence schema in the audit's AL1 sequence (see WP4); retire G-CBS dependency | Cleanest path if G-CBS scope exceeds what closure actually needs | Adds schema work; may duplicate effort |

### Recommendation

**Option A (ratify)** if the CEO wants G-CBS as the canonical closure-evidence standard.
**Option B (demote)** if the CEO wants closure unblocked now and is willing to defer G-CBS ratification.

The audit's AL1 implementation sequence (§L1) already defers full G-CBS resolution to step 8. This is consistent with Option B allowing WP4 to proceed.

### CEO decision needed

Choose A, B, or C. If A, specify ratification route (Council ruling, CEO decree, or PR). If B or C, specify whether `Council_Protocol_v1.3.md` should be patched to remove binding G-CBS references.

---

## Decision 2: Council Protocol reference alignment (C-003, OD-AUDIT-006)

### Problem

The current Council Protocol is v1.3, but binding/procedural docs reference older versions:

| Doc | Reference | Issue |
|---|---|---|
| `Council_Invocation_Runtime_Binding_Spec_v1.1.md` | Binds to unspecified council protocol version | Version gap not auditable |
| `AI_Council_Procedural_Spec_v1.1.md` | References procedural steps that may differ from v1.3 | Stale procedure risk |
| `Council_Context_Pack_Schema_v0.3.md` | Schema version may not match v1.3 protocol | Schema drift |
| `Intent_Routing_Rule_v1.1.md` | References older intent routing that may conflict | Routing authority confusion |

### Options

| Option | Effect | Effort |
|---|---|---|
| **A: Version-bump all binding docs** — Update each doc's protocol version reference to v1.3; verify procedural/context mappings | Clean authority; stale docs become current | Medium: 4-6 doc edits + review |
| **B: Pin to a version table** — Create a single `docs/01_governance/PROTOCOL_VERSION_REGISTER.md` that maps protocol surfaces to current versions; update register instead of each doc | Single source of truth for version binding | Low: one new doc + edit existing docs to reference register |
| **C: Defer** — Mark as known stale; audit C-003 documents the gap; fix when Council Protocol next receives a material revision | Zero immediate effort; gap documented | Gap persists |

### Recommendation

**Option B (version register)** — lowest long-term maintenance cost. The register can be a simple YAML/table and be referenced by docs, CI lints, and version-check tests.

### CEO decision needed

Approve approach and timeline (immediate vs deferred to next Council Protocol revision).

---

## Decision 3: DAP path/status consistency (C-009)

### Problem

The Deterministic Artefact Protocol (DAP) claims canonical placement/status and mandatory Gate 3 for artefacts, but path/status references appear inconsistent with actual repo usage and protocol workflows.

### Options

| Option | Effect | Effort |
|---|---|---|
| **A: Normalise DAP to current practice** — Update DAP path/status to reflect actual repo usage; add explicit artefact-type exceptions | Honest canonical doc; artefact creation not over-blocked | Low: 1 doc edit |
| **B: Demote DAP to advisory** — Mark DAP as guidance rather than binding protocol for audit/result artefacts | Simplest path; removes Gate 3 constraint for non-standard artefacts | Low: classification change |
| **C: Audit all artefact paths** — Exhaustive cross-reference of DAP vs all artefact paths in repo | Most thorough; highest effort | High |

### Recommendation

**Option A** — the audit's C-009 is MINOR severity, suggesting a lightweight normalisation is appropriate. Define in DAP that AWK/audit/result artefacts are exempt from Gate 3.

### CEO decision needed

Approve approach. If A, approve the specific exemption language for audit/result artefacts.

---

## Decision 4: Build Loop canonicality status (C-010, OD-AUDIT-004)

### Problem

`LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md` is listed as "Canonical per docs index" in the audit manifest (section F), but its draft/status-mixed markers and the manifest's own canonicality priority create ambiguity. Additionally, the active COO registry source is unresolved (OD-AUDIT-004).

### Options for canonicality:

| Option | Effect |
|---|---|
| **A: Add canonicality header** — Add explicit "Status: Canonical" or "Status: Working architecture — may diverge from deployed state" header | Clarity without demotion |
| **B: Demote to working architecture** — Mark as active reference that may diverge from deployed runtime | Safer; autonomous loop semantics not over-trusted |

### Recommendation

**Option A** — the Build Loop doc is actively referenced and functionally canonical for build semantics. A header clarifies status without breaking references.

### Options for active COO registry source (OD-AUDIT-004):

The audit asks which substrate is the active COO registry source for machine-checkable sole-writer enforcement. Candidates:

| Option | Effect |
|---|---|
| **A: GitHub issue label/state** — Use issue body state block or a label convention | Low ceremony; already in use implicitly |
| **B: Config file** — `config/governance/active_coo.yaml` | Machine-checkable; explicit |
| **C: GitHub Actions variable** — Repo-level variable | Branch/infra-independent |

### Recommendation

**Option B** — `config/governance/active_coo.yaml` is the cheapest machine-checkable path. The sole-writer guard reads it at dispatch time. The active COO updates it on switchover.

### CEO decision needed

1. Approve Build Loop canonicality status approach (A or B).
2. Approve active COO registry source approach (A, B, or C).

---

## Summary of CEO decisions required

| # | Decision | Options | Recommended |
|---|---|---|---|
| D1 | G-CBS ratify/demote/replace | A / B / C | B (demote) to unblock closure; ratify later |
| D2 | Council Protocol reference alignment | A / B / C | B (version register) |
| D3 | DAP path/status consistency | A / B / C | A (normalise with artefact-type exceptions) |
| D4a | Build Loop canonicality | A / B | A (canonicality header) |
| D4b | Active COO registry source | A / B / C | B (config/governance/active_coo.yaml) |

All five decisions are independent. The CEO may answer a subset now and defer the rest.