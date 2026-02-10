"""
Tests for test failure classification (Phase 3a).

Tests the classify_test_failure() function:
- TEST_TIMEOUT classification for timeout results
- TEST_FLAKE detection when test passed previously
- TEST_FAILURE for standard failures
"""

import pytest

from runtime.orchestration.loop.failure_classifier import classify_test_failure
from runtime.orchestration.loop.taxonomy import FailureClass
from runtime.orchestration.test_executor import PytestResult


class TestFailureClassification:
    """Tests for test failure classification."""

    def test_timeout_classified_as_test_timeout(self):
        """TIMEOUT status maps to TEST_TIMEOUT class."""
        result = PytestResult(
            status="TIMEOUT",
            exit_code=-15,  # SIGTERM
            stdout="",
            stderr="",
            duration=300.0,
            evidence={"timeout_triggered": True},
        )

        failure_class = classify_test_failure(result)
        assert failure_class == FailureClass.TEST_TIMEOUT

    def test_standard_failure_is_test_failure(self):
        """New test failure without history is TEST_FAILURE."""
        result = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="",
            stderr="",
            duration=5.0,
            evidence={},
            failed_tests={"test_new"},
        )

        failure_class = classify_test_failure(result)
        assert failure_class == FailureClass.TEST_FAILURE

    def test_flaky_test_detected(self):
        """Test that passed before but fails now is TEST_FLAKE."""
        previous = PytestResult(
            status="PASS",
            exit_code=0,
            stdout="",
            stderr="",
            duration=3.0,
            evidence={},
            passed_tests={"test_foo", "test_bar"},
            failed_tests=set(),
        )

        current = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="",
            stderr="",
            duration=3.5,
            evidence={},
            passed_tests={"test_bar"},
            failed_tests={"test_foo"},  # Was passing before
        )

        failure_class = classify_test_failure(current, [previous])
        assert failure_class == FailureClass.TEST_FLAKE

    def test_flake_detection_requires_previous_pass(self):
        """Flake requires test passed in previous run."""
        previous = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="",
            stderr="",
            duration=3.0,
            evidence={},
            passed_tests=set(),
            failed_tests={"test_foo"},
        )

        current = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="",
            stderr="",
            duration=3.5,
            evidence={},
            passed_tests=set(),
            failed_tests={"test_foo"},  # Failed before too
        )

        failure_class = classify_test_failure(current, [previous])
        assert failure_class == FailureClass.TEST_FAILURE  # Not flaky, consistently fails

    def test_flake_detection_across_multiple_runs(self):
        """Flake detection works across multiple previous runs."""
        run1 = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="",
            stderr="",
            duration=3.0,
            evidence={},
            passed_tests={"test_bar"},
            failed_tests={"test_foo"},
        )

        run2 = PytestResult(
            status="PASS",
            exit_code=0,
            stdout="",
            stderr="",
            duration=3.0,
            evidence={},
            passed_tests={"test_foo", "test_bar"},  # test_foo passed this time
            failed_tests=set(),
        )

        run3 = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="",
            stderr="",
            duration=3.5,
            evidence={},
            passed_tests={"test_bar"},
            failed_tests={"test_foo"},  # Fails again
        )

        failure_class = classify_test_failure(run3, [run1, run2])
        assert failure_class == FailureClass.TEST_FLAKE  # Passed in run2

    def test_failure_without_test_names(self):
        """Failure without test names is TEST_FAILURE."""
        result = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="",
            stderr="",
            duration=5.0,
            evidence={},
            failed_tests=None,  # No test names parsed
        )

        failure_class = classify_test_failure(result)
        assert failure_class == FailureClass.TEST_FAILURE

    def test_no_previous_results_is_test_failure(self):
        """Failure with no history is TEST_FAILURE."""
        result = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="",
            stderr="",
            duration=5.0,
            evidence={},
            failed_tests={"test_something"},
        )

        failure_class = classify_test_failure(result, previous_results=None)
        assert failure_class == FailureClass.TEST_FAILURE

    def test_empty_previous_results_is_test_failure(self):
        """Failure with empty history is TEST_FAILURE."""
        result = PytestResult(
            status="FAIL",
            exit_code=1,
            stdout="",
            stderr="",
            duration=5.0,
            evidence={},
            failed_tests={"test_something"},
        )

        failure_class = classify_test_failure(result, previous_results=[])
        assert failure_class == FailureClass.TEST_FAILURE

    def test_timeout_takes_precedence_over_flake(self):
        """Timeout classification takes precedence over flake detection."""
        previous = PytestResult(
            status="PASS",
            exit_code=0,
            stdout="",
            stderr="",
            duration=3.0,
            evidence={},
            passed_tests={"test_slow"},
            failed_tests=set(),
        )

        current = PytestResult(
            status="TIMEOUT",  # Timed out
            exit_code=-15,
            stdout="",
            stderr="",
            duration=300.0,
            evidence={"timeout_triggered": True},
            failed_tests={"test_slow"},  # Would be flaky, but timeout takes precedence
        )

        failure_class = classify_test_failure(current, [previous])
        assert failure_class == FailureClass.TEST_TIMEOUT  # Not TEST_FLAKE
