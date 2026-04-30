# Workstream Context v1

Status: AA-approved substrate for LifeOS issue #102.

## Canonical state

`artifacts/workstreams/<slug>/state.yaml` is the canonical continuation state for a
LifeOS workstream. The `<slug>` key must exist in `artifacts/workstreams.yaml`.
Local filesystem paths inside state are hints only. They are never authority for
completion, merge, closure, or issue state.

There is no `artifacts/workstreams/current.yaml` alias in v1. Any future alias
must be pointer-only and explicitly non-canonical.

## Legacy active-work file

`.context/active_work.yaml` is legacy/session-local/advisory. It may be generated
from canonical workstream state for old tools, but it must never compete with or
override `artifacts/workstreams/<slug>/state.yaml`. If both files exist and they
conflict, canonical workstream state wins. Tests cover this precedence so the old
file cannot quietly become a second source of truth.

## Required anti-staleness fields

A v1 state file must include:

- `lifecycle_state`
- `status`
- `repo_full_name`
- `default_branch`
- `current_head_sha` or `observed_main_sha` once implementation starts
- `last_verified_at`
- `completion_truth.required`
- `completion_truth.refs`

`state.yaml` alone never proves done, merged, or closed. Completion truth lives in
external readback: GitHub PR state, CI/check results, main-branch readback, issue
receipt, and commit refs.

## Tool preflight entries

Each tool preflight entry must include:

- `status`
- `checked_at`
- `evidence_ref`
- `required`
- `scope`
- `phase`
- `failure_reason`
- `stale_after` or `valid_until`

Required `PASS` without an `evidence_ref` is invalid. Required `UNKNOWN` is valid
only before the relevant phase/check is required. Required `FAIL`, `SKIPPED`, or
stale entries block resume when the workstream has reached the relevant phase.
Durations such as `24h` are parsed deterministically by
`scripts/workflow/workstream_context.py`.

## Reviewer results

`schemas/workstreams/reviewer_result.schema.json` defines reviewer verdicts as
only `PASS`, `REVISE`, or `BLOCK`.

## Resume prompt

`python3 scripts/workflow/workstream_context.py emit-resume-prompt --state <path>`
emits a prompt containing:

- active issue
- current phase
- next action
- blockers
- typed `do_not_start` entries
- evidence refs and summaries only
- completion truth requirements

It must not inline full evidence packet bodies.

## Quality routing

The changed-scope quality gate must route workstream context validation for:

- `artifacts/workstreams/**`
- `schemas/workstreams/**`
- `docs/02_protocols/workstream_context_v1.md`
- `scripts/workflow/workstream_context.py`
- related tests and fixtures

This explicitly prevents the quality gate from skipping workstream validation just
because a relevant file lives under `artifacts/`.
