# Tier-1 → Tier-2 Conditions Manifest (FP-4.x Requirements) v0.1
Authority: LifeOS Governance Council  
Date: 2025-12-09  
Status: Binding Pre-Activation Requirements  

This document enumerates all conditions that MUST be satisfied before Tier-2 orchestration is formally activated.

It is the canonical specification for Runtime Fix Pack FP-4.x.

------------------------------------------------------------
# CONDITION SET CND-1 — EXECUTION ENVELOPE & THREAT MODEL
------------------------------------------------------------

1. Runtime must declare and enforce the following execution envelope:
   - Single-process execution
   - No arbitrary subprocess execution
   - No ungoverned network I/O
   - Environment determinism (PYTHONHASHSEED=0)
   - Fully pinned interpreter + dependencies

2. Either:
   - These constraints are enforced technically, OR
   - All subprocess/network activity is routed via a deterministic, test-covered gateway.

------------------------------------------------------------
# CONDITION SET CND-2 — AMU₀ & INDEX INTEGRITY HARDENING
------------------------------------------------------------

1. AMU₀ lineage must implement **hash chaining**:
   - Each snapshot references parent hash.

2. INDEX and lineage updates must be **atomic**:
   - Write-temp + rename pattern.

3. A Governance policy must define the hash function (SHA-256), and changes require explicit Council approval.

------------------------------------------------------------
# CONDITION SET CND-3 — GOVERNANCE SURFACE IMMUTABILITY
------------------------------------------------------------

1. Runtime must not be able to modify:
   - workflow validator
   - governance protections
   - Protected Artefact Registry
   - DAP gateway

2. These surfaces must be made read-only or signature-protected.

3. A **Council-only override path** must exist:
   - Must log override events to AMU₀ lineage.
   - Must require explicit human approval.

------------------------------------------------------------
# CONDITION SET CND-4 — ANTI-FAILURE VALIDATOR HARDENING
------------------------------------------------------------

1. Expand test suite to include adversarial attempts:
   - Smuggled human steps
   - Workflow chaining to exceed effective complexity
   - Hidden human effort inside “agent” tasks

2. Add **attestation logging**:
   - Record the exact two (or fewer) human governance primitives (Intent/Approve/Veto) used per workflow.
   - Store attestation entries in AMU₀ lineage.

------------------------------------------------------------
# CONDITION SET CND-5 — OPERATIONAL SAFETY LAYER
------------------------------------------------------------

1. Provide failure-mode playbooks + tests for:
   - DAP OK / INDEX corrupted
   - Anti-Failure validator misbehaving (fail-open / fail-closed)
   - AMU₀ snapshot corruption or unreadability

2. Add **health checks**:
   - DAP write health
   - INDEX coherence
   - AMU₀ readability

3. Define a minimal **Tier-1 halt procedure**:
   - Stop process / restore last known good AMU₀.

------------------------------------------------------------
# CONDITION SET CND-6 — SIMPLIFICATION REQUIREMENTS
------------------------------------------------------------

1. Deduplicate deterministic sorting logic across DAP and INDEX updater.  
2. Simplify AMU₀ lineage representation to linear hash chain.  
3. Clarify API boundaries between runtime and governance layers.

------------------------------------------------------------
# CLOSING
------------------------------------------------------------

Completion of FP-4.x, in full compliance with these conditions, is required for:

- **Tier-2 General Activation Approval**, and  
- Issuance of **Tier-1 → Tier-2 Activation Ruling v0.2**.

This Manifest is binding on Runtime and Antigrav until superseded by Council.

Signed,  
LifeOS Governance Council  
