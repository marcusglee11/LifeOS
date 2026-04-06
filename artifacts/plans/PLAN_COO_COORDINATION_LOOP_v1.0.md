# COO Coordination Loop - Closure Artifacts and Decision-Support Gate

## Header

- Title: `COO Coordination Loop - Closure Artifacts and Decision-Support Gate`
- Status: `APPROVED`
- Version: `1.0`
- Authors: `claude_code`, `codex`
- Tasks: `T-027`, `T-028`, `T-029`, `T-030`
- Branch kind: `build`
- Gate: `Council approval required before protected-path edits`

## Context

The user is still the manual coordination hub between agents and the COO. This plan closes that loop by introducing file-based sprint-close and decision-support artifacts, a deterministic closure-ingestion command, and a dispatch gate for tasks requiring council clearance.

This plan intentionally keeps the new packet family out of `docs/02_protocols/schemas/lifeos_packet_schemas_CURRENT.yaml`. These are file-based COO coordination artifacts documented in `artifacts/coo/schemas.md`, not live envelope packets.

## Goals

- Add `sprint_close_packet.v1`, `session_context_packet.v1`, and `council_request.v1` to `artifacts/coo/schemas.md`.
- Add `artifacts/dispatch/closures/` as the dedicated closure directory.
- Add `decision_support_required: bool = False` to `TaskEntry` and preserve it across all serialization and state-transition paths.
- Add `lifeos coo process-closures`.
- Add a 7th auto-dispatch predicate blocking L0 dispatch until matching council clearance exists.
- Add agent-side sprint-close emission in dispatch wrappers.
- After Council approval only, update `CLAUDE.md` and `config/governance/delegation_envelope.yaml`.

## Pre-Execution Gate

Before any implementation work that touches protected paths:

- submit an `escalation_packet.v1` to the CEO queue requesting approval to edit:
  - `CLAUDE.md`
  - `config/governance/delegation_envelope.yaml`
- reference this plan by path
- wait for `docs/01_governance/Council_Ruling_COO_Loop_v1.0.md`
- require `**Decision**: APPROVED`

Protected-path implementation work is sequenced last as `T-030`.

## Council Review Unlock Process

This plan uses two distinct approval gates:

1. standard implementation-plan approval for the full build
2. CT-2 style council review only for the protected-path slice in `T-030`

Unlock rules:

- `T-027`, `T-028`, and `T-029` may begin only after this plan is explicitly approved
- `T-030` remains blocked until the council ruling gate below is satisfied

### Gate 1: plan approval

Before starting any build work:

- review this plan against `docs/02_protocols/Project_Planning_Protocol_v1.0.md §4`
- fix any rubric failures before moving status forward
- require explicit user approval of this plan before implementation starts

### Gate 2: council review for `T-030`

The council review scope is intentionally narrow. It is not a review of the entire implementation plan. The artefact under review is the protected-path portion only:

- mandatory `sprint_close_packet.v1` handoff requirement in `CLAUDE.md`
- `CT-6` as the governance label for `decision_support_required: true` in `config/governance/delegation_envelope.yaml`
- formal `CT-6` registration in the delegation framework so the COO enforces it through delegation-trigger evaluation

Council is being asked to approve these operating rules as protocol, not merely as implementation details. The decision question is:

- should LifeOS adopt mandatory close reporting and a formal council-escalation trigger as standing operating rules across agent handoff and COO delegation

Required council inputs:

1. Artefact Under Review:
   - this plan, with focus limited to `T-030`
   - exact protected files to be edited
   - proposed `CT-6` trigger semantics
2. Role Set:
   - `Architecture`
   - `Governance`
   - `Risk`
3. Council Objective:
   - decide whether the protected-path governance updates are safe, correctly scoped, admissible, and appropriate as standing operating rules
4. Output Requirements:
   - consolidated verdict
   - mandatory fixes, if any
   - explicit unlock decision for `T-030`

Required council package contents:

- approved implementation plan path: `artifacts/plans/PLAN_COO_COORDINATION_LOOP_v1.0.md`
- review packet path: `artifacts/review_packets/Review_Packet_COO_Coordination_Loop_v1.0.md`
- exact approval payload:
  - `CLAUDE.md` protocol change: agents must emit `sprint_close_packet.v1` at handoff
  - `config/governance/delegation_envelope.yaml` governance change: define `CT-6` as the governance trigger for tasks with `decision_support_required: true`, requiring `council_request.v1` emission and blocking auto-dispatch until resolved by a council member
  - delegation framework change: register `CT-6` as a formal trigger so COO enforcement is deterministic
- exact decision questions:
  - does Council approve mandatory `sprint_close_packet.v1` emission at handoff as a protocol requirement across agents
  - does Council approve `CT-6` as the governance label for decisions an agent cannot resolve alone
  - does Council approve registering `CT-6` in the delegation framework so unresolved `council_request.v1` artifacts block COO auto-dispatch
  - is `CT-6` narrow enough to avoid over-escalation while still covering the intended decision classes
  - are any wording, scope, or boundary fixes required before protected-path implementation

Council execution requirements:

- fail closed if any required input is missing
- fail closed if any reviewer output is malformed relative to the canonical verdict/issues/invariant template
- require `Governance` and `Risk` to be independent models
- treat `Revise`, `Reject`, degraded lens coverage, or unresolved conditions as blocking outcomes

Unlock artifact and decision rule:

- council output must be stewarded into `docs/01_governance/Council_Ruling_COO_Loop_v1.0.md`
- the final ruling must contain the exact marker `**Decision**: APPROVED`
- `T-030` is locked until that file exists with that marker
- if the ruling returns conditions, all conditions must be resolved before `T-030` starts

## Architectural Decisions

- New packet family lives in `artifacts/coo/schemas.md`.
- New packet family is file-based, not live COO model-output.
- `runtime/orchestration/coo/service.py` remains unchanged in this sprint.
- `classify_coo_response()` remains unchanged in this sprint.
- New file-based packet logic lives in `runtime/orchestration/coo/closures.py`.
- Closure directory is `artifacts/dispatch/closures/`.
- `artifacts/dispatch/completed/` remains exclusively owned by the dispatch engine.
- `decision_support_required` is a first-class `TaskEntry` field with default `False`.
- `council_request.v1` must include `related_tasks`, `resolved`, `resolved_at`, and an authoritative `approval_ref` when resolved so dispatch gating is deterministic.
- Agent enum in new packet fields is fixed to:
  - `codex | claude_code | gemini | opencode`
- Review packet location is fixed to:
  - `artifacts/review_packets/Review_Packet_COO_Coordination_Loop_v1.0.md`
- `artifacts/for_ceo/` is treated as an existing directory if present; if absent, create `artifacts/for_ceo/.gitkeep` during `T-027`.

## Proposed Changes

| file | operation | description |
| --- | --- | --- |
| `artifacts/coo/schemas.md` | `MODIFY` | Add new file-based COO packet schemas |
| `artifacts/dispatch/closures/.gitkeep` | `CREATE` | Establish closures directory |
| `artifacts/for_ceo/.gitkeep` | `CREATE_IF_MISSING` | Establish CEO pickup directory if absent |
| `runtime/orchestration/coo/closures.py` | `CREATE` | Add closure packet validation, loading, and writing |
| `runtime/tests/orchestration/coo/test_closures.py` | `CREATE` | Add closure packet tests |
| `runtime/orchestration/coo/backlog.py` | `MODIFY` | Add `decision_support_required` and preserve it everywhere |
| `runtime/tests/orchestration/coo/test_backlog.py` | `MODIFY` | Add tests for field round-trip and state transitions |
| `runtime/orchestration/coo/auto_dispatch.py` | `MODIFY` | Add `_council_cleared()` and wire it into full eligibility |
| `runtime/tests/orchestration/coo/test_auto_dispatch.py` | `MODIFY` | Add tests for the 7th predicate |
| `runtime/orchestration/coo/commands.py` | `MODIFY` | Add `cmd_coo_process_closures()` |
| `runtime/tests/orchestration/coo/test_commands.py` | `MODIFY` | Add tests for closure-processing command |
| `runtime/cli.py` | `MODIFY` | Register and dispatch `coo process-closures` |
| `artifacts/coo/brief.md` | `MODIFY` | Add closures and `for_ceo` orientation steps |
| `scripts/workflow/dispatch_opencode.sh` | `CREATE` | Add OpenCode dispatch wrapper with sprint-close emission |
| `scripts/workflow/dispatch_codex.sh` | `MODIFY` | Add sprint-close emission after existing receipt flow |
| `config/tasks/backlog.yaml` | `MODIFY` | Add `T-027..T-030` |
| `docs/11_admin/BACKLOG.md` | `MODIFY` | Add human-readable references to `T-027..T-030` |
| `docs/INDEX.md` | `MODIFY` | Update timestamp because docs are touched |
| `docs/LifeOS_Strategic_Corpus.md` | `MODIFY` | Regenerate because docs are touched |
| `artifacts/review_packets/Review_Packet_COO_Coordination_Loop_v1.0.md` | `CREATE` | Required review packet |
| `CLAUDE.md` | `MODIFY` | Council-gated handoff requirement for sprint-close packets |
| `config/governance/delegation_envelope.yaml` | `MODIFY` | Council-gated `CT-6` trigger |
