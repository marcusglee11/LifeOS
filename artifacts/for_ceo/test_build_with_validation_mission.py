"""
Tests for BuildWithValidationMission.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from runtime.orchestration.missions.base import (
    MissionType,
    MissionContext,
    MissionValidationError,
)
from runtime.orchestration.missions.build_with_validation import BuildWithValidationMission

@pytest.fixture
def mock_context(tmp_path: Path) -> MissionContext:
    """Create a mock mission context for testing."""
    return MissionContext(
        repo_root=tmp_path,
        baseline_commit="abc123",
        run_id="test-run-id",
    )

class TestBuildWithValidationMission:
    
    def test_mission_type(self):
        """Verify mission type is correct."""
        mission = BuildWithValidationMission()
        assert mission.mission_type == MissionType.BUILD_WITH_VALIDATION
        
    def test_validate_inputs_success(self):
        """Verify valid inputs pass validation."""
        mission = BuildWithValidationMission()
        # Should not raise
        mission.validate_inputs({"task_description": "Implement feature X"})
        
    def test_validate_inputs_fail(self):
        """Verify missing task_description fails validation."""
        mission = BuildWithValidationMission()
        with pytest.raises(MissionValidationError) as exc_info:
            mission.validate_inputs({})
        assert "task_description" in str(exc_info.value)
        
    @patch("runtime.agents.api.call_agent")
    def test_run_success_first_try(self, mock_call_agent, mock_context):
        """Verify success when validator approves on first try."""
        # Worker response
        worker_resp = MagicMock()
        worker_resp.content = "Implemented code"
        worker_resp.model_used = "worker-model"
        
        # Validator response
        validator_resp = MagicMock()
        validator_resp.content = "APPROVED: Looks great."
        validator_resp.model_used = "validator-model"
        
        mock_call_agent.side_effect = [worker_resp, validator_resp]
        
        mission = BuildWithValidationMission()
        inputs = {"task_description": "Task X"}
        result = mission.run(mock_context, inputs)
        
        assert result.success is True
        assert result.outputs["result"] == "Implemented code"
        assert len(result.executed_steps) == 2
        assert result.executed_steps == ["worker_iter_1", "validator_iter_1"]
        assert result.evidence["iterations"] == 1

    @patch("runtime.agents.api.call_agent")
    def test_run_success_second_try(self, mock_call_agent, mock_context):
        """Verify success when validator approves on second try."""
        # Iteration 1
        w1 = MagicMock(content="Buggy code", model_used="m")
        v1 = MagicMock(content="REJECTED: Fix the bug", model_used="m")
        
        # Iteration 2
        w2 = MagicMock(content="Fixed code", model_used="m")
        v2 = MagicMock(content="APPROVED", model_used="m")
        
        mock_call_agent.side_effect = [w1, v1, w2, v2]
        
        mission = BuildWithValidationMission()
        inputs = {"task_description": "Task X", "max_iterations": 2}
        result = mission.run(mock_context, inputs)
        
        assert result.success is True
        assert result.outputs["result"] == "Fixed code"
        assert len(result.executed_steps) == 4
        assert result.evidence["iterations"] == 2

    @patch("runtime.agents.api.call_agent")
    def test_run_failure_max_iterations(self, mock_call_agent, mock_context):
        """Verify failure when max iterations reached without approval."""
        # Iteration 1
        w1 = MagicMock(content="c1", model_used="m")
        v1 = MagicMock(content="REJECTED", model_used="m")
        
        # Iteration 2
        w2 = MagicMock(content="c2", model_used="m")
        v2 = MagicMock(content="REJECTED again", model_used="m")
        
        mock_call_agent.side_effect = [w1, v1, w2, v2]
        
        mission = BuildWithValidationMission()
        inputs = {"task_description": "Task X", "max_iterations": 2}
        result = mission.run(mock_context, inputs)
        
        assert result.success is False
        assert "Validation failed after 2 iterations" in result.error
        assert result.escalation_reason is not None
        assert len(result.executed_steps) == 4
