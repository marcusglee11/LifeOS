# Plan: Git Workflow Protocol v1.1 Implementation

**Version:** v1.1
**Status:** PROPOSED
**Author:** Antigravity

## Goal

Upgrade Git workflow to v1.1, making it fail-closed, evidence-backed, and enforcing "anti-deletion" discipline.

## User Review Required
>
> [!IMPORTANT]
> This plan implements strict blocking gates for:
>
> - Direct commits/pushes to `main`
> - Merges without proven CI checks (via `gh` CLI)
> - Destructive operations without dry-run evidence
> - Branch deletion without archive receipts

## Proposed Changes

### 1. Protocol Documentation

- **[MODIFY]** `docs/02_protocols/Git_Workflow_Protocol_v1.0.md`
  - Update to v1.1 content provided in instruction.
  - Define new invariants (CI proof, Archive Receipt, Safe Clean).

### 2. Enforcement Tooling (`scripts/git_workflow.py`)

- **[MODIFY]** `scripts/git_workflow.py`
  - **Rewrite** to implement v1.1 commands:
    - `hooks install`: Configure `core.hooksPath`.
    - `merge`: Check CI status via `gh run list`, generate receipt.
    - `branch archive`: Archive receipt generation.
    - `branch create`: Naming validation, `active_branches.json` tracking.
    - `safety preflight`: Dry-run for destructive ops.
    - `emergency`: Log overrides to JSONL.

### 3. Git Hooks

- **[NEW]** `scripts/hooks/pre-commit`
- **[NEW]** `scripts/hooks/pre-push`
  - Block operations on `main`.

### 4. Safety Gate Integration

- **[MODIFY]** `scripts/repo_safety_gate.py`
  - Integrate with `git_workflow.py`.
  - Add "destructive" mode support.

## Verification Plan

### Automated Tests

- **[NEW]** `runtime/tests/test_git_workflow.py`
  - Test `validate_branch_name`.
  - Test `merge` logic (receipt generation).
  - Test `archive` logic.
  - Test `safety preflight`.
  - Test `emergency` override logging.

### Manual Verification

1. **Hook Installation:** Run `python scripts/git_workflow.py hooks install`.
2. **Commit Block:** Try to commit on `main`.
3. **Merge Block:** Try to merge without CI proof.
4. **Archive:** Archive a test branch.
5. **Emergency:** Use emergency override.
