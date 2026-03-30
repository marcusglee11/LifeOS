"""Tests for single-flight run lock mechanism."""

from __future__ import annotations

import json
import os
import time

import pytest

from runtime.orchestration.loop.run_lock import (
    DEFAULT_TTL,
    LOCK_RELATIVE_PATH,
    UNVERIFIABLE_LOCK_GRACE_SECONDS,
    RunLockError,
    RunLockHandle,
    acquire_run_lock,
    release_run_lock,
)


def test_acquire_and_release(tmp_path):
    """Happy path: acquire, verify file, release, verify gone."""
    handle = acquire_run_lock(tmp_path, "run_001")

    lock_file = tmp_path / LOCK_RELATIVE_PATH
    assert lock_file.exists()

    payload = json.loads(lock_file.read_text("utf-8"))
    assert payload["schema_version"] == "run_lock_v1"
    assert payload["run_id"] == "run_001"
    assert payload["pid"] == os.getpid()
    assert "pid_namespace" in payload
    assert "start_ts" in payload

    released = release_run_lock(handle)
    assert released is True
    assert not lock_file.exists()


def test_concurrent_acquisition_blocked(tmp_path):
    """Second acquire with live PID raises RunLockError."""
    handle = acquire_run_lock(tmp_path, "run_001")

    with pytest.raises(RunLockError) as exc_info:
        acquire_run_lock(tmp_path, "run_002")

    assert exc_info.value.code == "CONCURRENT_RUN_DETECTED"
    assert "run_001" in str(exc_info.value)

    release_run_lock(handle)


def test_stale_lock_recovered(tmp_path):
    """Stale lock (dead PID + expired TTL) is recovered automatically."""
    lock_path = tmp_path / LOCK_RELATIVE_PATH
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    stale_payload = {
        "schema_version": "run_lock_v1",
        "pid": 999999999,  # almost certainly dead
        "created_at_epoch": int(time.time()) - DEFAULT_TTL - 100,
        "run_id": "stale_run",
        "start_ts": "2020-01-01T00:00:00+00:00",
    }
    lock_path.write_text(json.dumps(stale_payload), encoding="utf-8")

    # Should recover stale lock and acquire
    handle = acquire_run_lock(tmp_path, "run_fresh")
    assert handle.run_id == "run_fresh"

    payload = json.loads(lock_path.read_text("utf-8"))
    assert payload["run_id"] == "run_fresh"

    release_run_lock(handle)


def test_release_wrong_run_id_noop(tmp_path):
    """Release with wrong run_id returns False and doesn't remove lock."""
    handle = acquire_run_lock(tmp_path, "run_001")

    wrong_handle = RunLockHandle(
        repo_root=handle.repo_root,
        lock_path=handle.lock_path,
        run_id="run_OTHER",
    )
    released = release_run_lock(wrong_handle)
    assert released is False

    # Original lock still exists
    lock_file = tmp_path / LOCK_RELATIVE_PATH
    assert lock_file.exists()
    payload = json.loads(lock_file.read_text("utf-8"))
    assert payload["run_id"] == "run_001"

    # Clean up with correct handle
    release_run_lock(handle)


def test_configurable_ttl(tmp_path):
    """Custom TTL is honored — short TTL makes recent lock stale when PID is dead."""
    lock_path = tmp_path / LOCK_RELATIVE_PATH
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    # Lock created 10 seconds ago with dead PID
    payload = {
        "schema_version": "run_lock_v1",
        "pid": 999999999,
        "created_at_epoch": int(time.time()) - 10,
        "run_id": "old_run",
        "start_ts": "2020-01-01T00:00:00+00:00",
    }
    lock_path.write_text(json.dumps(payload), encoding="utf-8")

    # With default TTL (6h), this would NOT be stale — PID dead but not old enough
    with pytest.raises(RunLockError):
        acquire_run_lock(tmp_path, "new_run", ttl_seconds=DEFAULT_TTL)

    # With short TTL (5s), it IS stale — dead PID + age > TTL
    handle = acquire_run_lock(tmp_path, "new_run", ttl_seconds=5)
    assert handle.run_id == "new_run"
    release_run_lock(handle)


def test_release_missing_lock_returns_false(tmp_path):
    """Release when lock file is already gone returns False."""
    handle = RunLockHandle(
        repo_root=tmp_path,
        lock_path=tmp_path / LOCK_RELATIVE_PATH,
        run_id="nonexistent",
    )
    assert release_run_lock(handle) is False


def test_unverifiable_lock_within_grace_blocks(tmp_path):
    """Legacy lock without pid namespace is blocked during grace period."""
    lock_path = tmp_path / LOCK_RELATIVE_PATH
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "run_lock_v1",
        "pid": 2,
        "created_at_epoch": int(time.time()) - 10,
        "run_id": "legacy_run",
        "start_ts": "2020-01-01T00:00:00+00:00",
    }
    lock_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(RunLockError):
        acquire_run_lock(tmp_path, "new_run")


def test_unverifiable_lock_after_grace_is_recovered(tmp_path):
    """Legacy lock without pid namespace is recovered after grace period."""
    lock_path = tmp_path / LOCK_RELATIVE_PATH
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": "run_lock_v1",
        "pid": 2,
        "created_at_epoch": int(time.time()) - UNVERIFIABLE_LOCK_GRACE_SECONDS - 5,
        "run_id": "legacy_run",
        "start_ts": "2020-01-01T00:00:00+00:00",
    }
    lock_path.write_text(json.dumps(payload), encoding="utf-8")

    handle = acquire_run_lock(tmp_path, "new_run")
    assert handle.run_id == "new_run"
    release_run_lock(handle)
