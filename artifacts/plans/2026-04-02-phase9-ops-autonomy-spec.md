# Phase 9: Constrained Ops Ratification

**Status:** Proposed
**Date:** 2026-04-02
**Scope:** Governance-and-certification hardening for the existing constrained ops surface.

## Summary

Phase 9 ratifies the already-built constrained ops path without expanding executor scope. The only initial constrained lane is `workspace_mutation_v1`, covering:

- `workspace.file.write`
- `workspace.file.edit`
- `lifeos.note.record`

No new executor actions are introduced in this phase. No Phase 10 lane is pre-authorized by default.

## Ratification Contract

- `lifeos certify ops --profile local|ci|live` remains the certification surface.
- `operation_proposal.v1` remains the COO planning packet.
- `operational_receipt.v1` remains the executor outcome packet.
- `artifacts/status/ops_readiness.json` remains ephemeral and gitignored.

Lane status is explicit:

- `ratification_pending`: local design validation allowed; `ci` and `live` must fail closed
- `ratified`: requires a valid `approval_ref` under `docs/01_governance/`

## Excluded Scope

The initial lane excludes all non-approved operational classes. Machine-readable exclusions only name action ids that already exist. Broader excluded classes remain reserved in governance text until concrete action ids exist:

- scheduling and admin reporting
- housekeeping and artifact maintenance
- broader system maintenance
- package installation
- secret access
- governance mutation

## Default Approval Outcome

- all initial actions remain `explicit_human_approval`
- no unattended operation is approved in Phase 9
- no Phase 10 expansion is pre-authorized
- any future executor expansion requires explicit enumeration in a later ruling
