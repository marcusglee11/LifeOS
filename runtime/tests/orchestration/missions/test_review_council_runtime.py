from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

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
@patch("runtime.orchestration.missions.review.CouncilFSM")
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
@patch("runtime.orchestration.missions.review.CouncilFSM")
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
