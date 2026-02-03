"""
Test Failure Classification - Phase 3a

Classifies pytest test failures into structured taxonomy:
- TEST_FAILURE: Standard test assertion failure
- TEST_FLAKE: Test that failed but passed in previous run
- TEST_TIMEOUT: Test execution exceeded timeout threshold
"""
from __future__ import annotations

from typing import List, Optional

from runtime.orchestration.loop.taxonomy import FailureClass
from runtime.orchestration.test_executor import PytestResult


def classify_test_failure(
    result: PytestResult,
    previous_results: Optional[List[PytestResult]] = None
) -> FailureClass:
    """
    Classify a pytest failure into FailureClass.

    Classification rules:
    1. If status == "TIMEOUT": return TEST_TIMEOUT
    2. If failed but passed on previous run: return TEST_FLAKE
    3. Otherwise: return TEST_FAILURE

    Args:
        result: Current pytest execution result
        previous_results: Optional list of previous pytest results for flake detection

    Returns:
        FailureClass enum value
    """
    # Rule 1: Timeout
    if result.status == "TIMEOUT":
        return FailureClass.TEST_TIMEOUT

    # Rule 2: Flakiness detection
    if previous_results and result.failed_tests:
        # Build set of tests that passed in any previous run
        prev_passed = set()
        for prev in previous_results:
            if prev.passed_tests:
                prev_passed.update(prev.passed_tests)

        # Check if any currently failed test passed before
        flaky = result.failed_tests & prev_passed
        if flaky:
            return FailureClass.TEST_FLAKE

    # Rule 3: Standard failure
    return FailureClass.TEST_FAILURE
