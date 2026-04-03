from __future__ import annotations

import os
import subprocess
from pathlib import Path

from scripts.workflow import git_lock_health


def test_ensure_git_lock_health_removes_orphaned_primary_index_lock(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    git_dir = repo / ".git"
    git_dir.mkdir(parents=True)
    lock_path = git_dir / "index.lock"
    lock_path.write_text("", encoding="utf-8")

    def fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd[:4] == ["git", "-C", str(repo), "rev-parse"]:
            if cmd[-1] == "--git-dir":
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=".git\n", stderr="")
            if cmd[-1] == "--git-common-dir":
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=".git\n", stderr="")
        if cmd[:3] == ["ps", "-eo", "pid=,args="]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(git_lock_health.subprocess, "run", fake_run)
    result = git_lock_health.ensure_git_lock_health(repo, auto_cleanup=True)

    assert result.ok is True
    assert result.removed_locks == [str(lock_path)]
    assert not lock_path.exists()


def test_ensure_git_lock_health_resolves_linked_worktree_common_dir(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    common_git = repo / ".git"
    linked_git = common_git / "worktrees" / "topic"
    linked_git.mkdir(parents=True)
    refs_dir = common_git / "refs" / "heads"
    refs_dir.mkdir(parents=True)
    lock_path = refs_dir / "topic.lock"
    lock_path.write_text("", encoding="utf-8")

    def fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd[:4] == ["git", "-C", str(repo), "rev-parse"]:
            if cmd[-1] == "--git-dir":
                return subprocess.CompletedProcess(
                    args=cmd,
                    returncode=0,
                    stdout=".git/worktrees/topic\n",
                    stderr="",
                )
            if cmd[-1] == "--git-common-dir":
                return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=".git\n", stderr="")
        if cmd[:3] == ["ps", "-eo", "pid=,args="]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(git_lock_health.subprocess, "run", fake_run)
    result = git_lock_health.ensure_git_lock_health(repo, auto_cleanup=True)

    assert result.ok is True
    assert result.removed_locks == [str(lock_path)]
    assert not lock_path.exists()


def test_inspect_git_locks_blocks_when_active_process_detected(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    git_dir = repo / ".git"
    git_dir.mkdir(parents=True)
    lock_path = git_dir / "index.lock"
    lock_path.write_text("", encoding="utf-8")

    active_pid = os.getpid() + 1000

    def fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd[:4] == ["git", "-C", str(repo), "rev-parse"]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=".git\n", stderr="")
        if cmd[:3] == ["ps", "-eo", "pid=,args="]:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=f"{active_pid} git -C {repo} status\n",
                stderr="",
            )
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(git_lock_health.subprocess, "run", fake_run)
    result = git_lock_health.inspect_git_locks(repo)

    assert result.ok is False
    assert result.blocking_locks == [str(lock_path)]
    assert any(f"pid={active_pid}" in note for note in result.notes)


def test_inspect_git_locks_fails_closed_when_process_detection_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    git_dir = repo / ".git"
    git_dir.mkdir(parents=True)
    lock_path = git_dir / "HEAD.lock"
    lock_path.write_text("", encoding="utf-8")

    def fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd[:4] == ["git", "-C", str(repo), "rev-parse"]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=".git\n", stderr="")
        if cmd[:3] == ["ps", "-eo", "pid=,args="]:
            return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="ps failed")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(git_lock_health.subprocess, "run", fake_run)
    result = git_lock_health.inspect_git_locks(repo)

    assert result.ok is False
    assert result.blocking_locks == [str(lock_path)]
    assert result.notes == ["process detection unavailable: ps failed"]


def test_ensure_git_lock_health_treats_already_deleted_lock_as_removed(
    tmp_path: Path, monkeypatch
) -> None:
    """FileNotFoundError during unlink should count as removed, not as failure."""
    repo = tmp_path / "repo"
    git_dir = repo / ".git"
    git_dir.mkdir(parents=True)
    lock_path = git_dir / "index.lock"
    lock_path.write_text("", encoding="utf-8")

    original_unlink = Path.unlink

    def flaky_unlink(self, missing_ok=False):
        # Simulate the lock disappearing between scan and unlink
        raise FileNotFoundError(f"no such file: {self}")

    def fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd[:4] == ["git", "-C", str(repo), "rev-parse"]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=".git\n", stderr="")
        if cmd[:3] == ["ps", "-eo", "pid=,args="]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(git_lock_health.subprocess, "run", fake_run)
    monkeypatch.setattr(Path, "unlink", flaky_unlink)
    result = git_lock_health.ensure_git_lock_health(repo, auto_cleanup=True)

    assert result.ok is True
    assert result.removed_locks == [str(lock_path)]


def test_ensure_git_lock_health_aggregates_multiple_removal_failures(
    tmp_path: Path, monkeypatch
) -> None:
    """All lock removals are attempted; failures are aggregated, not short-circuited."""
    repo = tmp_path / "repo"
    git_dir = repo / ".git"
    git_dir.mkdir(parents=True)
    lock1 = git_dir / "index.lock"
    lock2 = git_dir / "HEAD.lock"
    lock1.write_text("", encoding="utf-8")
    lock2.write_text("", encoding="utf-8")

    def fail_unlink(self, missing_ok=False):
        raise PermissionError(f"permission denied: {self}")

    def fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd[:4] == ["git", "-C", str(repo), "rev-parse"]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=".git\n", stderr="")
        if cmd[:3] == ["ps", "-eo", "pid=,args="]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(git_lock_health.subprocess, "run", fake_run)
    monkeypatch.setattr(Path, "unlink", fail_unlink)
    result = git_lock_health.ensure_git_lock_health(repo, auto_cleanup=True)

    assert result.ok is False
    assert len(result.blocking_locks) == 2
    assert result.removed_locks == []
    # Two failure notes (one per lock) plus any notes carried from inspect_git_locks
    assert sum(1 for n in result.notes if "failed to remove" in n) == 2


def test_inspect_git_locks_ignores_non_allowlisted_locks(
    tmp_path: Path, monkeypatch
) -> None:
    repo = tmp_path / "repo"
    git_dir = repo / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "random.lock").write_text("", encoding="utf-8")

    def fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd[:4] == ["git", "-C", str(repo), "rev-parse"]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=".git\n", stderr="")
        if cmd[:3] == ["ps", "-eo", "pid=,args="]:
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(git_lock_health.subprocess, "run", fake_run)
    result = git_lock_health.inspect_git_locks(repo)

    assert result.ok is True
    assert result.blocking_locks == []
    assert result.removed_locks == []
