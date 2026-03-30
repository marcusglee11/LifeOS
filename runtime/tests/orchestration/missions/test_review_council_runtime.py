from __future__ import annotations

import os
import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.orchestration.council.models import CouncilRuntimeResult
from runtime.orchestration.missions.base import MissionContext
from runtime.orchestration.missions.review import ReviewMission


def _context(tmp_path: Path) -> MissionContext:
    return MissionContext(
        repo_root=tmp_path,
        baseline_commit="abc123",
        run_id="review-run-1",
        operation_executor=None,
    )


def _inputs() -> dict:
    return {
        "subject_packet": {"goal": "test"},
        "review_type": "build_review",
        "use_council_runtime": True,
    }


@patch("runtime.orchestration.missions.review.load_council_policy")
@patch("runtime.orchestration.missions.review.CouncilFSMv2")
def test_review_mission_opt_in_maps_protocol_verdict(MockFSM, mock_load_policy, tmp_path: Path):
    mock_policy = object()
    mock_load_policy.return_value = mock_policy

    runtime_result = CouncilRuntimeResult(
        status="complete",
        run_log={"synthesis": {"verdict": "Accept"}},
        decision_payload={"status": "COMPLETE", "verdict": "Accept", "run_id": "council-1"},
        block_report=None,
    )
    MockFSM.return_value.run.return_value = runtime_result

    mission = ReviewMission()
    result = mission.run(_context(tmp_path), _inputs())

    assert result.success is True
    assert result.outputs["verdict"] == "approved"
    assert "prepare_ccp" in result.executed_steps
    assert "execute_council_fsm" in result.executed_steps
    assert result.evidence["usage"]["total"] == 0


@patch("runtime.orchestration.missions.review.load_council_policy")
@patch("runtime.orchestration.missions.review.CouncilFSMv2")
def test_review_mission_opt_in_handles_blocked_runtime(MockFSM, mock_load_policy, tmp_path: Path):
    mock_policy = object()
    mock_load_policy.return_value = mock_policy

    runtime_result = CouncilRuntimeResult(
        status="blocked",
        run_log={"status": "blocked"},
        decision_payload={"status": "BLOCKED", "reason": "required_seats_missing"},
        block_report={"category": "required_seats_missing", "detail": "Chair failed"},
    )
    MockFSM.return_value.run.return_value = runtime_result

    mission = ReviewMission()
    result = mission.run(_context(tmp_path), _inputs())

    assert result.success is True
    assert result.outputs["verdict"] == "escalate"
    assert "Council runtime blocked" in (result.escalation_reason or "")


@patch("runtime.orchestration.missions.review.load_council_policy")
@patch("runtime.orchestration.missions.review.CouncilFSMv2")
def test_review_mission_revise_verdict_maps_to_needs_revision(
    MockFSM, mock_load_policy, tmp_path: Path
):
    """'Revise' (v2.2.1 verdict) must map to 'needs_revision' mission verdict."""
    mock_load_policy.return_value = object()

    runtime_result = CouncilRuntimeResult(
        status="complete",
        run_log={"synthesis": {"verdict": "Revise"}},
        decision_payload={
            "status": "COMPLETE",
            "verdict": "Revise",
            "run_id": "council-2",
            "tier": "T1",
        },
        block_report=None,
    )
    MockFSM.return_value.run.return_value = runtime_result

    mission = ReviewMission()
    result = mission.run(_context(tmp_path), _inputs())

    assert result.success is True
    assert result.outputs["verdict"] == "needs_revision"


@patch("runtime.orchestration.missions.review.load_council_policy")
@patch("runtime.orchestration.missions.review.CouncilFSMv2")
def test_review_mission_ccp_includes_run_type_and_output_has_tier(
    MockFSM, mock_load_policy, tmp_path: Path
):
    """CCP header must include run_type; council_decision output must include tier."""
    mock_load_policy.return_value = object()

    captured_ccp: dict = {}

    def capture_run(ccp):
        captured_ccp.update(ccp)
        return CouncilRuntimeResult(
            status="complete",
            run_log={"synthesis": {"verdict": "Accept"}},
            decision_payload={
                "status": "COMPLETE",
                "verdict": "Accept",
                "run_id": "c3",
                "tier": "T2",
            },
            block_report=None,
        )

    MockFSM.return_value.run.side_effect = capture_run

    mission = ReviewMission()
    result = mission.run(_context(tmp_path), _inputs())

    # CCP header must have run_type
    header = captured_ccp.get("header", {})
    assert "run_type" in header, "CCP header missing run_type"

    # council_decision output must include tier
    council_decision = result.outputs.get("council_decision", {})
    assert "tier" in council_decision, "council_decision missing tier"


@patch("runtime.orchestration.missions.review.load_council_policy")
@patch("runtime.orchestration.missions.review.CouncilFSMv2")
def test_review_mission_allows_advisory_run_type(MockFSM, mock_load_policy, tmp_path: Path):
    mock_load_policy.return_value = object()
    captured_ccp: dict = {}

    def capture_run(ccp):
        captured_ccp.update(ccp)
        return CouncilRuntimeResult(
            status="complete",
            run_log={"synthesis": {"verdict": "Accept"}},
            decision_payload={
                "status": "COMPLETE",
                "verdict": "Accept",
                "run_id": "c4",
                "tier": "T1",
            },
            block_report=None,
        )

    MockFSM.return_value.run.side_effect = capture_run

    mission = ReviewMission()
    inputs = _inputs()
    inputs["run_type"] = "advisory"
    result = mission.run(_context(tmp_path), inputs)

    assert result.success is True
    header = captured_ccp.get("header", {})
    assert header.get("run_type") == "advisory"


@pytest.mark.skipif(
    os.environ.get("RUN_LIVE_REVIEW_COUNCIL_RUNTIME") != "1"
    or not all(shutil.which(t) for t in ("claude", "codex", "gemini")),
    reason="Set RUN_LIVE_REVIEW_COUNCIL_RUNTIME=1 with claude/codex/gemini CLIs available to run live delegated council dispatch",
)
def test_review_mission_real_v2_runtime_path_smoke(tmp_path: Path):
    mission = ReviewMission()
    result = mission.run(_context(tmp_path), _inputs())

    assert result.success is True
    assert "execute_council_fsm" in result.executed_steps
    assert result.outputs["verdict"] in {"approved", "needs_revision", "rejected", "escalate"}
    council_decision = result.outputs.get("council_decision", {})
    assert council_decision.get("tier") in {"T0", "T1", "T2", "T3"}


def test_review_mission_config_loaded_once_per_instance():
    """ReviewMission loads ModelConfig in __init__, not per run() call."""
    m = ReviewMission()
    assert hasattr(m, "_model_config")
    assert m._model_config is not None
    m2 = ReviewMission()
    assert m._model_config is not m2._model_config  # separate instances, not shared
