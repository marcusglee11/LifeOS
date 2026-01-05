# BLOCKED: Council Context Pack CT-2

**Status**: BLOCKED
**Date**: 2026-01-05
**Blocking Condition**: Missing Canonical Governance Artefacts
**Rule**: Fail-Closed (User Instruction F)

---

## Missing Categories & Candidates

| Category | Missing Requirement | Closest Candidates / Findings |
|----------|---------------------|-------------------------------|
| **2) Procedural Spec** | `AI Council — Procedural Specification v1.0` | **Candidate 1**: `docs/01_governance/Council_Invocation_Runtime_Binding_Spec_v1.0.md` (Claims to bind the Proc Spec) <br> **Candidate 2**: `docs/01_governance/Antigravity_Council_Review_Packet_Spec_v1.0.md` (Mechanical spec) <br> **Note**: referenced as `contentReference[oaicite:4]{index=4}` in Binding Spec but file not found in `docs/`. |
| **3) Role Prompts** | Individual prompts for: <br> - Structural & Operational <br> - Technical <br> - Risk <br> - Simplicity <br> - Determinism | **Found**: <br> - `docs/09_prompts/v1.0/roles/reviewer_l1_unified_v1.0.md` (Unified role) <br> - `docs/09_prompts/v1.0/roles/reviewer_architect_alignment_v1.0.md` (Architect + Alignment) <br> - `docs/09_prompts/v1.0/roles/chair_prompt_v1.0.md` (Chair) <br> - `docs/09_prompts/v1.0/roles/cochair_prompt_v1.0.md` (Co-Chair) |
| **1) Protocol** | `Council Protocol v1.0` (Active) | **Found**: `docs/99_archive/legacy_structures/Specs/council/Council_Protocol_v1.0.md` (Marked as Canonical in text, but located in archive) |

## Impact
Unable to assemble a binding "Full Council" pack without the individual role prompts and the explicit procedural specification. "Full Council" implies usage of the 6 canonical roles defined in the Protocol, but only L1 Unified and Architect/Alignment prompts exist.

## Recommended Action
1. Restore or locate `AI Council — Procedural Specification v1.0`.
2. Generate or locate the individual role prompts for Structural, Technical, Risk, Simplicity, and Determinism reviewers.
