# Git Workflow Protocol v1.1 (Fail-Closed, Evidence-Backed)

**Status:** Active  
**Applies To:** All agent and human work that modifies repo state  
**Primary Tooling:** `scripts/git_workflow.py` + Git hooks + GitHub branch protection  
**Last Updated:** 2026-01-16

---

## 1. Purpose

This protocol makes Git operations **auditable, deterministic, and fail-closed** for an agentic codebase.  
It is not “guidance”; it defines **enforced invariants**.

---

## 2. Core Invariants (MUST HOLD)

1. **Branch-per-build:** Every mission/build occurs on its own branch.
2. **Main is sacred:** No direct commits to `main`. No direct pushes to `main`.
3. **Merge is fail-closed on CI proof:** A merge to `main` occurs only if required checks passed on the PR’s **latest HEAD SHA**.
4. **No orphan work:** A branch may be deleted only if:
   - it has been merged to `main`, OR
   - it has an explicit **Archive Receipt**.
5. **Destructive operations are gated:** Any operation that can delete files must pass a safety gate and emit evidence (dry-run + actual).

---

## 3. Enforcement Model (HOW THIS IS REAL)

Enforcement is implemented via:

- **Server-side:** GitHub branch protection on `main` (PR required; required checks; no force push).
- **Client-side:** Repo Git hooks (installed via tooling) block prohibited operations locally.
- **Safe path:** `scripts/git_workflow.py` provides the canonical interface for state-changing actions and emits receipts.

If any enforcement layer is missing or cannot be verified, the workflow is **BLOCKED** until fixed.

---

## 4. Naming Conventions (Validated by Tooling)

Branch names MUST match one of:

| Type | Pattern | Example |
|------|---------|---------|
| Feature/Mission | `build/<topic>` | `build/cso-constitution` |
| Bugfix | `fix/<issue>` | `fix/test-failures` |
| Hotfix | `hotfix/<issue>` | `hotfix/ci-regression` |
| Experiment | `spike/<topic>` | `spike/new-validator` |

Tooling MAY auto-suffix names for collision resistance, but prefixes must remain.

---

## 5. Workflow Stages (Canonical)

### Stage 1: Start Build (from latest main)

Command:

- `python scripts/git_workflow.py branch create <name>`

Effects:

- Creates branch from updated `main`
- Validates branch name
- Records branch entry in `artifacts/active_branches.json` (deterministic ordering)

### Stage 2: Work-in-Progress (feature branch only)

Rules:

- Commits are permitted only on non-main branches.
- Push feature branch for backup: `git push -u origin <branch>` (allowed)

### Stage 3: Review-Ready (local tests + PR)

Command:

- `python scripts/git_workflow.py review prepare`

Requirements (fail-closed):

- Runs required local tests (repo-defined)
- If tests fail: no PR creation; prints the failure locator
- If tests pass: create/update PR and record PR number in `artifacts/active_branches.json`

Outputs:

- Review-ready artifacts/logs as defined by repo (tooling must be deterministic)

### Stage 4: Approved → Merge (CI proof + receipt)

Command:

- `python scripts/git_workflow.py merge`

Hard requirements (fail-closed):

- Required CI checks passed
- Proof is tied to the PR’s latest HEAD SHA
- Merge is performed via squash merge (unless repo policy requires otherwise)

Outputs:

- Merge Receipt JSON written to `artifacts/git_workflow/merge_receipts/…`
- `artifacts/active_branches.json` updated with status=merged

### Stage 5: Archive (explicit non-merge closure)

Command:

- `python scripts/git_workflow.py branch archive <branch> --reason "<text>"`

Rules:

- Archive is the only alternative to merge for satisfying “no orphan work”.
- Archive writes an Archive Receipt and updates `artifacts/active_branches.json` with status=archived.
- After archive, deletion is permitted (but still logged).

Outputs:

- Archive Receipt JSON written to `artifacts/git_workflow/archive_receipts/…`

---

## 6. Prohibited Operations (Blocked by Hooks/Tooling)

These operations MUST be blocked unless executed under emergency override:

- Commit on `main`
- Push to `main`
- Delete a branch without merge OR archive receipt
- Run destructive cleans/resets without safety preflight evidence

If tooling cannot enforce a block, the system is considered **non-compliant**.

---

## 7. CI Proof Contract (Definition)

“CI passed” means:

- The repo-defined required checks are SUCCESS on GitHub
- The checks correspond to the PR’s latest HEAD SHA
- The merge tool records the proof method and captured outputs in the Merge Receipt

No proof → no merge.

---

## 8. Destructive Operations Safety (Anti-Deletion)

Any operation that can delete files must:

1. Run `safety preflight` in destructive mode
2. Capture dry-run listing (what would be deleted)
3. Execute the operation
4. Capture actual deletion listing (what was deleted)
5. Emit a Destructive Ops evidence JSON

If any step fails or cannot be proven: BLOCK.

---

## 9. Emergency Override (Accountable, Retrospective Approval)

Command:

- `python scripts/git_workflow.py emergency <operation> --reason "<text>"`

Rules:

- Emergency override is exceptional only.
- Every override must be logged (JSONL) with:
  - operation, reason, branch, head sha, timestamp, and tool version.
- Retrospective approval must be recorded via:
  - `python scripts/git_workflow.py emergency approve <override_id> --approver CEO --note "<text>"`

Unapproved overrides are tracked as debt and must be visible in diagnostics.

---

## 10. Recovery Procedures (Fail-Closed)

Tooling must provide recovery commands that do not guess:

- `python scripts/git_workflow.py recover orphan`
- `python scripts/git_workflow.py recover divergence`
- `python scripts/git_workflow.py recover files`

Each recovery command must:

- print exact diagnosis
- propose deterministic steps
- never delete data silently
- emit an evidence record if it changes state

---

## 11. Integration Points

- GitHub Branch Protection: `main` requires PR + required checks
- Repo Safety Gate: enforced before destructive operations and (optionally) before checkout
- CI Pipeline: runs on all PRs; required checks are defined in repo policy

---

## 12. Compliance

A repo is compliant with this protocol if:

- hooks are installed and active, OR equivalent enforcement is present
- merges produce receipts with CI proof
- archives produce receipts
- destructive ops are gated and evidenced
- `artifacts/active_branches.json` is accurate and deterministically ordered

---

## 13. Operational Notes (Batch 2 Burn-In — 2026-02-27)

The following operational findings were documented during the Batch 2 burn-in
(post top-3 Batch-1 fixes). They inform future sprint and burn-in procedures.

### 13.1 Attempt Ledger Must Be Committed Between Spine Runs

The ledger file at `artifacts/loop_state/attempt_ledger.jsonl` is written by
every spine run. The next run's `verify_repo_clean()` check fails if the ledger
is uncommitted. The F3 fix (applied in `build/batch2-prep`) auto-commits the
ledger between sequential runs. Procedure consequence: always verify the ledger
is committed before starting a new run; the auto-commit gate now enforces this.

### 13.2 Steward Diff Budget Is Configurable via `constraints.max_diff_lines`

The steward phase enforces a maximum diff size before accepting a commit. The
default was raised from 300 to 500 lines as F5 fix. Task curators can further
adjust via the `constraints.max_diff_lines` field in the task spec JSON.
Use case: large refactors or test-only expansions that legitimately exceed the
default. Do not raise above 1000 without Council approval.

### 13.3 Doc Tasks Must Specify "APPEND-ONLY" Constraint Explicitly

Builder LLMs tend to rewrite entire files when given doc-update tasks, even
when intent is to add a small section (Batch 1 Finding 4). Task specs for
protocol doc amendments must include the explicit constraint:
`"APPEND-ONLY — do not rewrite or reorder existing content"`. This was
validated in Batch 2 B2-T03; the manual implementation here demonstrates the
correct append-only pattern for future builder reference.

---

## 14. Worktree-First Build Protocol

### 14.1 Default Rule

All new builds default to isolated git worktrees. Applies to `build/`, `fix/`,
`hotfix/`, and `spike/` branches.

### 14.2 Start Command

Use:

- `python3 scripts/workflow/start_build.py <topic> [--kind build|fix|hotfix|spike]`
- `cd .worktrees/<short-name>`

The command resolves the primary repo automatically (safe to invoke from linked
worktrees), derives branch names from topic+kind, and creates linked worktrees
deterministically (`[a-z0-9-]`, truncated to 30 chars).

### 14.3 Close Command

Run `/close-build` (or `python3 scripts/workflow/close_build.py`) from the
linked worktree. On successful merge, cleanup removes the linked worktree and
deletes the source branch.

### 14.4 Exception Path

Primary-tree builds are hard-blocked for `build|fix|hotfix|spike` close/merge
operations unless explicit break-glass is used. Normal autonomous flows must
auto-remediate by retrying in an isolated worktree.

Exception path (human-only) is allowed only when:

- a single active build is confirmed, and
- `git status --porcelain=v1` is empty.

When using this exception, document the rationale in the first commit message.

### 14.5 Recovery Path (Wrong-Tree WIP)

If scoped work was started in the primary tree by mistake, do not hand-migrate
with manual stash/checkout/worktree commands. Use:

- `python3 scripts/workflow/start_build.py --recover-primary`

Recovery stashes tracked+untracked changes, switches primary back to
`main/master`, ensures a linked worktree exists for the current scoped branch,
and reapplies the stash in that linked worktree.
