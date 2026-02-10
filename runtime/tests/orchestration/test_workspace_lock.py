from __future__ import annotations

from pathlib import Path
import json
import time

import pytest

from runtime.orchestration.workspace_lock import (
    WorkspaceLockError,
    acquire_workspace_lock,
    lock_path_for_workspace,
    release_workspace_lock,
)


def test_active_lock_detected(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    handle = acquire_workspace_lock(workspace, run_id="run-a", attempt_id="attempt-0001", ttl_seconds=60)

    try:
        with pytest.raises(WorkspaceLockError) as exc:
            acquire_workspace_lock(workspace, run_id="run-b", attempt_id="attempt-0001", ttl_seconds=60)
        assert exc.value.code == "CONCURRENT_RUN_DETECTED"
    finally:
        assert release_workspace_lock(handle)


def test_stale_lock_is_cleared(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    lock_path = lock_path_for_workspace(workspace)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    stale_payload = {
        "schema_version": "workspace_lock_v1",
        "pid": 999999,
        "created_at_epoch": int(time.time()) - 10_000,
        "run_id": "stale-run",
        "attempt_id": "attempt-0001",
    }
    lock_path.write_text(json.dumps(stale_payload), encoding="utf-8")

    handle = acquire_workspace_lock(workspace, run_id="fresh-run", attempt_id="attempt-0001", ttl_seconds=10)
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
        assert payload["run_id"] == "fresh-run"
    finally:
        assert release_workspace_lock(handle)


def test_dead_pid_within_ttl_still_blocks(tmp_path: Path) -> None:
    workspace = tmp_path / "ws"
    lock_path = lock_path_for_workspace(workspace)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "workspace_lock_v1",
        "pid": 999999,
        "created_at_epoch": int(time.time()),
        "run_id": "other-run",
        "attempt_id": "attempt-0001",
    }
    lock_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(WorkspaceLockError) as exc:
        acquire_workspace_lock(workspace, run_id="run-new", attempt_id="attempt-0001", ttl_seconds=300)

    assert exc.value.code == "CONCURRENT_RUN_DETECTED"
