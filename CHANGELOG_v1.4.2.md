# CHANGELOG: OpenCode Steward Hardening v1.4.2

## Fixes (Council Chair Condition Satisfaction - Canonical Taxonomy Only)
- **P0.1 Allowlist Coherence**: Evidence directory permissions remain `["read"]` for steward (unchanged from v1.4.1).
- **Protocol Correction**: Reverted `docs/02_protocols/Council_Protocol_v1.2.md` to remove non-canonical `artifacts_output` tag (was added in v1.4.1, now removed).
- **P0.2 Touches Taxonomy**: Updated CCP `touches` to use canonical `governance_protocol` (instead of non-canonical `artifacts_output`) to reflect governance surface coverage.
- **P1.1 Rollback Verification**: Verification step remains in CCP Rollback Runbook (unchanged from v1.4.1).

## Summary
This revision applies only canonical taxonomy tags as required by Chair conditions. No new tags were invented. The CCP now correctly reflects:
- `tier_activation` (CT-2 activation)
- `docs_only` (doc steward scope)
- `governance_protocol` (governance-controlled activation producing review packets)

## Evidence
- **Bundle**: `Bundle_OpenCode_Steward_Hardening_CT2_v1.4.2.zip`
- **Manifest**: `artifacts/evidence/opencode_steward_certification/HASH_MANIFEST_v1.4.2.json`
