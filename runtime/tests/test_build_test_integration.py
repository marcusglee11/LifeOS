"""
Integration tests for build-test verification (Phase 3a).

Tests the integration of pytest execution with the build mission:
- Build -> test -> pass flow
- Build -> test -> fail -> retry -> pass flow
- Test timeout handling
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

from runtime.orchestration.missions.autonomous_build_cycle import AutonomousBuildCycleMission
from runtime.orchestration.missions.base import MissionContext
from runtime.orchestration.test_executor import PytestResult
from runtime.orchestration.loop.taxonomy import FailureClass


class TestBuildTestIntegration:
    """Integration tests for build-test verification."""

    @pytest.fixture
    def mission(self):
        """Create mission instance."""
        return AutonomousBuildCycleMission()

    @pytest.fixture
    def mock_context(self, tmp_path):
        """Create mock mission context."""
        context = MagicMock(spec=MissionContext)
        context.repo_root = tmp_path
        context.run_id = "test-run-123"
        return context

    @patch('runtime.orchestration.missions.autonomous_build_cycle.check_pytest_scope')
    @patch('runtime.orchestration.missions.autonomous_build_cycle.TestExecutor')
    def test_run_verification_tests_success(self, mock_executor_class, mock_scope, mission, mock_context, tmp_path):
        """Verification tests run successfully on passing tests."""
        # Mock scope check to allow
        mock_scope.return_value = (True, "Allowed")

        # Mock successful test execution
        mock_result = PytestResult(
            status="PASS",
            exit_code=0,
            stdout="Test output",
            stderr="",
            duration=2.5,
            evidence={"status": "PASS"},
            counts={"passed": 1, "failed": 0, "skipped": 0},
        )
        mock_executor = MagicMock()
        mock_executor.run.return_value = mock_result
        mock_executor_class.return_value = mock_executor

        # Run verification
        result = mission._run_verification_tests(mock_context, target="runtime/tests")

        assert result["success"] is True
        assert result["evidence"]["exit_code"] == 0
        assert result["evidence"]["status"] == "PASS"
        assert result["error"] is None

    @patch('runtime.orchestration.missions.autonomous_build_cycle.check_pytest_scope')
    @patch('runtime.orchestration.missions.autonomous_build_cycle.TestExecutor')
    def test_run_verification_tests_failure(self, mock_executor_class, mock_scope, mission, mock_context, tmp_path):
        """Verification tests detect test failures."""
        # Mock scope check to allow
        mock_scope.return_value = (True, "Allowed")

        # Mock failed test execution
        mock_result = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="Test output",
            stderr="",
            duration=2.5,
            evidence={"status": "FAIL"},
            counts={"passed": 0, "failed": 1, "skipped": 0},
            failed_tests={"test_failure"},
        )
        mock_executor = MagicMock()
        mock_executor.run.return_value = mock_result
        mock_executor_class.return_value = mock_executor

        # Run verification
        result = mission._run_verification_tests(mock_context, target="runtime/tests")

        assert result["success"] is False
        assert result["evidence"]["exit_code"] != 0
        assert result["evidence"]["status"] == "FAIL"
        assert result["error"] == "Tests failed"

    def test_run_verification_tests_scope_denied(self, mission, mock_context):
        """Verification tests are blocked on out-of-scope paths."""
        # Try to run tests outside allowed scope
        result = mission._run_verification_tests(
            mock_context,
            target="/etc/passwd"  # Not allowed
        )

        assert result["success"] is False
        assert "Test scope denied" in result["error"]
        assert "PATH_OUTSIDE_ALLOWED_SCOPE" in result["error"]

    @patch('runtime.orchestration.missions.autonomous_build_cycle.check_pytest_scope')
    @patch('runtime.orchestration.missions.autonomous_build_cycle.TestExecutor')
    def test_verification_timeout_handling(self, mock_executor_class, mock_scope, mission, mock_context, tmp_path):
        """Long-running tests are terminated with timeout."""
        # Mock scope check to allow
        mock_scope.return_value = (True, "Allowed")

        # Mock timeout result
        mock_result = PytestResult(
            status="TIMEOUT",
            exit_code=-15,
            stdout="",
            stderr="",
            duration=2.0,
            evidence={"status": "TIMEOUT", "timeout_triggered": True},
        )
        mock_executor = MagicMock()
        mock_executor.run.return_value = mock_result
        mock_executor_class.return_value = mock_executor

        # Run with short timeout
        result = mission._run_verification_tests(
            mock_context,
            target="runtime/tests",
            timeout=2  # 2 second timeout
        )

        assert result["success"] is False
        assert result["evidence"]["status"] == "TIMEOUT"
        assert result["evidence"]["timeout_triggered"] is True

    def test_prepare_retry_context_test_failure(self, mission):
        """Retry context is prepared correctly for test failures."""
        # Create a failed test result
        test_result = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="",
            stderr="",
            duration=5.0,
            evidence={},
            failed_tests={"test_example"},
            error_messages=["AssertionError: expected True, got False"],
        )

        verification = {
            "success": False,
            "test_result": test_result,
            "evidence": {},
        }

        context = mission._prepare_retry_context(verification)

        assert context["failure_class"] == FailureClass.TEST_FAILURE.value
        assert "test_example" in context["failed_tests"]
        assert len(context["error_messages"]) > 0
        assert "suggestion" in context

    def test_prepare_retry_context_flake_detection(self, mission):
        """Retry context detects flaky tests."""
        # Previous run: test passed
        previous = PytestResult(
            status="PASS",
            exit_code=0,
            stdout="",
            stderr="",
            duration=3.0,
            evidence={},
            passed_tests={"test_flaky"},
        )

        # Current run: same test failed
        current = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="",
            stderr="",
            duration=3.5,
            evidence={},
            failed_tests={"test_flaky"},
        )

        verification = {
            "success": False,
            "test_result": current,
            "evidence": {},
        }

        context = mission._prepare_retry_context(verification, [previous])

        assert context["failure_class"] == FailureClass.TEST_FLAKE.value
        assert "flaky" in context["suggestion"].lower()

    def test_prepare_retry_context_timeout(self, mission):
        """Retry context handles timeout failures."""
        test_result = PytestResult(
            status="TIMEOUT",
            exit_code=-15,
            stdout="",
            stderr="",
            duration=300.0,
            evidence={"timeout_triggered": True},
        )

        verification = {
            "success": False,
            "test_result": test_result,
            "evidence": {},
        }

        context = mission._prepare_retry_context(verification)

        assert context["failure_class"] == FailureClass.TEST_TIMEOUT.value
        assert "timeout" in context["suggestion"].lower()

    @patch('runtime.orchestration.missions.autonomous_build_cycle.check_pytest_scope')
    @patch('runtime.orchestration.missions.autonomous_build_cycle.TestExecutor')
    def test_evidence_captured_in_verification(self, mock_executor_class, mock_scope, mission, mock_context, tmp_path):
        """Test evidence is properly captured and truncated."""
        # Mock scope check to allow
        mock_scope.return_value = (True, "Allowed")

        # Mock result with output
        mock_result = PytestResult(
            status="PASS",
            exit_code=0,
            stdout="Test output message" * 100,
            stderr="",
            duration=2.5,
            evidence={"status": "PASS"},
            counts={"passed": 1, "failed": 0, "skipped": 0},
        )
        mock_executor = MagicMock()
        mock_executor.run.return_value = mock_result
        mock_executor_class.return_value = mock_executor

        result = mission._run_verification_tests(mock_context, target="runtime/tests")

        evidence = result["evidence"]
        assert "pytest_stdout" in evidence
        assert "pytest_stderr" in evidence
        assert "exit_code" in evidence
        assert "duration_seconds" in evidence
        assert "test_counts" in evidence

        # Check truncation (should not exceed 50KB)
        assert len(evidence["pytest_stdout"]) <= 50 * 1024
        assert len(evidence["pytest_stderr"]) <= 50 * 1024

    def test_fix_suggestions_generated(self, mission):
        """Fix suggestions are generated for different failure classes."""
        # Test each failure class
        for failure_class in [
            FailureClass.TEST_FAILURE,
            FailureClass.TEST_FLAKE,
            FailureClass.TEST_TIMEOUT,
        ]:
            suggestion = mission._generate_fix_suggestion(failure_class)
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0

    @patch('runtime.orchestration.missions.autonomous_build_cycle.check_pytest_scope')
    @patch('runtime.orchestration.missions.autonomous_build_cycle.TestExecutor')
    def test_verification_with_mixed_results(self, mock_executor_class, mock_scope, mission, mock_context, tmp_path):
        """Verification handles mixed pass/fail test results."""
        # Mock scope check to allow
        mock_scope.return_value = (True, "Allowed")

        # Mock mixed results
        mock_result = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="Test output",
            stderr="",
            duration=3.0,
            evidence={"status": "FAIL"},
            counts={"passed": 2, "failed": 1, "skipped": 0},
            passed_tests={"test_pass", "test_pass_2"},
            failed_tests={"test_fail"},
        )
        mock_executor = MagicMock()
        mock_executor.run.return_value = mock_result
        mock_executor_class.return_value = mock_executor

        result = mission._run_verification_tests(mock_context, target="runtime/tests")

        # Overall should fail (1 failure)
        assert result["success"] is False
        assert result["evidence"]["test_counts"]["passed"] >= 2
        assert result["evidence"]["test_counts"]["failed"] >= 1
