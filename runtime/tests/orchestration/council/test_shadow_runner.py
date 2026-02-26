"""Tests for Council V2 shadow runner."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runtime.orchestration.council.shadow_runner import ShadowCouncilRunner


def _make_mock_result(status="complete", decision_payload=None):
    """Create a mock CouncilRuntimeResult."""
    result = MagicMock()
    result.status = status
    result.decision_payload = decision_payload or {"verdict": "Accept", "status": "COMPLETE"}
    result.run_log = {}
    result.block_report = None
    return result


def test_shadow_produces_verdict(tmp_path):
    """Shadow runner writes verdict.json with correct schema."""
    runner = ShadowCouncilRunner(tmp_path)
    mock_result = _make_mock_result()

    with patch("runtime.orchestration.council.CouncilFSMv2") as MockFSM, \
         patch("runtime.orchestration.council.load_council_policy") as mock_policy:
        mock_policy.return_value = {}
        MockFSM.return_value.run.return_value = mock_result

        verdict = runner.run_shadow(run_id="run_test_001", ccp={"header": {}, "sections": {}})

    assert verdict["schema_version"] == "shadow_council_v1"
    assert verdict["run_id"] == "run_test_001"
    assert verdict["status"] == "complete"
    assert "verdict_hash" in verdict
    assert verdict["verdict_hash"].startswith("sha256:")

    # Verify file on disk
    verdict_file = tmp_path / "artifacts" / "shadow_council" / "run_test_001" / "verdict.json"
    assert verdict_file.exists()
    disk_verdict = json.loads(verdict_file.read_text("utf-8"))
    assert disk_verdict["run_id"] == "run_test_001"


def test_shadow_catches_fsm_error(tmp_path):
    """Shadow runner catches FSM errors and returns error verdict."""
    runner = ShadowCouncilRunner(tmp_path)

    with patch("runtime.orchestration.council.CouncilFSMv2") as MockFSM, \
         patch("runtime.orchestration.council.load_council_policy") as mock_policy:
        mock_policy.return_value = {}
        MockFSM.return_value.run.side_effect = RuntimeError("FSM exploded")

        verdict = runner.run_shadow(run_id="run_error_001", ccp={})

    assert verdict["status"] == "shadow_error"
    assert "FSM exploded" in verdict["error"]
    assert verdict["schema_version"] == "shadow_council_v1"

    # Error verdict persisted to disk
    verdict_file = tmp_path / "artifacts" / "shadow_council" / "run_error_001" / "verdict.json"
    assert verdict_file.exists()


def test_shadow_output_directory_structure(tmp_path):
    """Shadow runner creates artifacts/shadow_council/<run_id>/ structure."""
    runner = ShadowCouncilRunner(tmp_path)
    mock_result = _make_mock_result()

    with patch("runtime.orchestration.council.CouncilFSMv2") as MockFSM, \
         patch("runtime.orchestration.council.load_council_policy") as mock_policy:
        mock_policy.return_value = {}
        MockFSM.return_value.run.return_value = mock_result

        runner.run_shadow(run_id="run_dir_001", ccp={})

    expected_dir = tmp_path / "artifacts" / "shadow_council" / "run_dir_001"
    assert expected_dir.is_dir()
    assert (expected_dir / "verdict.json").is_file()


def test_shadow_verdict_schema(tmp_path):
    """Shadow verdict contains all required fields."""
    runner = ShadowCouncilRunner(tmp_path)
    decision = {"verdict": "Accept", "status": "COMPLETE", "tier": "T2"}
    mock_result = _make_mock_result(decision_payload=decision)

    with patch("runtime.orchestration.council.CouncilFSMv2") as MockFSM, \
         patch("runtime.orchestration.council.load_council_policy") as mock_policy:
        mock_policy.return_value = {}
        MockFSM.return_value.run.return_value = mock_result

        verdict = runner.run_shadow(run_id="run_schema_001", ccp={})

    required_keys = {"schema_version", "run_id", "timestamp", "status", "decision_payload", "verdict_hash"}
    assert required_keys.issubset(set(verdict.keys()))
    assert verdict["decision_payload"] == decision
