"""
Test suite for BaseMission core contracts and error hierarchy.

Tests cover:
- MissionResult field contracts (success, outputs, error)
- MissionValidationError -> MissionError -> Exception inheritance chain
- _make_result() method behavior via concrete subclass
- MissionContext field accessibility
- Error result validation
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionError,
    MissionResult,
    MissionType,
    MissionValidationError,
)


class TestMission(BaseMission):
    """Concrete BaseMission subclass for testing _make_result()."""

    @property
    def mission_type(self) -> MissionType:
        return MissionType.NOOP

    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        pass

    def run(self, context: MissionContext, inputs: Dict[str, Any]) -> MissionResult:
        return self._make_result(success=True, outputs={})


def _make_context() -> MissionContext:
    """Return a minimal valid MissionContext for testing."""
    return MissionContext(
        repo_root=Path("."),
        baseline_commit="abc123",
        run_id="test-run-001",
    )


def test_mission_result_success_contract() -> None:
    """Verify success result has success=True, outputs dict, error=None."""
    result = MissionResult(
        success=True,
        mission_type=MissionType.NOOP,
        outputs={"key": "value"},
        error=None,
    )

    assert result.success is True
    assert isinstance(result.outputs, dict)
    assert result.outputs == {"key": "value"}
    assert result.error is None


def test_mission_result_error_contract() -> None:
    """Verify error result has success=False, outputs={}, non-empty error string."""
    result = MissionResult(
        success=False,
        mission_type=MissionType.NOOP,
        outputs={},
        error="Test error message",
    )

    assert result.success is False
    assert result.outputs == {}
    assert isinstance(result.error, str)
    assert len(result.error) > 0
    assert result.error == "Test error message"


def test_mission_validation_error_inheritance() -> None:
    """Assert MissionValidationError -> MissionError -> Exception chain."""
    error = MissionValidationError("Test validation error")

    assert isinstance(error, MissionValidationError)
    assert isinstance(error, MissionError)
    assert isinstance(error, Exception)

    assert MissionError in MissionValidationError.__mro__
    assert Exception in MissionValidationError.__mro__
    assert str(error) == "Test validation error"


def test_make_result_via_concrete_subclass() -> None:
    """Create minimal concrete BaseMission subclass to test _make_result()."""
    mission = TestMission()

    assert isinstance(mission, BaseMission)
    assert isinstance(mission, TestMission)


def test_mission_context_field_accessibility() -> None:
    """Verify all MissionContext fields are accessible."""
    context = MissionContext(
        repo_root=Path("/tmp/test-repo"),
        baseline_commit="deadbeef",
        run_id="run-xyz-001",
    )

    assert context.repo_root == Path("/tmp/test-repo")
    assert context.baseline_commit == "deadbeef"
    assert context.run_id == "run-xyz-001"
    assert context.operation_executor is None
    assert context.journal is None
    assert isinstance(context.metadata, dict)


def test_make_result_success() -> None:
    """Test _make_result with success=True and outputs."""
    mission = TestMission()

    result = mission._make_result(
        success=True,
        outputs={"result": "test_value", "count": 42},
    )

    assert isinstance(result, MissionResult)
    assert result.success is True
    assert result.outputs == {"result": "test_value", "count": 42}
    assert result.error is None


def test_make_result_error() -> None:
    """Test _make_result with success=False and error message."""
    mission = TestMission()

    result = mission._make_result(
        success=False,
        error="Operation failed: test error",
    )

    assert isinstance(result, MissionResult)
    assert result.success is False
    assert result.outputs == {}
    assert result.error == "Operation failed: test error"


def test_make_result_empty_outputs() -> None:
    """Test _make_result with empty outputs dict."""
    mission = TestMission()

    result = mission._make_result(success=True, outputs={})

    assert result.success is True
    assert result.outputs == {}
    assert result.error is None


def test_mission_context_with_metadata() -> None:
    """Verify MissionContext metadata field is accessible."""
    context = MissionContext(
        repo_root=Path("."),
        baseline_commit="abc",
        run_id="run-1",
        metadata={"key": "value"},
    )

    assert context.metadata == {"key": "value"}
