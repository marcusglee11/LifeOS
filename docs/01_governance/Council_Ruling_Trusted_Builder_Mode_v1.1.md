# Council Ruling: Trusted Builder Mode v1.1

**Decision**: RATIFIED
**Date**: 2026-01-26
**Scope**: Trusted Builder Mode v1.1 (Loop Retry Plan Bypass)
**Status**: ACTIVE

## 1. Verdict Breakdown

| Reviewer | Verdict | Notes |
|---|---|---|
| **Claude** | APPROVE | - |
| **Gemini** | APPROVE | - |
| **Kimi** | APPROVE_WITH_CONDITIONS | Conditions C1–C6 satisfied (see evidence). |
| **DeepSeek** | APPROVE | P0 blockers (B1–B3) resolved in v1.1 delta. |

**Final Ruling**: The Council unanimously APPROVES Trusted Builder Mode v1.1, enabling restricted Plan Artefact bypass for patchful retries and no-change test reruns, subject to the strict fail-closed guards implemented.

## 2. Closure Statement

All P0 conditions for "Trusted Builder Mode v1.1" have been satisfied:

* **Normalization (C1)**: Failure classes canonicalized.
* **Patch Seam (C2)**: Eligibility computed from concrete patch diffstat only.
* **Protected Paths (C3)**: Authoritative registry wired fail-closed.
* **Audit Logic (C4/C5)**: Ledger and Packets contain structured bypass info.
* **Fail-Closed Invariants (DeepSeek)**: Speculative build timeouts, path evasion checks, and budget atomicity (locks) are active.

## 3. Deferred Items (P1 Backlog)

The following non-blocking enhancements are deferred to the P1 backlog (Phase 4):

1. **Ledger Hash Chain**: Cryptographic linking of bypass records.
2. **Monitoring**: Alerting on high bypass utilization.
3. **Semantic Guardrails**: Heuristics to detect "meaningful" changes beyond protected path checks (only if allowlist expands).

## 4. Evidence References

* **Proposal**: [Council_Proposal_Trusted_Builder_v1.1.md](../../artifacts/Council_Proposal_Trusted_Builder_v1.1.md)
* **Evidence Packet**: [Council_Rereview_Packet__Trusted_Builder_Mode_v1.1__P0_Fixes.md](../../artifacts/Council_Rereview_Packet__Trusted_Builder_Mode_v1.1__P0_Fixes.md)
* **Verbatim Transcript**: [Council_Evidence_Verbatim__Trusted_Builder_Mode_v1.1.md](../../artifacts/Council_Evidence_Verbatim__Trusted_Builder_Mode_v1.1.md)

Bundle (Non-Versioned):
* Path: artifacts/packets/council/CLOSURE_BUNDLE_Trusted_Builder_Mode_v1.1.zip
* SHA256: c7f36ea5ad223da6073ff8b2c799cfbd249c2ff9031f6e101cd2cf31320bdabf
* Note: artifacts/packets/ is runtime artefact storage and is gitignored (not version-controlled). Canonical record is the ruling + proposal + evidence packet in-repo.
