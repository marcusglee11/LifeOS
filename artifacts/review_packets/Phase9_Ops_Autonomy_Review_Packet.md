# Review Packet: Phase 9 Ops Autonomy Ratification

**Status:** Draft
**Date:** 2026-04-02
**Purpose:** CEO and Council review material for ratifying the constrained ops lane without expanding executor scope.

## Proposal

Ratify the existing `workspace_mutation_v1` lane as the only approved constrained ops lane for this phase. The lane remains human-approval-gated and limited to:

- `workspace.file.write`
- `workspace.file.edit`
- `lifeos.note.record`

## Requested Decision

- Approve or reject the initial constrained lane
- Confirm that `ci` and `live` certification must fail closed until a ruling is recorded
- Confirm that no Phase 10 lane is pre-authorized by this ruling

## Evidence Basis

- Existing executor and receipt path in `runtime/orchestration/ops/`
- Existing CLI entrypoint: `lifeos certify ops --profile local|ci|live`
- Existing lane manifest: `config/ops/lanes.yaml`
- Existing readiness artifact contract: `artifacts/status/ops_readiness.json`

## Reserved Excluded Classes

These classes remain out of scope for Phase 9 even where no concrete action ids exist yet:

- scheduling and admin reporting
- housekeeping and artifact maintenance
- broader system maintenance
- package installation
- secret access
- governance mutation

## Expected Ratification Effects

- `local` certification remains available for design validation
- `ci` and `live` fail closed while lane status is `ratification_pending`
- once ratified, the lane must reference a governing ruling under `docs/01_governance/`
- no unattended promotion occurs in this phase
