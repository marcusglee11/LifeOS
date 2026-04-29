# COO to EA Dispatch Pipeline Protocol v0.1

<!-- markdownlint-disable MD013 MD040 MD060 -->

**Status:** Design packet, not runtime-active
**Version:** 0.1
**Issue:** #62
**Last updated:** 2026-04-29
**Authority:** LifeOS Target Architecture v2.3c; Work Management Framework v0.1; Git Workflow Protocol v1.1; active delegation envelope
**Next executable slice:** #79

---

## 1. Purpose

This packet defines the automated COO to EA dispatch pipeline for repository and build work.
It is a design/specification deliverable only. It does not implement dispatcher runtime code.

The pipeline moves LifeOS from manual EA CLI invocation toward governed automation where:

- COO selects, orchestrates, verifies, and reconciles.
- Codex EA executes repository/build work in isolated worktrees by default.
- GitHub issue/PR/CI state is the v0 control surface and completion truth.
- Wrapper process success is transport-only. Actual success requires a validated
  `ea_receipt.v0` plus GitHub, PR, and CI evidence.

## 2. Non-goals

This packet does not:

- Implement #79, #76, #77, or #78.
- Add runtime scripts, validators, schemas, GitHub workflows, or dispatch wrappers.
- Ratify OpenClaw, Telegram, or local TUI output as completion truth.
- Replace the Work Management Framework queue model in this issue.
- Change protected governance or foundation documents.
- Authorize provider routing away from Codex for repo/build execution.

## 3. Design Packet

### 3.1 Control surfaces

| Surface | v0 role | Completion authority |
|---|---|---|
| GitHub issue | Canonical automated work-order object and state thread | Yes |
| GitHub issue labels/state block | Machine-readable lifecycle state and routing | Yes |
| GitHub PR | Code-review and diff evidence | Yes |
| GitHub CI checks | Latest-head execution proof | Yes |
| `ea_receipt.v0` | Structured EA execution receipt | Required, but not sufficient alone |
| Wrapper exit code | Transport health only | No |
| OpenClaw chat/output | COO substrate context and message transport | No |
| Telegram messages | Notification or operator convenience only | No |
| Local TUI/session transcript | Debug context only | No |
| `config/tasks/backlog.yaml` | Current WMF queue source before migration | Not completion truth for automated runs |

GitHub is the v0 control surface because it already binds issues, PRs, commits, review,
and CI into one auditable plane. Local files may stage or mirror facts, but automated
completion is not true until GitHub evidence passes verification.

### 3.2 Role boundary

| Actor | Responsibilities | Must not do |
|---|---|---|
| CEO/Marcus | Sets strategy, approves gated dispatches, approves provider rule changes | Supply internal paths or manually mutate automation truth as routine operation |
| COO | Selects work, checks eligibility, opens/updates GitHub work orders, dispatches, verifies receipts and GitHub evidence, escalates | Directly execute repo/build work, edit code as EA, treat wrapper success as task success |
| Codex EA | Executes repo/build work, edits files, runs tests, opens/updates PR, emits `ea_receipt.v0`, posts result payload | Mutate COO state block directly, self-approve completion, bypass CI evidence |
| GitHub/CI | Carries issue, PR, commit, workflow, and check evidence | Interpret task semantics alone |
| Reviewer | Reviews PR/diff/evidence when required | Replace COO verification or CEO approval gates |

Codex is the default and only repo/build execution lane unless Marcus explicitly changes
the rule. Provider changes are CEO-gated because they alter execution authority and
evidence semantics.

### 3.3 Dispatch flow

1. COO selects a candidate work item from GitHub issue state or WMF backlog mirror.
2. COO applies auto-dispatch eligibility rules or records CEO approval reference.
3. COO creates or updates a GitHub work-order issue with a validated dispatch request.
4. COO writes `attempt_id`, dispatch timestamp, expected executor `codex`, and timeout.
5. GitHub workflow or dispatch wrapper starts Codex EA in an isolated build worktree.
6. Codex EA performs repo/build work, runs verification, opens or updates a PR, and emits
   `ea_receipt.v0`.
7. Codex EA posts a structured result payload to the GitHub issue.
8. COO verifier validates result payload, receipt, PR evidence, and CI status on the PR
   latest head SHA.
9. COO updates GitHub state, mirrors any WMF/backlog state if still needed, and reports
   outcome to CEO.

No terminal success transition occurs at step 5 or because a wrapper returned exit code 0.

## 4. Minimal Payload Specs

### 4.1 `coo_ea_dispatch_request.v0`

The dispatch request is the minimum object the COO passes to GitHub/workflow/Codex EA.
It may live in the issue body, workflow inputs, or both. #79 should choose exact storage
after implementation discovery, but fields below are required for v0.

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | string | yes | Exactly `coo_ea_dispatch_request.v0` |
| `repo` | string | yes | `owner/name`, e.g. `marcusglee11/LifeOS` |
| `issue_number` | integer | yes | GitHub work-order issue |
| `issue_url` | string | yes | GitHub issue URL |
| `command_id` | string | yes | COO or system-generated command correlation ID |
| `attempt_id` | string | yes | COO-generated per dispatch attempt |
| `task_ref` | string | yes | WMF id, legacy task id, or issue id |
| `task_type` | string | yes | `build`, `fix`, `hotfix`, `spike`, `stewardship`, or later ratified enum |
| `executor` | string | yes | Must be `codex` for repo/build v0 unless Marcus approves change |
| `base_ref` | string | yes | Target base branch or SHA |
| `branch_name` | string | yes | Proposed work branch |
| `scope_paths` | list[string] | yes | Expected write/read surface |
| `acceptance_criteria` | list[string] | yes | Concrete closure checks |
| `verification_commands` | list[string] | yes | Minimum local commands EA must run when feasible |
| `required_evidence` | list[string] | yes | Must include `ea_receipt.v0`, PR URL, latest-head CI result |
| `approval_ref` | string or null | yes | CEO/Council/GitHub approval reference or null for auto-dispatch |
| `auto_dispatch_basis` | object or null | yes | Predicate evidence when no approval_ref exists |
| `timeout_seconds` | integer | yes | Worker timeout from dispatch start |
| `created_at` | string | yes | ISO-8601 UTC timestamp |

Minimal example:

```json
{
  "schema_version": "coo_ea_dispatch_request.v0",
  "repo": "marcusglee11/LifeOS",
  "issue_number": 79,
  "issue_url": "https://github.com/marcusglee11/LifeOS/issues/79",
  "command_id": "CMD-20260429-001",
  "attempt_id": "ATT-20260429-001",
  "task_ref": "WI-2026-079",
  "task_type": "build",
  "executor": "codex",
  "base_ref": "main",
  "branch_name": "build/github-codex-dispatch-79",
  "scope_paths": ["runtime/orchestration/", "runtime/tests/"],
  "acceptance_criteria": ["validated EA receipt", "PR opened", "CI success on PR latest head"],
  "verification_commands": ["pytest runtime/tests -q"],
  "required_evidence": ["ea_receipt.v0", "pull_request", "ci_latest_head"],
  "approval_ref": null,
  "auto_dispatch_basis": {
    "requires_approval": false,
    "risk": "low",
    "protected_paths": "excluded",
    "scope_overlap": "none",
    "decision_support_required": false
  },
  "timeout_seconds": 3600,
  "created_at": "2026-04-29T00:00:00Z"
}
```

### 4.2 `ea_receipt.v0`

`ea_receipt.v0` already has a repository validator in `runtime/receipts/ea_receipt.py`.
The receipt is JSON and requires:

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | string | yes | Exactly `ea_receipt.v0` |
| `status` | string | yes | `success` or `failure` |
| `commands_run` | list[string] | yes | Commands the EA invoked |
| `inner_exit_codes` | list[integer] | yes | Inner command exit codes, not wrapper transport code |
| `files_changed` | list[string] | yes | Repo paths changed |
| `tests_run` | list[string] | yes | Test or gate names/commands |
| `blockers` | list[string] | yes | Required non-empty when `status=failure` |

Receipt validation is necessary but insufficient. A valid success receipt can only become
task success after GitHub result payload, PR, and CI evidence also pass verification.

### 4.3 `coo_ea_result.v0`

The EA result is the GitHub issue comment payload that lets the COO correlate an EA run
to the current work-order attempt.

| Field | Type | Required | Notes |
|---|---|---|---|
| `schema_version` | string | yes | Exactly `coo_ea_result.v0` |
| `repo` | string | yes | Must match dispatch request |
| `issue_number` | integer | yes | Must match current work-order issue |
| `attempt_id` | string | yes | Must match current active attempt |
| `executor` | string | yes | Must be `codex` unless CEO-approved provider change exists |
| `status` | string | yes | `succeeded`, `failed`, `blocked`, or `needs_decision` |
| `summary` | string | yes | Human-readable result summary |
| `receipt` | object | yes | Embedded `ea_receipt.v0` or canonical JSON object copied from it |
| `pr_url` | string or null | yes | Required for `succeeded` repo/build work |
| `head_sha` | string or null | yes | Required when PR exists |
| `ci_url` | string or null | yes | Required for `succeeded` repo/build work |
| `ci_status` | string or null | yes | `success`, `failure`, `cancelled`, `skipped`, or null |
| `evidence_urls` | list[string] | yes | Issue, PR, workflow, log, or artifact URLs |
| `blockers` | list[string] | yes | Required non-empty unless `status=succeeded` |
| `created_at` | string | yes | ISO-8601 UTC timestamp |

Minimal example:

```json
{
  "schema_version": "coo_ea_result.v0",
  "repo": "marcusglee11/LifeOS",
  "issue_number": 79,
  "attempt_id": "ATT-20260429-001",
  "executor": "codex",
  "status": "succeeded",
  "summary": "Implemented first Codex dispatch slice and opened PR.",
  "receipt": {
    "schema_version": "ea_receipt.v0",
    "status": "success",
    "commands_run": ["pytest runtime/tests -q"],
    "inner_exit_codes": [0],
    "files_changed": ["runtime/orchestration/example.py"],
    "tests_run": ["pytest runtime/tests -q"],
    "blockers": []
  },
  "pr_url": "https://github.com/marcusglee11/LifeOS/pull/123",
  "head_sha": "0123456789abcdef0123456789abcdef01234567",
  "ci_url": "https://github.com/marcusglee11/LifeOS/actions/runs/123456789",
  "ci_status": "success",
  "evidence_urls": ["https://github.com/marcusglee11/LifeOS/pull/123"],
  "blockers": [],
  "created_at": "2026-04-29T00:00:00Z"
}
```

## 5. Verification Rules

### 5.1 Wrapper exit code is transport-only

Wrapper exit code 0 means only that the wrapper completed transport duties, such as
launching Codex, polling a process, or posting a comment. It does not mean the EA task
succeeded.

Wrapper exit code handling:

| Wrapper observation | Meaning | COO state effect |
|---|---|---|
| exit 0, no valid result | Transport succeeded; execution truth missing | Stay non-terminal until timeout, then `timed_out` |
| exit 0, valid failure result | Transport succeeded; EA reported failure | `failed` or `blocked` by result status |
| exit 0, valid success receipt but no PR/CI | Transport succeeded; evidence incomplete | `needs_decision` or `failed`, not `succeeded` |
| nonzero wrapper exit, no valid result | Transport failed | `failed` with transport blocker, or `timed_out` if no event observed |

### 5.2 Success predicate

A dispatch attempt can transition to `succeeded` only when all conditions pass:

1. Current GitHub issue state is `dispatched` or `running`.
2. Result payload schema is exactly `coo_ea_result.v0`.
3. `repo`, `issue_number`, `attempt_id`, and `executor` match the current dispatch.
4. Embedded `receipt` validates as `ea_receipt.v0`.
5. Receipt `status` is `success`.
6. Every `inner_exit_codes` value is 0.
7. `blockers` is empty in both result and receipt.
8. PR exists, targets the expected base, and points at `head_sha`.
9. Required CI checks are `success` on that PR latest head SHA.
10. Worktree/branch evidence does not show dirty worktree, orphaned changes, or partial commit state.
11. Acceptance criteria are satisfied by evidence, not by narrative claim.

If any condition fails, the attempt is not successful.

### 5.3 Fail-closed result handling

| Result condition | Required handling |
|---|---|
| Missing result before timeout | Keep current state; reconciliation moves to `timed_out` after deadline |
| Missing `ea_receipt.v0` | Reject success; transition to `needs_decision` or `failed` with missing-receipt blocker |
| Malformed receipt JSON | Reject result; transition to `needs_decision` with schema blocker |
| Malformed result payload | Reject result; transition to `needs_decision`; do not infer status |
| Ambiguous or conflicting result | Transition to `needs_decision`; COO asks CEO or dispatches explicit recovery after approval |
| Late result after timeout or terminal state | Classify as `late_result`; log and escalate; do not apply automatically |
| Unknown executor/provider | Reject result unless explicit Marcus approval exists for provider change |

## 6. State Machine

### 6.1 Canonical lifecycle

| State | Meaning | Entry evidence | Exit evidence |
|---|---|---|---|
| `backlog` | Work exists but is not ready | Issue or WMF item exists | Valid task template and scope |
| `ready` | Dispatchable after eligibility/approval check | Acceptance criteria and routing known | Dispatch request written |
| `awaiting_ceo_approval` | COO cannot dispatch without CEO | Gate reason recorded | CEO approval reference |
| `dispatched` | COO issued trigger and attempt started | Dispatch request, `attempt_id`, timestamp | Workflow ack or valid fast result |
| `running` | Codex EA is executing | GitHub workflow/run or worker ack | Result payload or timeout |
| `validating_result` | Transient verifier phase, not persisted as final issue state | Result payload observed | Verification decision |
| `succeeded` | EA completed and COO accepted result | Valid result, valid receipt, PR, latest-head CI success | Terminal |
| `failed` | EA or verification failed with no immediate external dependency | Valid failure receipt or verification failure | CEO-approved retry or redirect |
| `blocked` | External dependency blocks completion | Permission, missing credential, unavailable resource, or dependency | Dependency resolved and COO/CEO re-dispatches |
| `needs_decision` | Human judgment required | Malformed, ambiguous, partial, or high-risk state | CEO direction |
| `timed_out` | Deadline exceeded without valid result | Reconciliation detects timeout | CEO-approved retry |
| `superseded` | Redirect replaced this work order | New issue links parent | Terminal |

### 6.2 Transition rules

```text
backlog -> ready
ready -> dispatched
ready -> awaiting_ceo_approval
awaiting_ceo_approval -> ready
dispatched -> running
dispatched -> validating_result
running -> validating_result
validating_result -> succeeded
validating_result -> failed
validating_result -> blocked
validating_result -> needs_decision
running -> timed_out
dispatched -> timed_out
failed -> dispatched               # retry; CEO approval required in v0
timed_out -> dispatched            # retry; CEO approval required in v0
needs_decision -> ready
needs_decision -> blocked
failed -> superseded               # redirect; CEO approval required in v0
```

`validating_result` is an implementation phase. If #79 chooses not to persist it as a
GitHub state, verifier logs must still record equivalent evidence.

## 7. Failure-Mode Matrix

| Case | Detection | State result | Auto action | CEO gate/recovery | Required test |
|---|---|---|---|---|---|
| Success | Valid result, valid success receipt, PR exists, CI success on PR head | `succeeded` | Close/mark accepted | None if auto-eligible or already approved | `test_success_requires_receipt_pr_ci` |
| Inner failure | Receipt valid, `status=failure` or nonzero inner exit | `failed` | Record blocker, keep PR/issue open | Retry approval in v0 | `test_inner_failure_blocks_success` |
| Missing receipt | Result lacks receipt or receipt path/object absent | `needs_decision` or `failed` | Reject success | CEO chooses retry or manual recovery | `test_missing_receipt_fails_closed` |
| Malformed receipt | Receipt JSON invalid or fails `ea_receipt.v0` validation | `needs_decision` | Reject payload | CEO chooses retry or recovery | `test_malformed_receipt_fails_closed` |
| Worker hang/timeout | No valid result before `timeout_seconds` | `timed_out` | Stop waiting, mark timed out | CEO-approved retry only in v0 | `test_worker_timeout_moves_to_timed_out` |
| Permission denial | Result/receipt blocker mentions permission, token, branch protection, or GitHub 403 | `blocked` | Do not retry automatically | CEO fixes auth or grants permission | `test_permission_denial_blocks_retry` |
| CI failure | PR exists but required checks fail/cancel/skip or not latest head | `failed` | Reject success | Retry/fix dispatch approval in v0 | `test_ci_failure_rejects_success` |
| Dirty worktree | Receipt or wrapper evidence shows uncommitted changes after EA run | `failed` | Reject success | Recovery dispatch or manual cleanup | `test_dirty_worktree_rejects_success` |
| Partial commit state | Commit/branch advanced but no PR, no result, or failure after commit | `needs_decision` | Freeze automatic state mutation | CEO chooses salvage PR, retry, or revert path | `test_partial_commit_state_needs_decision` |
| Wrapper exit 0 only | Wrapper completed but no valid result/evidence | Non-terminal until timeout | Continue reconciliation | Timeout recovery gate applies | `test_wrapper_exit_zero_is_transport_only` |
| Ambiguous result | Conflicting status/receipt/CI/PR fields or unknown status | `needs_decision` | Reject inference | CEO decision required | `test_ambiguous_result_fails_closed` |
| Late result | Valid result arrives after terminal state or stale attempt | No transition; classify `late_result` | Log and escalate | CEO decides whether to apply manually | `test_late_result_not_applied` |

## 8. CEO Gates and Auto-Dispatch Eligibility

### 8.1 Auto-dispatch eligibility

COO may auto-dispatch repo/build work only when every predicate is true:

| Predicate | Required value |
|---|---|
| `requires_approval` | `false` |
| `risk` | `low` |
| `task_type` | Auto-eligible type under current runtime policy |
| Protected paths | No overlap with protected paths |
| Scope concurrency | No overlap with in-progress scope paths |
| `decision_support_required` | `false`, or latest matching council request is resolved and non-stale |
| Acceptance criteria | Present and testable |
| Executor | `codex` |
| Budget/external side effects | None |
| Intent clarity | No ambiguity requiring CEO judgment |

All predicate evidence must be recorded in the dispatch request or linked GitHub state.
If any predicate is missing, false, stale, malformed, or unknown, dispatch is not
auto-eligible.

### 8.2 CEO approval gates

CEO approval is required for:

- Any task with `requires_approval=true`.
- `risk` medium/high or unknown.
- Protected path or governance surface touch.
- Architecture, provider, identity, credential, budget, or external commitment changes.
- Provider routing away from Codex.
- Ambiguous scope, unclear acceptance criteria, or conflicting instructions.
- Retry after timeout in v0.
- Redirect to a materially different plan in v0.
- Partial commit/branch state recovery when automatic proof is incomplete.
- Permission or credential remediation requiring Marcus action.
- Any action outside the active delegation envelope.

## 9. Implementation Plan

Each work package should be reviewable as an independent PR. #62 covers WP0 only.

| Work package | Scope | Main outputs | Review notes |
|---|---|---|---|
| WP0: #62 design packet | This document, index link, corpus refresh | Canonical spec to unblock #79 | No runtime code |
| WP1: #79 first executable slice | GitHub issue to Codex EA to PR/result/receipt happy path plus fail-closed verifier | `coo_ea_dispatch_request.v0`/`coo_ea_result.v0` validator, Codex wrapper integration, focused tests | Must prove wrapper exit 0 is transport-only |
| WP2: GitHub state reconciler | Issue state transitions, timeout pass, late result handling | Reconciliation command/service, timeout tests | GitHub remains control surface |
| WP3: PR/CI evidence verifier | Latest-head PR and CI proof validation | GitHub API checks, branch/commit correlation | Reject stale CI and wrong-head checks |
| WP4: COO eligibility integration | Auto-dispatch predicate wiring and CEO approval gates | Dispatch readiness integration with delegation envelope/WMF | No provider fallback |
| WP5: Migration and mirrors | Backlog/WMF mirror update from GitHub truth | One-way mirror or reconciliation report | Avoid competing state authorities |
| WP6: Hardening | Permission denial, dirty worktree, partial commit recovery runbooks | Recovery flows and tests | CEO gates remain explicit |

## 10. First Production-Capable Slice Acceptance Criteria

Issue #79 is the next executable slice and must implement the smallest production-capable path.
It is not implemented by this packet.

Issue #79 acceptance criteria:

1. A low-risk approved or auto-eligible work-order issue can dispatch Codex EA through GitHub.
2. Dispatch request validates against `coo_ea_dispatch_request.v0`.
3. Codex is the repo/build executor by default and no fallback provider executes repo/build work.
4. Codex runs in isolated worktree/branch context.
5. Wrapper exit 0 is recorded only as transport success.
6. EA posts `coo_ea_result.v0` to the GitHub issue.
7. Result embeds a valid `ea_receipt.v0`.
8. Success requires receipt success, all inner exit codes 0, PR URL, PR head SHA, and CI success on latest PR head.
9. Missing, malformed, ambiguous, stale, wrong-attempt, or wrong-executor result fails closed.
10. Tests cover success, inner failure, missing receipt, malformed receipt, worker hang/timeout,
    permission denial, CI failure, dirty worktree, partial commit state, wrapper exit 0 only,
    ambiguous result, and late result.
11. GitHub issue/PR/CI evidence is the only completion truth. OpenClaw, Telegram, and local TUI
    output are not accepted as completion truth.
12. COO/EA boundary remains intact: COO orchestrates/verifies; Codex EA executes repo/build work.

## 11. Migration Path

| Phase | Operating mode | Completion truth | Exit criteria |
|---|---|---|---|
| M0: Manual baseline | Human runs Codex/EA CLI and manually summarizes | Human-reviewed PR/tests | Current manual path documented |
| M1: Structured manual receipt | Manual EA invocation must produce `ea_receipt.v0` and GitHub result comment | GitHub issue comment plus PR/CI | Missing receipt rejected even when CLI looked successful |
| M2: Transport wrapper | Wrapper starts Codex and posts result payload; COO verifies manually | GitHub result plus receipt plus PR/CI | Wrapper exit 0 no longer treated as task success |
| M3: Automated verifier | COO verifier validates result, receipt, PR, CI and transitions issue state | GitHub state mutation by COO verifier | Failure-mode test matrix passes |
| M4: Auto-dispatch eligibility | COO auto-dispatches only eligible low-risk work | GitHub issue/PR/CI | CEO gates enforced, Codex default locked |
| M5: Backlog mirror retirement | WMF/local backlog becomes derived for automated dispatch state | GitHub issue state | No competing completion state remains |

Rollback path at every phase: stop automated dispatch, keep GitHub issue/PR evidence,
return to manual Codex EA invocation, and require manual COO verification before state
closure.

## 12. #62 Acceptance Mapping

| Required deliverable | Location in this packet |
|---|---|
| Design packet for automated COO to EA dispatch pipeline | Sections 1-3 |
| Minimal spec for dispatch request and EA result/receipt payloads | Section 4 |
| State machine and failure-mode matrix | Sections 6-7 |
| Implementation plan split into PR-sized work packages | Section 9 |
| Acceptance criteria for first production-capable slice | Section 10 |
| Migration path from manual EA CLI invocation to governed automation | Section 11 |

## 13. References

- `docs/00_foundations/LifeOS Target Architecture v2.3c.md`
- `docs/02_protocols/Work_Management_Framework_v0.1.md`
- `docs/02_protocols/Git_Workflow_Protocol_v1.1.md`
- `docs/02_protocols/Agent_Control_Plane_Pin_v1.0.md`
- `runtime/receipts/ea_receipt.py`
- `runtime/tests/receipts/test_ea_receipt.py`
- `config/governance/delegation_envelope.yaml`
- `config/models.yaml`
