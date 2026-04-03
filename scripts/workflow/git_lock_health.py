#!/usr/bin/env python3
"""Best-effort Git lock inspection for workflow entry points."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GitLockHealth:
    ok: bool
    removed_locks: list[str] = field(default_factory=list)
    blocking_locks: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def _git_path(repo_root: Path, args: list[str]) -> Path | None:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        return None
    raw = proc.stdout.strip()
    if not raw:
        return None
    path = Path(raw)
    if path.is_absolute():
        return path
    return (repo_root / path).resolve()


def _iter_allowed_locks(git_dir: Path, git_common_dir: Path) -> list[Path]:
    locks: list[Path] = []
    seen: set[Path] = set()
    for path in (git_dir / "index.lock", git_dir / "HEAD.lock", git_common_dir / "index.lock", git_common_dir / "HEAD.lock"):
        if path in seen:
            continue
        seen.add(path)
        if path.exists():
            locks.append(path)

    refs_roots = [git_common_dir / "refs"]
    git_refs = git_dir / "refs"
    if git_refs != refs_roots[0]:
        refs_roots.append(git_refs)
    for refs_root in refs_roots:
        if not refs_root.exists():
            continue
        for path in sorted(refs_root.rglob("*.lock")):
            if path in seen:
                continue
            seen.add(path)
            locks.append(path)
    return locks


def _load_process_table() -> tuple[list[tuple[int, str]] | None, str | None]:
    try:
        proc = subprocess.run(
            ["ps", "-eo", "pid=,args="],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return None, "ps timed out"
    if proc.returncode != 0:
        details = (proc.stderr or "").strip() or (proc.stdout or "").strip() or "ps failed"
        return None, details
    rows: list[tuple[int, str]] = []
    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pid_text, _, args = stripped.partition(" ")
        if not pid_text.isdigit():
            continue
        rows.append((int(pid_text), args.strip()))
    return rows, None


def _mentions_same_repo(args: str, repo_root: Path, git_dir: Path, git_common_dir: Path) -> bool:
    haystack = args.lower()
    for path in {repo_root, git_dir, git_common_dir}:
        normalized = str(path).lower()
        if normalized and normalized in haystack:
            return True
    return False


def _is_interesting_process(args: str) -> bool:
    names = (
        " git ",
        "/git ",
        "start_build.py",
        "close_build.py",
        "closure_pack.py",
        "git_workflow.py",
    )
    haystack = f" {args.lower()} "
    return any(name in haystack for name in names)


def _active_lock_owner_note(
    repo_root: Path,
    git_dir: Path,
    git_common_dir: Path,
) -> str | None:
    processes, error = _load_process_table()
    if processes is None:
        return f"process detection unavailable: {error}"

    current_pid = os.getpid()
    for pid, args in processes:
        if pid == current_pid:
            continue
        if not _is_interesting_process(args):
            continue
        if _mentions_same_repo(args, repo_root, git_dir, git_common_dir):
            return f"active process pid={pid}: {args}"
    return None


def inspect_git_locks(repo_root: Path) -> GitLockHealth:
    repo_root = Path(repo_root).resolve()
    git_dir = _git_path(repo_root, ["rev-parse", "--git-dir"])
    git_common_dir = _git_path(repo_root, ["rev-parse", "--git-common-dir"])
    if git_dir is None or git_common_dir is None:
        return GitLockHealth(
            ok=False,
            blocking_locks=[],
            notes=["unable to resolve git-dir or git-common-dir"],
        )

    existing_locks = _iter_allowed_locks(git_dir, git_common_dir)
    if not existing_locks:
        return GitLockHealth(ok=True, notes=[])

    owner_note = _active_lock_owner_note(repo_root, git_dir, git_common_dir)
    lock_strings = [str(path) for path in existing_locks]
    if owner_note is not None:
        return GitLockHealth(
            ok=False,
            blocking_locks=lock_strings,
            notes=[owner_note],
        )

    return GitLockHealth(
        ok=True,
        blocking_locks=[],
        notes=["no active git owner detected for allowlisted lockfiles"],
    )


def ensure_git_lock_health(repo_root: Path, *, auto_cleanup: bool = True) -> GitLockHealth:
    inspected = inspect_git_locks(repo_root)
    if inspected.blocking_locks:
        return inspected
    if not auto_cleanup:
        return inspected

    repo_root = Path(repo_root).resolve()
    git_dir = _git_path(repo_root, ["rev-parse", "--git-dir"])
    git_common_dir = _git_path(repo_root, ["rev-parse", "--git-common-dir"])
    if git_dir is None or git_common_dir is None:
        return inspected

    candidate_locks = _iter_allowed_locks(git_dir, git_common_dir)
    if not candidate_locks:
        return GitLockHealth(ok=True, notes=inspected.notes)

    removed: list[str] = []
    failed: list[tuple[str, str]] = []
    for path in candidate_locks:
        try:
            path.unlink()
            removed.append(str(path))
        except FileNotFoundError:
            removed.append(str(path))  # already gone — goal achieved
        except OSError as exc:
            failed.append((str(path), str(exc)))

    if failed:
        fail_notes = [f"failed to remove orphaned lock {p}: {e}" for p, e in failed]
        return GitLockHealth(
            ok=False,
            blocking_locks=[p for p, _ in failed],
            removed_locks=removed,
            notes=list(inspected.notes) + fail_notes,
        )

    notes = list(inspected.notes)
    if removed:
        notes.append(f"removed orphaned git lock(s): {', '.join(removed)}")
    return GitLockHealth(ok=True, removed_locks=removed, notes=notes)
