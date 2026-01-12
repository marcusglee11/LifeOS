"""
Tests for run_tests operation registration.

Proof-of-Capability Experiment: CAPABILITY_PROOF_001
Validates that run_tests operation is registered and callable.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from subprocess import TimeoutExpired

from runtime.orchestration.operations import (
    Operation,
    OperationExecutor,
    ExecutionContext,
    Envelope,
    CompensationType,
    EnvelopeViolation,
    OperationFailed,
)


class TestRunTestsRegistration:
    """Test run_tests operation registration and behavior."""
    
    @pytest.fixture
    def executor(self):
        return OperationExecutor()
    
    @pytest.fixture
    def context(self, tmp_path):
        return ExecutionContext(
            run_id="sha256:test123",
            run_id_audit="test-uuid",
            mission_id="test-mission",
            mission_type="test",
            step_id="step-1",
            repo_root=tmp_path,
            baseline_commit="abc123",
            envelope=Envelope(
                allowed_paths=["tests/", "runtime/tests/"],
                allowed_tools=["pytest"],
                timeout_seconds=60,
            ),
            journal=None,
        )
    
    def test_run_tests_is_registered(self, executor):
        """run_tests operation type is recognized by executor."""
        # The _dispatch method should recognize run_tests
        # This tests that the handler is registered
        from runtime.orchestration.operations import OperationExecutor
        
        executor = OperationExecutor()
        # Access the handlers indirectly through a mock operation
        op = Operation(
            operation_id="op-test",
            type="run_tests",
            params={},
            compensation_type=CompensationType.NONE,
        )
        
        # Should not raise "Unknown operation type" 
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="test output",
                stderr="",
            )
            # If run_tests is not registered, this would fail with OperationError
            result = executor.execute(op, self.make_context())
            
            assert result.operation_id == "op-test"
            assert result.type == "run_tests"
    
    def test_run_tests_executes_pytest(self, executor, context):
        """run_tests calls pytest with correct arguments."""
        op = Operation(
            operation_id="op-pytest",
            type="run_tests",
            params={"test_paths": ["tests/"], "pytest_args": ["-v"]},
            compensation_type=CompensationType.NONE,
        )
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="1 passed",
                stderr="",
            )
            
            result = executor.execute(op, context)
            
            assert result.status == "success"
            assert result.output["passed"] is True
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert "pytest" in str(call_args)
    
    def test_run_tests_returns_output_on_failure(self, executor, context):
        """run_tests captures output even when tests fail."""
        op = Operation(
            operation_id="op-fail",
            type="run_tests",
            params={"test_paths": ["tests/"]},
            compensation_type=CompensationType.NONE,
        )
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="1 failed",
                stderr="error details",
            )
            
            result = executor.execute(op, context)
            
            assert result.status == "success"  # Operation succeeded, tests failed
            assert result.output["passed"] is False
            assert result.output["exit_code"] == 1
            assert "failed" in result.output["stdout"]
    
    def test_run_tests_enforces_envelope(self, executor, context):
        """run_tests rejects paths outside envelope."""
        op = Operation(
            operation_id="op-envelope",
            type="run_tests",
            params={"test_paths": ["config/secrets/"]},  # Not in allowed_paths
            compensation_type=CompensationType.NONE,
        )
        
        with patch("subprocess.run"):
            result = executor.execute(op, context)
            
            assert result.status == "failed"
            assert "not in allowed paths" in result.evidence.get("error", "")
    
    def test_run_tests_handles_timeout(self, executor, context):
        """run_tests handles pytest timeout gracefully."""
        op = Operation(
            operation_id="op-timeout",
            type="run_tests",
            params={"test_paths": ["tests/"]},
            compensation_type=CompensationType.NONE,
        )
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = TimeoutExpired(cmd=["pytest"], timeout=60)
            
            result = executor.execute(op, context)
            
            assert result.status == "failed"
            assert "timed out" in result.evidence.get("error", "")
    
    def make_context(self, tmp_path=None):
        """Create a test context."""
        return ExecutionContext(
            run_id="sha256:test",
            run_id_audit="test-uuid",
            mission_id="test-mission",
            mission_type="test",
            step_id="step-1",
            repo_root=Path(tmp_path or "/tmp"),
            baseline_commit="abc123",
            envelope=Envelope(
                allowed_paths=["tests/", "runtime/tests/"],
                timeout_seconds=60,
            ),
            journal=None,
        )
