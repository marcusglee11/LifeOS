"""Tests for shadow council wiring in ReviewMission."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runtime.orchestration.missions.review import ReviewMission
from runtime.orchestration.missions.base import MissionContext


def _make_context(tmp_path):
    return MissionContext(
        repo_root=tmp_path,
        baseline_commit="abc123",
        run_id="run_shadow_test",
        operation_executor=None,
        journal=None,
        metadata={},
    )


def _make_inputs():
    return {
        "subject_packet": {"payload": {"test": True}},
        "review_type": "build_review",
    }


def _mock_agent_response():
    resp = MagicMock()
    resp.packet = {"verdict": "approved", "rationale": "LGTM", "concerns": [], "recommendations": []}
    resp.content = "approved"
    resp.call_id = "call_001"
    resp.model_used = "test-model"
    resp.usage = {"total": 100}
    return resp


def test_review_calls_shadow_after_legacy(monkeypatch, tmp_path):
    """ReviewMission.run() calls _run_shadow_council after legacy path."""
    context = _make_context(tmp_path)
    inputs = _make_inputs()

    shadow_called = []

    with patch("runtime.agents.api.call_agent", return_value=_mock_agent_response()):
        mission = ReviewMission()
        original_shadow = mission._run_shadow_council

        def track_shadow(*args, **kwargs):
            shadow_called.append(True)
            return original_shadow(*args, **kwargs)

        monkeypatch.setattr(mission, "_run_shadow_council", track_shadow)
        result = mission.run(context, inputs)

    assert result.success is True
    assert len(shadow_called) == 1, "Shadow should be called exactly once"


def test_shadow_failure_does_not_affect_result(monkeypatch, tmp_path):
    """Shadow council failure does not affect the pipeline result."""
    context = _make_context(tmp_path)
    inputs = _make_inputs()

    with patch("runtime.agents.api.call_agent", return_value=_mock_agent_response()):
        mission = ReviewMission()

        # Patch the actual shadow runner to fail
        with patch(
            "runtime.orchestration.council.shadow_runner.ShadowCouncilRunner.run_shadow",
            side_effect=RuntimeError("Shadow exploded!"),
        ):
            result = mission.run(context, inputs)

    assert result.success is True
    assert result.outputs["verdict"] == "approved"
