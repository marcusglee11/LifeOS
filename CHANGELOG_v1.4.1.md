# CHANGELOG: OpenCode Steward Hardening v1.4.1

## Fixes (Council Condition Satisfaction)
- **P0.1 Allowlist Coherence**: Updated `CCP_OpenCode_Steward_Activation_CT2_Phase2.md` to set `artifacts/evidence/opencode_steward_certification/**` to `["read"]` permissions (matching runner enforcement).
- **P0.2 Touches Classification**: Added `artifacts_output` to CCP `touches` list.
- **Protocol Amendment**: Updated `docs/02_protocols/Council_Protocol_v1.2.md` to formally recognize `artifacts_output` as a valid `touches` tag.
- **P1.1 Rollback Verification**: Added Step 5 to CCP Rollback Runbook (Verification of clean status and HEAD).

## Evidence
- **Bundle**: `Bundle_OpenCode_Steward_Hardening_CT2_v1.4.1.zip`
- **Verification**: All changes are text-only policy alignments; no code changes to runner or harness.
