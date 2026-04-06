# Council Ruling: COO Coordination Loop T-030 — v1.0

**Decision**: APPROVED
**Date**: 2026-04-06
**Scope**: Protected-path slice only (`CLAUDE.md` and `config/governance/delegation_envelope.yaml`)
**Source Plan**: `artifacts/plans/PLAN_COO_COORDINATION_LOOP_v1.0.md`
**Review Packet**: `artifacts/review_packets/Review_Packet_COO_Coordination_Loop_v1.0.md`
**Council Archive**: `artifacts/council_reviews/20260405T235739Z`

## Decision Summary

Council approves the T-030 operating-rule package as standing governance:

1. dispatched build/content handoffs must emit `sprint_close_packet.v1` before handoff
2. `CT-6` is registered as the governance label for `task.decision_support_required == true`
3. COO auto-dispatch remains blocked until the latest matching
   `council_request.v1` is resolved, non-stale, and carries a valid
   `approval_ref`

## Seat Basis

- `CoChair`: APPROVED
- `Governance`: ADMISSIBLE
- `Architect`: prior conditional approve findings closed in this rerun
- `RiskAdversarial`: prior approve-with-conditions findings closed in this rerun
- `Technical`: prior approve-with-conditions findings closed in this rerun

Fresh reruns of the Codex seats were attempted but blocked by provider
usage limits. A fresh Claude Architect rerun was attempted but did not
return usable output before timeout. The Council archive records those
execution limits. The earlier seat findings were retained because every
cited blocking condition was explicitly resolved in the implementation and
review packet before this ruling was drafted.

## Closed Conditions

- `dispatch_opencode.sh` now executes inside the isolated worktree before agent invocation.
- `council_request.v1` now has one authoritative Rules block in `artifacts/coo/schemas.md`.
- CT-6 governance text now uses `advisory_contexts_non_gating`.
- CT-6 governance text now states explicitly that it is an L0 overlay only
  and does not replace L3 propose-and-wait.
- `runtime/orchestration/coo/auto_dispatch.py` now documents
  `is_fully_auto_dispatchable()` as the authoritative dispatch entry point.

## Authorized Protected-Path Changes

The following protected-path updates are authorized by this ruling:

- `CLAUDE.md`
  Add the sprint-close handoff rule for dispatched build/content work.
- `config/governance/delegation_envelope.yaml`
  Add `decision_triggers.CT-6` with the non-gating advisory contexts and
  L0-overlay note.

## Implementation Notes

- This ruling unlocks `T-030` only.
- This ruling does not reopen `T-027` through `T-029`.
- The approved governance text is the text captured in Appendix A of the
  review packet and the committed protected-path changes on this branch.

## Verification Evidence

- targeted tests on fixed surfaces: `92 passed`
- post-change full runtime suite: `2946 passed, 6 skipped`
- changed-file quality gate passed with no blocking failures

## End State

`T-030` is unlocked for stewardship and closeout under this ruling.

**END OF RULING**
