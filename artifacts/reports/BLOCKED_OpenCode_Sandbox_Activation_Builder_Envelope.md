# BLOCKED: OpenCode Sandbox Activation - Builder Envelope

**Date**: 2026-01-12
**Status**: BLOCKED

## Reason

Per **Section G2** of the CEO Instruction: "If referenced governance/protocol docs are missing... BLOCK."

## Missing Documentation

The following critical governance document is referenced in `LIFEOS_STATE.md` (v1.1) and `F7_Runtime_Antigrav_Mission_Protocol_v1.0.md` (v1.0) but is **missing** from the repository at the expected location:

- **Expected Path**: `docs/01_governance/OpenCode_First_Stewardship_Policy_v1.1.md` (or v1.0)
- **Actual State**: Not found in `docs/01_governance/`.
- **Search Results**:
  - `docs/01_governance/` listing shows 10 files, none matching `OpenCode*`.
  - `find_by_name` found `artifacts/for_ceo/deliverables/OpenCode_First_Stewardship_Policy_v1.1.md`.
  - Access to the artifact path is **blocked** by `.gitignore`, preventing verification of content.

## Impact

We cannot verify the "Mandatory routing policy" or confirm if specific Builder allowlists are mandated/forbidden by the Constitution, as required by **Section C3**.

## Next Step (Unblock)

Move the authoritative policy file from the artifacts directory to the governance directory and commit it.

```bash
# Proposed Unblock Command
mv artifacts/for_ceo/deliverables/OpenCode_First_Stewardship_Policy_v1.1.md docs/01_governance/OpenCode_First_Stewardship_Policy_v1.1.md
```
