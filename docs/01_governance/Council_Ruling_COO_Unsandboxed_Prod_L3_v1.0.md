# Council Ruling: COO Unsandboxed Prod L3

**Decision**: RATIFIED
**Date**: 2026-03-19
**Scope**: COO Unsandboxed Production Profile Promotion (L3)
**Status**: ACTIVE

## 1. Verdict Breakdown

| Lens | Provider | Initial Verdict | Post-Fix Status |
|------|----------|----------------|-----------------|
| **Risk** | gemini | Accept (high) | No changes required |
| **Implementation** | gemini | Accept (high) | No changes required |
| **Architecture** | claude_code | Revise (medium) | All findings resolved (cec9cb63) |
| **Governance** | codex | Revise (high) | All findings resolved (cec9cb63, 48b43b30) |

**Final Ruling**: The Council APPROVES COO Unsandboxed Prod L3 promotion, subject to the following conditions being satisfied prior to activation:

1. All Revise findings from run `20260319T021805Z` have been resolved (verified in commits cec9cb63, 48b43b30)
2. Re-run of council review produces Accept verdict (Task 3 below)
3. Gate-5 soak window completed (16 clean runs, 4 sessions, 2 calendar days)
4. CEO completes gate-6 UAT handoff

## 2. Closure Statement

### Governance Findings (Resolved)
- **Gate-3 ruling verification**: `gate3_prepare.py` now validates ruling file exists under `docs/01_governance/` and contains RATIFIED/APPROVED marker before sealing (fail-closed).
- **Promotion guard hardening**: `promotion_guard.py` now validates ruling_ref file existence, path normalization, and delegation_envelope_sha256 integrity.
- **Shell injection (CWE-78)**: `openclaw_verify_surface.sh` replaced `python3 -c` interpolation with heredoc+argv; PROFILE_NAME validated against safe character set.
- **Path traversal (CWE-22)**: `LIFEOS_COO_CAPTURE_LABEL` sanitized to `[A-Za-z0-9._-]+`; output path boundary-checked.

### Architecture Findings (Resolved)
- **Soak runner fallthrough**: `apply_reset()` raises `ValueError` on unrecognized reason values.
- **Gate-3 idempotency**: Raises `RuntimeError` if manifest already sealed.
- **Gate-6 hardcoded ruling ref**: Reads from sealed manifest instead of literal path.
- **Missing capture dump**: `_maybe_capture_dump` now called in `--execute` auto-dispatch branch.
- **Private symbol coupling**: `classify_coo_response()` exposed as public API; controller updated.

### Least-Privilege Acknowledgment
The candidate profile (`coo_unsandboxed_prod_l3.json`) deliberately sets `unsandboxed: true`, session sandbox not required, and elevated disable not required. This is an accepted design trade-off to enable production COO autonomy at L3. Blast radius is bounded by:
- Delegation envelope ceiling: `[L0, L3, L4]`
- Approval manifest hash-binding (profile + envelope + ruling)
- Deterministic rollback to `coo_shared_ingress_burnin.json`
- `verify_surface.sh` runtime enforcement on every invocation

## 3. Conditions

| ID | Condition | Status |
|----|-----------|--------|
| C1 | Revise findings resolved | RESOLVED (cec9cb63, 48b43b30) |
| C2 | Council re-run Accept | PENDING (Task 3) |
| C3 | Gate-5 soak complete | PENDING |
| C4 | Gate-6 CEO UAT | PENDING |

## 4. Evidence References

- **Council Run**: `artifacts/council_reviews/20260319T021805Z/`
- **Live Result**: `artifacts/council_reviews/20260319T021805Z/live_result.json`
- **Review Packet**: `artifacts/review_packets/Review_Packet_COO_Unsandboxed_Prod_L3_Council_Dogfood_v1.0.md`
- **Hardening Commit**: `cec9cb63` (10 findings fixed, 5 regression tests added)
- **API Cleanup Commit**: `48b43b30` (classify_coo_response public API)
