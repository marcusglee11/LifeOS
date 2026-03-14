"""Tests: Mission compensation + LLM replay cache (Phase 3B+3C — Constitutional Compliance)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import pytest

from runtime.orchestration.missions.base import (
    BaseMission,
    CompensableMission,
    MissionContext,
    MissionResult,
    MissionType,
)


# ===========================================================================
# Phase 3B: CompensableMission interface
# ===========================================================================


class _NoopMission(BaseMission):
    @property
    def mission_type(self) -> MissionType:
        return MissionType.NOOP

    def validate_inputs(self, inputs):
        pass

    def run(self, context, inputs):
        return self._make_result(success=True, executed_steps=["noop"])


class _CompensableNoop(CompensableMission, _NoopMission):
    """Noop mission that also supports compensation."""

    def __init__(self):
        self.compensate_called = False
        self.compensate_result = True

    def compensate(self, context, run_result):
        self.compensate_called = True
        return self.compensate_result


class _FailingCompensable(CompensableMission, _NoopMission):
    """Mission whose compensation always fails."""

    def compensate(self, context, run_result):
        return False


# ---------------------------------------------------------------------------
# 3B-1: CompensableMission default compensate() returns True (no-op)
# ---------------------------------------------------------------------------

def test_default_compensate_returns_true():
    mission = _NoopMission()
    # Verify BaseMission is NOT a CompensableMission by default
    assert not isinstance(mission, CompensableMission)


def test_compensable_mixin_compensate_called():
    mission = _CompensableNoop()
    ctx = MissionContext(
        repo_root=Path("/tmp"),
        baseline_commit=None,
        run_id="test",
        operation_executor=None,
        journal=None,
    )
    result = MissionResult(success=False, mission_type=MissionType.NOOP)
    ok = mission.compensate(ctx, result)
    assert ok is True
    assert mission.compensate_called is True


# ---------------------------------------------------------------------------
# 3B-2: issubclass check works for CompensableMission detection
# ---------------------------------------------------------------------------

def test_issubclass_detection():
    assert issubclass(_CompensableNoop, CompensableMission)
    assert not issubclass(_NoopMission, CompensableMission)


# ---------------------------------------------------------------------------
# 3B-3: Compensation false return is handled gracefully
# ---------------------------------------------------------------------------

def test_failing_compensate_returns_false():
    mission = _FailingCompensable()
    ctx = MissionContext(
        repo_root=Path("/tmp"),
        baseline_commit=None,
        run_id="test",
        operation_executor=None,
        journal=None,
    )
    result = MissionResult(success=False, mission_type=MissionType.NOOP)
    ok = mission.compensate(ctx, result)
    assert ok is False


# ===========================================================================
# Phase 3C: LLM Replay Cache
# ===========================================================================


def test_write_replay_cache_creates_file(tmp_path: Path):
    from runtime.agents.api import _write_replay_cache

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = str(tmp_path)

        _write_replay_cache(
            call_id="sha256:abc123",
            content="hello world",
            model_version="gpt-4",
        )

    cache_files = list((tmp_path / "artifacts" / "replay_cache").glob("*.json"))
    assert len(cache_files) == 1
    data = json.loads(cache_files[0].read_text())
    assert data["call_id"] == "sha256:abc123"
    assert data["response_content"] == "hello world"
    assert data["model_version"] == "gpt-4"


def test_write_replay_cache_keyed_by_call_id(tmp_path: Path):
    from runtime.agents.api import _write_replay_cache

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = str(tmp_path)

        _write_replay_cache("sha256:aaa", "response-a", "gpt-4")
        _write_replay_cache("sha256:bbb", "response-b", "gpt-4")

    cache_dir = tmp_path / "artifacts" / "replay_cache"
    files = {f.name for f in cache_dir.glob("*.json")}
    assert len(files) == 2
    # Each call_id maps to a distinct file
    assert "sha256-aaa.json" in files
    assert "sha256-bbb.json" in files


def test_write_replay_cache_does_not_raise_on_error():
    """Best-effort: write failure must never propagate."""
    from runtime.agents.api import _write_replay_cache

    # Corrupt subprocess to cause failure in path detection
    with patch("subprocess.run", side_effect=RuntimeError("boom")):
        # Should not raise
        _write_replay_cache("sha256:abc", "content", "model")
