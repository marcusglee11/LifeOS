"""Trusted workspace lock with stale-lock handling for validator orchestration."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Any, Dict


LOCK_RELATIVE_PATH = Path("artifacts/validation_runs/.validator_workspace.lock")


class WorkspaceLockError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class WorkspaceLockHandle:
    workspace_root: Path
    lock_path: Path
    run_id: str
    attempt_id: str


def lock_path_for_workspace(workspace_root: Path) -> Path:
    return workspace_root.resolve() / LOCK_RELATIVE_PATH


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


def acquire_workspace_lock(
    workspace_root: Path,
    run_id: str,
    attempt_id: str,
    ttl_seconds: int = 900,
) -> WorkspaceLockHandle:
    workspace_root = workspace_root.resolve()
    lock_path = lock_path_for_workspace(workspace_root)
    now = int(time.time())

    payload = {
        "schema_version": "workspace_lock_v1",
        "pid": os.getpid(),
        "created_at_epoch": now,
        "run_id": run_id,
        "attempt_id": attempt_id,
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
            return WorkspaceLockHandle(workspace_root=workspace_root, lock_path=lock_path, run_id=run_id, attempt_id=attempt_id)
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
            holder_attempt_id = existing.get("attempt_id", "unknown")
            raise WorkspaceLockError(
                "CONCURRENT_RUN_DETECTED",
                f"Workspace lock held by pid={existing_pid} run_id={holder_run_id} attempt_id={holder_attempt_id}",
            )

    raise WorkspaceLockError("CONCURRENT_RUN_DETECTED", "Unable to acquire workspace lock")


def release_workspace_lock(handle: WorkspaceLockHandle) -> bool:
    if not handle.lock_path.exists():
        return False

    payload = _load_lock(handle.lock_path)
    if payload.get("run_id") != handle.run_id:
        return False

    handle.lock_path.unlink(missing_ok=True)
    return True
