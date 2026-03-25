# COO Workspace Ops V1 Review Handoff

Date: 2026-03-25
Branch: `build/coo-workspace-ops-exec`
Repo root: `/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/coo-workspace-ops-exec`
Base head: `5c573885b1567db128419ec2f5e65a1bec5e596f`
Subject under review: uncommitted worktree changes implementing `artifacts/plans/2026-03-25-coo-workspace-ops-v1.md`

## Status

This build is implemented locally in the worktree and not committed.

Completed:

- added a new COO ops lane under `runtime/orchestration/ops/`
- added `operation_proposal.v1` parsing and direct/chat routing for COO
- extended `lifeos coo approve` to accept `OP-...` IDs
- added CLI wiring for `lifeos coo chat` and `lifeos coo prompt-status`
- added canonical prompt source at `config/coo/prompt_canonical.md`
- added prompt sync script at `scripts/workflow/sync_coo_prompt.py`
- added targeted tests for parser, commands, and ops execution

Not completed:

- no commit / close-build flow was done
- no live `sync_coo_prompt.py` run was executed against `~/.openclaw/workspace/AGENTS.md`
- no live OpenClaw invocation was executed for `coo direct` or `coo chat`
- no full `runtime/tests` completion was observed in-session

## What Changed

Primary implementation files:

- `runtime/orchestration/ops/registry.py`
- `runtime/orchestration/ops/queue.py`
- `runtime/orchestration/ops/executor.py`
- `runtime/orchestration/coo/parser.py`
- `runtime/orchestration/coo/invoke.py`
- `runtime/orchestration/coo/context.py`
- `runtime/orchestration/coo/commands.py`
- `runtime/cli.py`
- `config/coo/prompt_canonical.md`
- `scripts/workflow/sync_coo_prompt.py`

Primary test files:

- `runtime/tests/orchestration/coo/test_parser.py`
- `runtime/tests/orchestration/coo/test_commands.py`
- `runtime/tests/orchestration/ops/test_ops_lane.py`

Working diff summary observed during handoff creation:

- `runtime/cli.py` — CLI surface for `coo chat`, `coo prompt-status`, `coo approve OP-...`, `coo direct --execute`
- `runtime/orchestration/coo/commands.py` — operation proposal classification, queue/execute routing, prompt drift status, chat JSON envelope
- `runtime/orchestration/coo/context.py` — direct-mode context example for `operation_proposal.v1`
- `runtime/orchestration/coo/invoke.py` — direct/chat prompt contract and indentation normalization for `proposal_id`
- `runtime/orchestration/coo/parser.py` — `parse_operation_proposal()`
- `runtime/orchestration/ops/*.py` — allowlist, path normalization, persistence, execution
- `runtime/tests/orchestration/coo/test_commands.py` — command coverage for direct/chat/approve/prompt-status
- `runtime/tests/orchestration/coo/test_parser.py` — parser coverage for operation proposals
- `runtime/tests/orchestration/ops/test_ops_lane.py` — path normalization and executor behavior

## Review Focus

- verify `operation_proposal.v1` validation is fail-closed and does not allow unknown actions or path escapes
- verify `/workspace/...` alias handling resolves only within the OpenClaw workspace root
- verify `workspace.file.edit` exact-match behavior rejects zero-match and multi-match cases
- verify `cmd_coo_direct()` preserves the existing escalation path while handling operation proposals first
- verify `cmd_coo_chat()` message stripping is safe when inline YAML appears with conversational text
- verify `cmd_coo_approve()` prefix routing for `T-...` vs `OP-...` does not regress backlog approvals
- verify `prompt-status` and `sync_coo_prompt.py` use the intended canonical/live paths and receipt location
- verify the implementation does not accidentally rely on repo-root workspace resolution where the plan requires the COO/OpenClaw workspace root

## Current Dirty Files

- `runtime/cli.py`
- `runtime/orchestration/coo/commands.py`
- `runtime/orchestration/coo/context.py`
- `runtime/orchestration/coo/invoke.py`
- `runtime/orchestration/coo/parser.py`
- `runtime/tests/orchestration/coo/test_commands.py`
- `runtime/tests/orchestration/coo/test_parser.py`
- `config/coo/prompt_canonical.md`
- `runtime/orchestration/ops/__init__.py`
- `runtime/orchestration/ops/executor.py`
- `runtime/orchestration/ops/queue.py`
- `runtime/orchestration/ops/registry.py`
- `runtime/tests/orchestration/ops/test_ops_lane.py`
- `scripts/workflow/sync_coo_prompt.py`

## Verification Run

Passed:

- `python3 -m pytest runtime/tests/orchestration/coo/test_parser.py runtime/tests/orchestration/coo/test_commands.py runtime/tests/orchestration/ops/test_ops_lane.py -q`
  - result: `54 passed`
- `python3 -m pytest runtime/tests/test_cli_doc_drift.py -q`
  - result: `2 passed`
- `python3 -m pytest runtime/tests/orchestration/coo/test_invoke_receipts.py -q`
  - result: `7 passed`

Did not complete cleanly within the session:

- `python3 -m pytest runtime/tests -q`
  - advanced cleanly through COO, council, dispatch, loop, and into missions
  - last observed progress reached `25%`
  - no failing test output was observed before the run stopped producing visible output
  - do not claim a full-suite pass from this session

## Suggested Immediate Commands

```bash
git status --short --untracked-files=all
git diff --stat
python3 -m pytest runtime/tests/orchestration/coo/test_parser.py runtime/tests/orchestration/coo/test_commands.py runtime/tests/orchestration/ops/test_ops_lane.py -q
python3 -m pytest runtime/tests/test_cli_doc_drift.py -q
python3 -m pytest runtime/tests/orchestration/coo/test_invoke_receipts.py -q
python3 -m pytest runtime/tests -q
```

If validating prompt drift/sync behavior in a live-safe environment:

```bash
python3 scripts/workflow/sync_coo_prompt.py
python3 -m runtime.cli coo prompt-status --json
```

If smoke-checking the new CLI surfaces with mocks or a safe live environment:

```bash
python3 -m runtime.cli coo direct "write a note in /workspace/notes/example.md"
python3 -m runtime.cli coo chat "write a note in /workspace/notes/example.md"
python3 -m runtime.cli coo approve OP-<proposal-id>
```

## Notes

- the initial `start_build.py` worktree for `build/coo-workspace-ops` was left in a broken `locked initializing` state, so the implementation work proceeded in `build/coo-workspace-ops-exec`
- no governance-protected paths were touched in this session
- the live OpenClaw workspace was intentionally not mutated during this build session
- review should assume the branch is still dirty and that the full runtime suite needs a definitive rerun before merge or close-build
