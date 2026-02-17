"""Tests for worktree dispatch — isolated execution context lifecycle."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from runtime.orchestration.loop.worktree_dispatch import (
    WorktreeError,
    WorktreeHandle,
    create_worktree,
    remove_worktree,
    validate_worktree_clean,
    validate_worktree_preconditions,
    worktree_scope,
    _worktree_dir_name,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_repo(path: Path) -> Path:
    """Create a minimal git repo at *path* and return it."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", str(path)], capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        capture_output=True, check=True, cwd=path,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        capture_output=True, check=True, cwd=path,
    )
    # Need at least one commit for worktrees to work
    (path / "README.md").write_text("init")
    subprocess.run(["git", "add", "."], capture_output=True, check=True, cwd=path)
    subprocess.run(
        ["git", "commit", "-m", "init", "--no-gpg-sign"],
        capture_output=True, check=True, cwd=path,
    )
    return path


# ---------------------------------------------------------------------------
# Precondition tests
# ---------------------------------------------------------------------------


class TestValidateWorktreePreconditions:
    def test_passes_on_valid_repo(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path / "repo")
        validate_worktree_preconditions(repo)  # should not raise

    def test_fails_on_non_repo(self, tmp_path: Path) -> None:
        with pytest.raises(WorktreeError) as exc:
            validate_worktree_preconditions(tmp_path)
        assert exc.value.code == "NOT_A_GIT_REPO"


# ---------------------------------------------------------------------------
# Create / remove tests
# ---------------------------------------------------------------------------


class TestCreateWorktree:
    def test_creates_sibling_directory(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path / "repo")
        handle = create_worktree(repo, "test-run-1")
        try:
            assert handle.worktree_path.exists()
            assert handle.worktree_path.parent == repo.parent
            assert handle.branch_name == "spine/test-run-1"
            # Verify it's a real git worktree
            result = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                capture_output=True, text=True, cwd=handle.worktree_path,
            )
            assert result.returncode == 0
        finally:
            remove_worktree(repo, handle)

    def test_fails_if_worktree_dir_exists(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path / "repo")
        wt_dir = repo.parent / _worktree_dir_name("dup-run")
        wt_dir.mkdir()
        with pytest.raises(WorktreeError) as exc:
            create_worktree(repo, "dup-run")
        assert exc.value.code == "WORKTREE_EXISTS"

    def test_fails_on_non_repo(self, tmp_path: Path) -> None:
        with pytest.raises(WorktreeError) as exc:
            create_worktree(tmp_path, "bad-run")
        assert exc.value.code == "NOT_A_GIT_REPO"


# ---------------------------------------------------------------------------
# Clean check tests
# ---------------------------------------------------------------------------


class TestValidateWorktreeClean:
    def test_passes_on_clean_worktree(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path / "repo")
        handle = create_worktree(repo, "clean-run")
        try:
            validate_worktree_clean(handle)  # should not raise
        finally:
            remove_worktree(repo, handle)

    def test_fails_on_dirty_worktree(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path / "repo")
        handle = create_worktree(repo, "dirty-run")
        try:
            (handle.worktree_path / "dirty.txt").write_text("uncommitted")
            with pytest.raises(WorktreeError) as exc:
                validate_worktree_clean(handle)
            assert exc.value.code == "WORKTREE_DIRTY"
        finally:
            remove_worktree(repo, handle)


# ---------------------------------------------------------------------------
# Context manager tests
# ---------------------------------------------------------------------------


class TestWorktreeScope:
    def test_creates_and_cleans_up(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path / "repo")
        wt_path = None
        with worktree_scope(repo, "scope-run") as handle:
            wt_path = handle.worktree_path
            assert wt_path.exists()
            assert handle.run_id == "scope-run"
        # After exit, worktree directory should be removed
        assert not wt_path.exists()

    def test_cleans_up_on_exception(self, tmp_path: Path) -> None:
        repo = _init_repo(tmp_path / "repo")
        wt_path = None
        with pytest.raises(ValueError):
            with worktree_scope(repo, "exc-run") as handle:
                wt_path = handle.worktree_path
                raise ValueError("simulated failure")
        assert not wt_path.exists()

    def test_worktree_is_independent(self, tmp_path: Path) -> None:
        """Files created in worktree don't appear in main repo."""
        repo = _init_repo(tmp_path / "repo")
        with worktree_scope(repo, "iso-run") as handle:
            (handle.worktree_path / "isolated.txt").write_text("only here")
            subprocess.run(
                ["git", "add", "."], capture_output=True, cwd=handle.worktree_path,
            )
            subprocess.run(
                ["git", "commit", "-m", "isolated", "--no-gpg-sign"],
                capture_output=True, cwd=handle.worktree_path,
            )
            assert not (repo / "isolated.txt").exists()


# ---------------------------------------------------------------------------
# Naming convention test
# ---------------------------------------------------------------------------


class TestWorktreeDirName:
    def test_deterministic(self) -> None:
        assert _worktree_dir_name("run_123") == "LifeOS__wt_spine_run_123"
