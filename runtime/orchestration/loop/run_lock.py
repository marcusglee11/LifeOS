"""Single-flight mutex for spine runs — prevents concurrent loop execution.

Follows the proven workspace_lock.py pattern (atomic O_CREAT|O_EXCL, PID liveness,
stale-lock recovery). Lock file lives at artifacts/locks/run.lock.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Any, Dict


LOCK_RELATIVE_PATH = Path("artifacts/locks/run.lock")
DEFAULT_TTL = 21600  # 6 hours


class RunLockError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class RunLockHandle:
    repo_root: Path
    lock_path: Path
    run_id: str


def _lock_path_for_repo(repo_root: Path) -> Path:
    return repo_root.resolve() / LOCK_RELATIVE_PATH


def _is_pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _load_lock(lock_path: Path) -> Dict[str, Any]:
    try:
        with open(lock_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return {}
    if not isinstance(payload, dict):
        return {}
    return payload


def acquire_run_lock(
    repo_root: Path,
    run_id: str,
    ttl_seconds: int = DEFAULT_TTL,
) -> RunLockHandle:
    """Acquire single-flight run lock. Fails closed on contention.

    Args:
        repo_root: Repository root path.
        run_id: Current run identifier.
        ttl_seconds: Time-to-live before a lock is considered stale.

    Returns:
        RunLockHandle on success.

    Raises:
        RunLockError: If lock is held by a live process.
    """
    repo_root = repo_root.resolve()
    lock_path = _lock_path_for_repo(repo_root)
    now = int(time.time())

    from datetime import datetime, timezone
    start_ts = datetime.now(timezone.utc).isoformat()

    payload = {
        "schema_version": "run_lock_v1",
        "pid": os.getpid(),
        "created_at_epoch": now,
        "run_id": run_id,
        "start_ts": start_ts,
    }

    lock_path.parent.mkdir(parents=True, exist_ok=True)

    for _ in range(2):
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                    json.dump(payload, handle, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
                    handle.write("\n")
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
                raise
            return RunLockHandle(repo_root=repo_root, lock_path=lock_path, run_id=run_id)
        except FileExistsError:
            existing = _load_lock(lock_path)
            existing_pid = int(existing.get("pid") or 0)
            created_at_epoch = int(existing.get("created_at_epoch") or 0)
            age_seconds = now - created_at_epoch if created_at_epoch else ttl_seconds + 1
            stale = (not existing_pid or not _is_pid_alive(existing_pid)) and age_seconds > ttl_seconds
            if stale:
                lock_path.unlink(missing_ok=True)
                continue
            holder_run_id = existing.get("run_id", "unknown")
            raise RunLockError(
                "CONCURRENT_RUN_DETECTED",
                f"Run lock held by pid={existing_pid} run_id={holder_run_id}",
            )

    raise RunLockError("CONCURRENT_RUN_DETECTED", "Unable to acquire run lock")


def release_run_lock(handle: RunLockHandle) -> bool:
    """Release run lock. Only releases if run_id matches (ownership check).

    Args:
        handle: Lock handle from acquire_run_lock.

    Returns:
        True if lock was released, False if lock was missing or owned by another run.
    """
    if not handle.lock_path.exists():
        return False

    payload = _load_lock(handle.lock_path)
    if payload.get("run_id") != handle.run_id:
        return False

    handle.lock_path.unlink(missing_ok=True)
    return True
