---
artifact_id: "92c884d7-804e-4380-b8a0-de41519510d5"
artifact_type: "PLAN_PACKET"
schema_version: "1.2"
created_at: "2026-01-15T09:55:00Z"
author: "Antigravity"
version: "0.1"
status: "DRAFT"
---

# Scope Envelope

- **Goal**: Enforce clean git status and specific evidence files in closure/return packets to ensure auditability and prevent uncommitted drifts.
- **Non-Goals**: Modifying the actual closure bundle script or the git state itself.
- **In-Scope Paths**:
  - `GEMINI.md`
  - `docs/01_governance/AgentConstitution_GEMINI_Template_v1.0.md`

---

# Proposed Changes

## P0.1 Enforce Git Status in Article XII

- **Description**: Add Section 5 "Closure Invariants" to Article XII of the constitution.
- **Rationale**: Compliance with user mandate to ensure no closure occurs with a dirty worktree and that all evidence is properly hashed and included.
- **Touchpoints**:
  - `GEMINI.md`
  - `docs/01_governance/AgentConstitution_GEMINI_Template_v1.0.md`

---

# Claims

- **Claim**: Article XII must govern closure packet validity.
  - **Type**: policy_mandate
  - **Evidence Pointer**: [GEMINI.md:L70](file:///c:/Users/cabra/Projects/LifeOS/GEMINI.md#L70)
  - **Status**: asserted

- **Claim**: Constitution updates require Document Steward Protocol.
  - **Type**: policy_mandate
  - **Evidence Pointer**: [GEMINI.md:L197](file:///c:/Users/cabra/Projects/LifeOS/GEMINI.md#L197)
  - **Status**: asserted

---

# Targets

- **Target**: `GEMINI.md`
  - **Type**: modify
  - **Mode**: fixed_path
  - **Intent**: Add Section 5 to Article XII regarding Git Status invariants.

- **Target**: `docs/01_governance/AgentConstitution_GEMINI_Template_v1.0.md`
  - **Type**: modify
  - **Mode**: fixed_path
  - **Intent**: Synchronize template with the local constitution.

---

# Validator Contract

- **Output Format**: PASS/FAIL
- **Failure Codes**:
  - ERR_DIRTY_WORKTREE: `git status --porcelain` is not empty.
  - ERR_MISSING_EVIDENCE: `git_status_porcelain.txt`, `git_diff.patch`, or `evidence_manifest.sha256` missing.

---

# Verification Matrix

| Case ID | Input Fixture | Expected | Expected Code | Prefix |
|---------|---------------|----------|---------------|--------|
| PASS_01 | Empty porcelain + all files present | PASS | | |
| FAIL_01 | Dirty porcelain | FAIL | ERR_DIRTY_WORKTREE | |
| FAIL_02 | Missing `git_diff.patch` | FAIL | ERR_MISSING_EVIDENCE | |

---

# Migration Plan

- **Backward Compat**: This is a new constraint for future closure packets. Existing packets are not affected but new ones must comply.
- **Rollout Stages**:
  - 1. Update template and local constitution.
  - 1. Perform Document Steward Protocol.
- **Deprecation Rules**: N/A

---

# Governance Impact

- **Touches Constitution**: yes
- **Gate**: Article XIII Section 4
- **Rationale**: The change modifies `GEMINI.md` and a governance-controlled template, requiring explicit approval and Document Steward routing.
