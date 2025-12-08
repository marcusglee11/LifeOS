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

2. COO Runtime Specification v1.0
   File: COO_Runtime_Spec_v1.0.md
   Status: Canonical, patchable via Fix Packs and CSO rulings.

3. COO Runtime Implementation Packet v1.0
   File: IMPLEMENTATION PACKET v1.0
   Status: Canonical, implementation-specific, updated via Fix Packs.

4. Fix Packets (Historical + Active)
   Files:
     R6.3_Fix_Packet.md
     R6.4_Fix_Packet.md
     R6.5_Fix_Packet.md
   Status: Immutable once released.
   Purpose: Bind defects and amendments to specification.

---------------------------------------------------------------
2. Applied Patches (Running Log)
---------------------------------------------------------------

This log declares all specification amendments applied to canonical documents.
Each entry MUST include:
- Patch identifier  
- Affected document(s)  
- Description  
- Merge date  
- Link or reference to the Fix Pack  

### R6.5-B1 — FSM §3 (REPLAY State Removal)
Affected Documents:
- COO_Runtime_Specification_v1.0.md

Description:
- Removed REPLAY as a standalone runtime FSM state.
- Declared Gate F (Replay Determinism) as an internal sub-step inside GATES.
- Cleaned residual references.

Merge Date: 2025-12-01

Reference: R6.5 Fix Pack

### R6.5-C1A — Unified Import Update Step
Affected Documents:
- IMPLEMENTATION PACKET v1.0

Description:
- Replaced the previous conceptual separation between “update test imports” and “update production imports” with a unified deterministic AST import update step.
- Declared the unified step as the single canonical step covering both tests + runtime.

Merge Date: 2025-12-01

Reference: R6.5 Fix Pack

---------------------------------------------------------------
3. Mirror Policy
---------------------------------------------------------------

All external locations (ChatGPT projects, build agents, council packets)
must reference these canonical files by name and path.

Mirrors must begin with:

"Mirror copy — canonical version lives at /docs/specs/<filename>.  
Do not edit here."

---------------------------------------------------------------
4. Update Rules
---------------------------------------------------------------

1. All Fix Packs must update this Index immediately upon approval.
2. All canonical files must include:
   - A “Patches Applied” section referencing amendments.
   - Version header unmodified unless a new spec version is declared.
3. No downstream mirror may be considered authoritative.

---------------------------------------------------------------
END — Spec Canon Index
===============================================================
