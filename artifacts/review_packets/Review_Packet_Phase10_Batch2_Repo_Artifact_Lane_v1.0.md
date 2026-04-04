# Review Packet — Phase 10 Batch 2: Repo Artifact Lane v1.0

**Status:** Draft — awaiting ratification
**Lane:** `repo_artifact_v1`
**Scope:** Mutation actions scoped to approved subdirectories of `artifacts/`

## Lane Summary

`repo_artifact_v1` adds three approval-gated mutation actions that operate on
the repo's `artifacts/` directory. All actions require explicit human approval.
Lane status is `ratification_pending` pending Council ruling.

## Action Definitions

| action_id | operation_kind | requires_approval | Description |
|---|---|---|---|
| `artifact.file.write` | mutation | true | Create or replace a file in an approved `artifacts/` subtree. Auto-creates parent dirs. Text-only. |
| `artifact.dir.ensure` | mutation | true | Ensure a directory exists in an approved subtree. Idempotent. Fails if path exists as a file. |
| `artifact.file.archive` | mutation | true | Move a file to `artifacts/99_archive/`. Fails if source is missing or destination already exists. |

## Subpath Allowlist

Allowed write subtrees: `plans/`, `review_packets/`, `evidence/`
Allowed archive destination: `99_archive/`

Explicitly excluded (path escape rejection at normalizer):
- `coo/operations/` (proposals, orders, receipts)
- `status/` (ops readiness artifacts)
- `packets/` (status packs)

## Collision Policy

`artifact.file.archive` fails if destination file already exists. No silent overwrite.

## Approval Class

All actions: `explicit_human_approval`. No unattended execution approved in this batch.

## Path Security

- `/artifacts/...` alias accepted; strip-and-resolve against artifacts root
- Relative paths resolved against artifacts root
- Other absolute paths rejected at normalizer
- Traversal escape check: resolved path must be within artifacts root
- Subpath check: first path component must be in `_ARTIFACT_ALLOWED_SUBTREES`

## Test Coverage

`runtime/tests/orchestration/ops/test_repo_artifact_lane.py`:
- Lane config: exists, ratification_pending, correct allowed_actions
- Registry: operation_kind=mutation, requires_approval=True for all 3 specs
- Path normalization: relative, alias, traversal rejection, absolute rejection
- Subpath allowlist: coo/operations/, status/, packets/ all rejected; 99_archive/ accepted
- Executor: write (creates file, creates parent dirs, rejects dir target),
  dir.ensure (creates, idempotent, rejects existing file),
  archive (moves file, missing source raises, destination collision raises)
- Receipt emission: operational_receipt.v1 stored and retrievable
- COO parser: artifact.file.write proposal accepted end-to-end

## Certification Posture (pre-ratification)

- `local`: PASS (ratification_pending allowed at local)
- `ci`: FAIL CLOSED (ratification_pending blocked at ci)
- `live`: FAIL CLOSED

## Ratification Follow-Up (separate branch after Council approval)

1. Add `docs/01_governance/Council_Ruling_Phase10_Batch2_Repo_Artifact_v1.0.md`
   with `**Decision**: RATIFIED` marker
2. Update `config/ops/lanes.yaml`: `status: ratified`,
   `approval_ref: docs/01_governance/Council_Ruling_Phase10_Batch2_Repo_Artifact_v1.0.md`
3. Update `docs/INDEX.md` and regenerate `docs/LifeOS_Strategic_Corpus.md`
4. Re-run `python3 scripts/run_ops_certification.py --profile local` → PASS
5. Re-run `python3 scripts/run_ops_certification.py --profile ci` → PASS
6. Close from linked worktree: `python3 scripts/workflow/close_build.py`
