"""Worktree dispatch — isolated execution context for LoopSpine runs.

Provides a context manager that creates, uses, and cleans up a git worktree
so that OpenClaw-originated jobs execute in an isolated working copy.

All failures raise WorktreeError with a machine-readable code (fail-closed).
"""

from __future__ import annotations

import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


class WorktreeError(RuntimeError):
    """Fail-closed worktree lifecycle error."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class WorktreeHandle:
    """Opaque handle to an active worktree."""

    worktree_path: Path
    branch_name: str
    run_id: str


def _run_git(args: list[str], cwd: Path, *, timeout: int = 30) -> subprocess.CompletedProcess[str]:
    """Run a git command, raising WorktreeError on failure."""
    try:
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired as exc:
        raise WorktreeError("GIT_TIMEOUT", f"git {args[0]} timed out after {timeout}s") from exc
    except FileNotFoundError as exc:
        raise WorktreeError("GIT_NOT_FOUND", "git executable not found") from exc


def validate_worktree_preconditions(repo_root: Path) -> None:
    """Fail-closed: repo must be a valid git repo."""
    result = _run_git(["rev-parse", "--is-inside-work-tree"], cwd=repo_root)
    if result.returncode != 0:
        raise WorktreeError(
            "NOT_A_GIT_REPO",
            f"Not a git repository: {repo_root}",
        )


def _worktree_dir_name(run_id: str) -> str:
    """Deterministic worktree directory name."""
    return f"LifeOS__wt_spine_{run_id}"


def create_worktree(repo_root: Path, run_id: str) -> WorktreeHandle:
    """Create an isolated worktree as a sibling of repo_root."""
    validate_worktree_preconditions(repo_root)

    branch_name = f"spine/{run_id}"
    wt_dir = repo_root.parent / _worktree_dir_name(run_id)

    if wt_dir.exists():
        raise WorktreeError(
            "WORKTREE_EXISTS",
            f"Worktree directory already exists: {wt_dir}",
        )

    result = _run_git(
        ["worktree", "add", "-b", branch_name, str(wt_dir)],
        cwd=repo_root,
    )
    if result.returncode != 0:
        raise WorktreeError(
            "WORKTREE_CREATE_FAILED",
            f"git worktree add failed: {result.stderr.strip()}",
        )

    return WorktreeHandle(worktree_path=wt_dir, branch_name=branch_name, run_id=run_id)


def validate_worktree_clean(handle: WorktreeHandle) -> None:
    """Post-run assertion: worktree must have no uncommitted changes."""
    result = _run_git(["status", "--porcelain"], cwd=handle.worktree_path)
    if result.returncode != 0:
        raise WorktreeError(
            "WORKTREE_STATUS_FAILED",
            f"git status failed in worktree: {result.stderr.strip()}",
        )
    if result.stdout.strip():
        raise WorktreeError(
            "WORKTREE_DIRTY",
            f"Worktree has uncommitted changes:\n{result.stdout.strip()}",
        )


def remove_worktree(repo_root: Path, handle: WorktreeHandle) -> None:
    """Best-effort cleanup: force remove worktree + delete branch."""
    # Remove the worktree registration
    _run_git(
        ["worktree", "remove", "--force", str(handle.worktree_path)],
        cwd=repo_root,
    )
    # Delete the branch (best-effort)
    _run_git(
        ["branch", "-D", handle.branch_name],
        cwd=repo_root,
    )


@contextmanager
def worktree_scope(repo_root: Path, run_id: str) -> Iterator[WorktreeHandle]:
    """Context manager: create worktree, yield handle, clean up.

    Raises WorktreeError on precondition or creation failure.
    Cleanup runs in finally block (best-effort).
    """
    handle = create_worktree(repo_root, run_id)
    try:
        yield handle
    finally:
        remove_worktree(repo_root, handle)
