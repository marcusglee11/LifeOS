# T-030 Council Review Remediation

## Header

- Title: `T-030 Council Review Remediation`
- Status: `APPROVED`
- Version: `1.1`
- Authors: `codex`
- Related: `T-030`, `artifacts/plans/PLAN_COO_COORDINATION_LOOP_v1.0.md`, `artifacts/review_packets/Review_Packet_COO_Coordination_Loop_v1.0.md`
- Worktree: `python3 scripts/workflow/start_build.py t030-remediation --kind fix`

## Context

The first `T-030` council run returned `Revise`. The blocking findings were:

- weak provenance because `artifacts/plans/PLAN_COO_COORDINATION_LOOP_v1.0.md` exists on disk but is not tracked by git
- stale source-plan references to `artifacts/reviews/` instead of `artifacts/review_packets/`
- CT-6 wording that was broader than the runtime can enforce
- naming drift between proposal text and runtime: `decision_support_needed` vs `decision_support_required`
- no authoritative ruling linkage for resolved `council_request.v1`
- `sprint_close_packet.v1` cited as mandatory without a deterministic wrapper-level emission rule
- empty Appendix A in the review packet

This sprint fixes those issues first, reruns the narrow `T-030` council review, and only then stewards protected-path changes if the rerun ruling is `docs/01_governance/Council_Ruling_COO_Loop_v1.0.md` with `**Decision**: APPROVED`.

## Goals

- Track the existing `artifacts/plans/PLAN_COO_COORDINATION_LOOP_v1.0.md` file in git and normalize its packet-path references.
- Make CT-6 machine-aligned by binding it to `task.decision_support_required == true`.
- Extend `council_request.v1` with authoritative `approval_ref` linkage and bounded expiration.
- Make dispatch wrappers emit `sprint_close_packet.v1` deterministically without changing the wrapper call signature.
- Rerun the narrow `T-030` council review with `codex`, `claude`, and `gemini` CLI seats.
- Steward `CLAUDE.md` and `config/governance/delegation_envelope.yaml` only after an approving rerun ruling.

Done means:

- source plan, review packet, and CCP are tracked and internally consistent
- runtime/schema/wrapper fixes are implemented and tested
- rerun archive contains five seat outputs plus synthesis artifacts
- protected-path changes are applied only if the rerun ruling contains `**Decision**: APPROVED`
- otherwise `T-030` remains blocked and no protected-path implementation is merged

## Proposed Changes

| file | operation | description |
| --- | --- | --- |
| `artifacts/plans/PLAN_COO_COORDINATION_LOOP_v1.0.md` | `CREATE` | Track the existing on-disk plan in git, normalize `artifacts/reviews/` to `artifacts/review_packets/`, and narrow CT-6 wording to match the remediation basis |
| `artifacts/plans/PLAN_T030_COUNCIL_REVIEW_REMEDIATION_v1.1.md` | `CREATE` | Record the approved remediation plan as a tracked implementation artifact |
| `artifacts/review_packets/Review_Packet_COO_Coordination_Loop_v1.0.md` | `CREATE` | Track the existing review packet in git, update scope/provenance/runtime citations, and populate Appendix A with proposed protected-file contents |
| `artifacts/council_reviews/coo_loop_t030.ccp.yaml` | `CREATE` | Track the existing CCP in git and align it to the corrected source plan, CT-6 semantics, and rerun criteria |
| `artifacts/coo/schemas.md` | `MODIFY` | Extend `council_request.v1` docs with `approval_ref`, `expires_at`, and explicit staleness rule; keep `sprint_close_packet.v1` as the authoritative packet schema |
| `runtime/orchestration/coo/approval_refs.py` | `CREATE` | Shared approval-ref validator for rulings under `docs/01_governance/` |
| `runtime/orchestration/coo/closures.py` | `MODIFY` | Enforce `approval_ref` on resolved council requests, support effective expiry, and keep sprint-close write/validate as the emission path |
| `runtime/orchestration/coo/auto_dispatch.py` | `MODIFY` | Enforce CT-6 against stale/unapproved council requests and return CT-6-specific block reasons |
| `runtime/orchestration/coo/sync_check.py` | `MODIFY` | Reuse the shared approval-ref validator instead of duplicating ruling-marker logic |
| `runtime/orchestration/coo/commands.py` | `MODIFY` | Surface stale council requests in `coo process-closures` output |
| `runtime/tests/orchestration/coo/test_closures.py` | `MODIFY` | Cover `approval_ref`, `expires_at`, effective expiry, and legacy resolved-request rejection |
| `runtime/tests/orchestration/coo/test_auto_dispatch.py` | `MODIFY` | Cover stale requests, invalid approval refs, mismatched `related_tasks`, and CT-6 reason strings |
| `runtime/tests/orchestration/coo/test_sync_check.py` | `MODIFY` | Confirm shared approval-ref validation behavior |
| `runtime/tests/orchestration/coo/test_commands.py` | `MODIFY` | Confirm `process-closures` reports unresolved and stale requests |
| `scripts/workflow/emit_sprint_close_packet.py` | `CREATE` | Thin CLI wrapper around `write_sprint_close_packet()` that exits non-zero on validation or write failure |
| `scripts/workflow/dispatch_codex.sh` | `MODIFY` | Keep `<topic> <task>` contract, derive `task_ref` from the task text, derive `order_id`, emit sprint-close packet, and fail closed if emission fails |
| `scripts/workflow/dispatch_opencode.sh` | `CREATE` | OpenCode wrapper with the same `<topic> <task>` contract and fail-closed sprint-close emission |
| `config/tasks/backlog.yaml` | `MODIFY` | Update `T-030` wording so the DoD reflects wrapper-level sprint-close emission with unchanged wrapper signature |
| `runtime/tests/test_emit_sprint_close_packet.py` | `CREATE` | Script-level tests for packet emission and failure behavior |
| `CLAUDE.md` | `MODIFY` | After approval only, require sprint-close packet emission in the handoff checklist for dispatched build/content work |
| `config/governance/delegation_envelope.yaml` | `MODIFY` | After approval only, register CT-6 as the governance label for `decision_support_required: true` with advisory contexts only |
| `docs/01_governance/Council_Ruling_COO_Loop_v1.0.md` | `CREATE` | Steward the rerun ruling; only `**Decision**: APPROVED` unlocks protected-path implementation |
| `docs/INDEX.md` | `MODIFY` | Update timestamp if the rerun ruling and protected docs are stewarded |
| `docs/LifeOS_Strategic_Corpus.md` | `MODIFY` | Regenerate if the rerun ruling and protected docs are stewarded |

## Verification Plan

### Automated Tests

Run before the first edit:

```bash
python3 scripts/workflow/start_build.py t030-remediation --kind fix
pytest runtime/tests -q
```

Run after the runtime/schema group:

```bash
pytest runtime/tests -q
```

Run after the wrapper group:

```bash
pytest runtime/tests -q
python3 scripts/workflow/quality_gate.py check --scope changed --json
```

Run after protected-path stewardship, if the rerun approves:

```bash
pytest runtime/tests -q
python3 scripts/workflow/quality_gate.py check --scope changed --json
python3 -m doc_steward.cli dap-validate .
git status --porcelain=v1
```

### Manual Verification

- `artifacts/plans/PLAN_COO_COORDINATION_LOOP_v1.0.md` is git-tracked and references `artifacts/review_packets/`, not `artifacts/reviews/`
- `artifacts/review_packets/Review_Packet_COO_Coordination_Loop_v1.0.md` is git-tracked and non-empty
- `CT-6` in the packet and envelope is defined only as the governance trigger for `decision_support_required: true`
- Appendix A in the review packet contains proposed post-approval contents for `CLAUDE.md` and `delegation_envelope.yaml`
- rerun archive contains five seat outputs plus `summary.json` and `draft_ruling_COO_Loop_v1.0.md`
- `docs/01_governance/Council_Ruling_COO_Loop_v1.0.md` exists before any protected-path stewardship
- `T-030` is treated as unlocked only when that ruling contains `**Decision**: APPROVED`
- `config/tasks/backlog.yaml` reflects the unchanged wrapper signature and updated T-030 DoD
- all in-repo `CR-*.yaml` fixtures are searched before merge and any resolved legacy packet without `approval_ref` is updated or intentionally left invalid

## Risks

- The rerun may still return `Revise`.
  Mitigation: stop after the ruling and keep `T-030` blocked.
- Tracking the existing untracked source plan may expose further drift.
  Mitigation: normalize the source plan and review packet together before the rerun.
- Requiring `approval_ref` for resolved council requests invalidates legacy resolved CR files.
  Mitigation: search all in-repo `CR-*.yaml` fixtures before merge and update or intentionally invalidate each one in the same change set.
- Derived expiry for legacy unresolved CR files may hide old stale requests until first read.
  Mitigation: `process-closures` and CT-6 checks must both report stale requests explicitly.
- Wrapper parsing of task IDs from task text can fail on malformed prompts.
  Mitigation: fail before dispatch unless the prompt contains exactly one canonical `T-###...` ID, and update wrapper usage examples accordingly.
- Sprint-close emission may fail after a successful agent run, leaving work completed but handoff blocked.
  Mitigation: use atomic writes, propagate a non-zero wrapper exit, and record the final wrapper exit in the invocation receipt.
- Doc stewardship may fail after the rerun ruling is drafted.
  Mitigation: validate the draft ruling in the archive before copying it to `docs/01_governance/`, then run `dap-validate`.

## Rollback

1. If failure occurs before the rerun, revert the fix-branch commits for source-plan, packet, runtime, wrapper, and test changes with `git revert <sha>` in reverse order, rerunning `pytest runtime/tests -q` after each revert group.
2. If the rerun verdict is `Revise` or `Reject`, do not steward `CLAUDE.md` or `config/governance/delegation_envelope.yaml`; keep the archive for audit and leave `T-030` blocked.
3. If the rerun is approving but protected-path implementation later proves faulty, open a new fix worktree and obtain new council approval before reverting `CLAUDE.md` or `config/governance/delegation_envelope.yaml`.
4. If only the ruling/doc stewardship fails, restore from the validated draft ruling in the archive rather than editing the protected doc ad hoc.
5. Do not delete the tracked `artifacts/plans/PLAN_COO_COORDINATION_LOOP_v1.0.md`; if it must later be superseded, create `v1.1` and mark `v1.0` obsolete.

## Assumptions

- The existing on-disk `artifacts/plans/PLAN_COO_COORDINATION_LOOP_v1.0.md` is the intended provenance source rather than a superseded draft.
- `sprint_close_packet.v1` remains defined by `artifacts/coo/schemas.md` and `runtime/orchestration/coo/closures.py`.
- The rerun remains `T-030`-only and does not reopen `T-027` through `T-029`.
- The same three CLI providers are available for the rerun: `codex`, `claude`, and `gemini`.
- Wrapper callers can supply task text containing exactly one canonical backlog task ID.
- Lessons learned and automatic remediation-plan generation are follow-on process work, not part of this plan’s done condition.
