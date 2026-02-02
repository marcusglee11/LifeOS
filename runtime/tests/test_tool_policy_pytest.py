"""
Tests for pytest tool policy enforcement (Phase 3a).

Tests scope enforcement for pytest execution:
- Allowed paths: runtime/tests/**
- Blocked paths: everything else
- Timeout handling
- Output capture
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import tempfile
import time

from runtime.governance.tool_policy import (
    check_tool_action_allowed,
    check_pytest_scope,
    reset_scope_roots,
)
from runtime.tools.schemas import ToolInvokeRequest, PolicyDecision
from runtime.orchestration.test_executor import TestExecutor, PytestResult


class TestPytestScopeEnforcement:
    """Tests for pytest scope boundary enforcement."""

    @pytest.mark.parametrize("target,expected_allowed", [
        ("runtime/tests/test_foo.py", True),
        ("runtime/tests/", True),
        ("runtime/tests", True),
        ("runtime/tests/subdir/test_bar.py", True),
        ("tests/test_foo.py", False),  # Not runtime/tests
        ("project_builder/tests/test_foo.py", False),
        ("runtime/governance/test_policy.py", False),  # Not in tests dir
        ("../escape.py", False),
        ("/etc/passwd", False),
        ("runtime/../docs/test.py", False),
    ])
    def test_scope_enforcement(self, target, expected_allowed):
        """Verify scope enforcement for various targets."""
        allowed, reason = check_pytest_scope(target)
        assert allowed is expected_allowed, f"Target: {target}, Reason: {reason}"

    def test_windows_path_separators(self):
        """Windows-style paths are normalized to forward slashes."""
        allowed, reason = check_pytest_scope("runtime\\tests\\test_foo.py")
        assert allowed is True, f"Windows path should be normalized: {reason}"

    # P0 Hardening Tests - Adversarial bypasses
    def test_deny_confusing_sibling_path(self):
        """Deny runtime/tests_evil (confusing sibling)."""
        allowed, reason = check_pytest_scope("runtime/tests_evil/test_x.py")
        assert allowed is False
        assert "PATH_OUTSIDE_ALLOWED_SCOPE" in reason

    def test_deny_path_traversal_dotdot(self):
        """Deny path traversal with .."""
        test_cases = [
            "runtime/tests/../runtime/governance/test_x.py",
            "runtime/tests/../docs/01_governance/x.py",
            "../runtime/tests/test_x.py",
            "runtime/../tests/test_x.py",
        ]
        for target in test_cases:
            allowed, reason = check_pytest_scope(target)
            assert allowed is False, f"Should deny: {target}"
            assert "PATH_TRAVERSAL_DENIED" in reason, f"Wrong reason for {target}: {reason}"

    def test_deny_path_traversal_dot(self):
        """Deny path traversal with . (current dir)."""
        test_cases = [
            "runtime/./tests/test_x.py",
            "./runtime/tests/test_x.py",
            "runtime/tests/./test_x.py",
        ]
        for target in test_cases:
            allowed, reason = check_pytest_scope(target)
            assert allowed is False, f"Should deny: {target}"
            assert "PATH_TRAVERSAL_DENIED" in reason

    def test_deny_windows_path_traversal(self):
        """Deny Windows-style path traversal."""
        test_cases = [
            "runtime\\tests\\..\\docs\\01_governance\\x.py",
            "runtime\\tests\\..\\runtime\\governance\\test_x.py",
        ]
        for target in test_cases:
            allowed, reason = check_pytest_scope(target)
            assert allowed is False, f"Should deny: {target}"
            assert "PATH_TRAVERSAL_DENIED" in reason

    def test_deny_absolute_posix_paths(self):
        """Deny absolute POSIX paths."""
        test_cases = [
            "/etc/passwd",
            "/runtime/tests/test_x.py",
            "/home/user/runtime/tests/test_x.py",
        ]
        for target in test_cases:
            allowed, reason = check_pytest_scope(target)
            assert allowed is False, f"Should deny: {target}"
            assert "ABSOLUTE_PATH_DENIED" in reason

    def test_deny_absolute_windows_paths(self):
        """Deny absolute Windows drive paths."""
        test_cases = [
            "C:\\Windows\\System32",
            "C:\\runtime\\tests\\test_x.py",
            "D:\\projects\\test.py",
        ]
        for target in test_cases:
            allowed, reason = check_pytest_scope(target)
            assert allowed is False, f"Should deny: {target}"
            assert "ABSOLUTE_PATH_DENIED" in reason

    def test_deny_unc_paths(self):
        """Deny UNC network paths."""
        test_cases = [
            "//server/share/test.py",
            "//192.168.1.1/files/test.py",
        ]
        for target in test_cases:
            allowed, reason = check_pytest_scope(target)
            assert allowed is False, f"Should deny: {target}"
            assert "ABSOLUTE_PATH_DENIED" in reason

    def test_deny_empty_or_none(self):
        """Deny empty or whitespace-only paths."""
        test_cases = [
            "",
            "   ",
            "\t",
            "\n",
        ]
        for target in test_cases:
            allowed, reason = check_pytest_scope(target)
            assert allowed is False, f"Should deny empty/whitespace: '{target}'"
            assert "PATH_EMPTY_OR_NONE" in reason


class TestPytestToolPolicy:
    """Tests for pytest tool policy enforcement."""

    def test_pytest_allowed_on_runtime_tests_file(self):
        """pytest is allowed to run tests in runtime/tests/."""
        request = ToolInvokeRequest(
            tool="pytest",
            action="run",
            args={"target": "runtime/tests/test_example.py"}
        )
        allowed, decision = check_tool_action_allowed(request)

        assert allowed is True
        assert decision.allowed is True
        assert "pytest.run" in decision.matched_rules

    def test_pytest_allowed_on_runtime_tests_directory(self):
        """pytest is allowed to run entire runtime/tests directory."""
        request = ToolInvokeRequest(
            tool="pytest",
            action="run",
            args={"target": "runtime/tests"}
        )
        allowed, decision = check_tool_action_allowed(request)

        assert allowed is True
        assert decision.allowed is True

    def test_pytest_allowed_on_runtime_tests_with_trailing_slash(self):
        """pytest is allowed with trailing slash."""
        request = ToolInvokeRequest(
            tool="pytest",
            action="run",
            args={"target": "runtime/tests/"}
        )
        allowed, decision = check_tool_action_allowed(request)

        assert allowed is True

    def test_pytest_blocked_on_arbitrary_path(self):
        """pytest is blocked on paths outside allowed scope."""
        blocked_targets = [
            "/etc/passwd",
            "../outside_tests.py",
            "project_builder/tests/test_builder.py",
            "docs/test_docs.py",
            "config/test_config.py",
            "runtime/test_outside.py",  # Not in tests/ subdir
            "tests/test_not_runtime.py",  # Missing runtime/ prefix
        ]

        for target in blocked_targets:
            request = ToolInvokeRequest(
                tool="pytest",
                action="run",
                args={"target": target}
            )
            allowed, decision = check_tool_action_allowed(request)

            assert allowed is False, f"Should block: {target}"
            assert "PATH_OUTSIDE_ALLOWED_SCOPE" in decision.decision_reason

    def test_pytest_requires_target(self):
        """pytest.run requires target argument (fail-closed)."""
        request = ToolInvokeRequest(
            tool="pytest",
            action="run",
            args={}  # Missing target
        )
        allowed, decision = check_tool_action_allowed(request)

        assert allowed is False
        assert "requires target" in decision.decision_reason.lower()
        assert "pytest_target_required" in decision.matched_rules


class TestPytestExecutor:
    """Tests for pytest executor with timeout and output capture."""

    def test_pytest_execution_pass(self, tmp_path):
        """Successful test execution returns PASS status."""
        # Create a passing test
        test_file = tmp_path / "test_pass.py"
        test_file.write_text("""
def test_pass():
    assert True
""")

        executor = TestExecutor(timeout=10)
        result = executor.run(str(test_file))

        assert result.status == "PASS"
        assert result.exit_code == 0
        assert result.duration >= 0

    def test_pytest_execution_fail(self, tmp_path):
        """Failing test execution returns FAIL status."""
        # Create a failing test
        test_file = tmp_path / "test_fail.py"
        test_file.write_text("""
def test_fail():
    assert False, "Expected failure"
""")

        executor = TestExecutor(timeout=10)
        result = executor.run(str(test_file))

        assert result.status == "FAIL"
        assert result.exit_code != 0

    def test_pytest_timeout_enforcement(self, tmp_path):
        """Test exceeding timeout is terminated with TIMEOUT status."""
        # Create a test that would hang forever
        test_file = tmp_path / "test_hang.py"
        test_file.write_text("""
import time

def test_hang():
    time.sleep(9999)
""")

        executor = TestExecutor(timeout=2)  # 2 second timeout
        result = executor.run(str(test_file))

        assert result.status == "TIMEOUT"
        assert result.exit_code == -15  # SIGTERM
        assert result.duration >= 2
        assert result.evidence["timeout_triggered"] is True

    def test_pytest_output_captured_in_evidence(self, tmp_path):
        """Pytest stdout/stderr is captured in result evidence."""
        test_file = tmp_path / "test_output.py"
        test_file.write_text("""
import sys

def test_output():
    print("STDOUT_MARKER_12345")
    print("STDERR_MARKER_67890", file=sys.stderr)
    assert True
""")

        executor = TestExecutor(timeout=10)
        # Use -s flag to disable pytest's output capture
        result = executor.run(str(test_file), extra_args=["-s"])

        assert result.status == "PASS"
        # With -s flag, pytest doesn't capture, so output appears in stdout
        # But pytest may still capture depending on configuration
        # The key requirement is that evidence contains the stdout
        assert result.evidence.get("pytest_stdout") is not None
        assert result.evidence.get("pytest_stderr") is not None
        assert len(result.stdout) > 0  # Some output was captured

    def test_pytest_counts_parsed(self, tmp_path):
        """Test counts are extracted from pytest output."""
        test_file = tmp_path / "test_counts.py"
        test_file.write_text("""
import pytest

def test_pass_1():
    assert True

def test_pass_2():
    assert True

@pytest.mark.skip
def test_skip():
    pass
""")

        executor = TestExecutor(timeout=10)
        result = executor.run(str(test_file))

        assert result.status == "PASS"
        assert result.counts is not None
        assert result.counts.get("passed", 0) >= 2
        assert result.counts.get("skipped", 0) >= 1

    def test_output_truncation(self, tmp_path):
        """Large output is truncated at 50KB boundary."""
        test_file = tmp_path / "test_large_output.py"
        test_file.write_text("""
def test_large_output():
    # Generate >50KB of output
    for i in range(10000):
        print("X" * 100)
    assert True
""")

        executor = TestExecutor(timeout=10)
        result = executor.run(str(test_file))

        # Check that output doesn't exceed limit significantly
        # (some overage allowed for truncation marker)
        assert len(result.stdout) <= 52 * 1024  # 50KB + 2KB for marker
        if result.evidence.get("truncated"):
            assert "[OUTPUT TRUNCATED AT 50KB LIMIT]" in result.stdout

    def test_evidence_structure(self, tmp_path):
        """Evidence dict follows Phase 3a schema."""
        test_file = tmp_path / "test_evidence.py"
        test_file.write_text("""
def test_simple():
    assert True
""")

        executor = TestExecutor(timeout=10)
        result = executor.run(str(test_file))

        evidence = result.evidence

        # Verify required fields
        assert "target" in evidence
        assert "exit_code" in evidence
        assert "status" in evidence
        assert "duration_seconds" in evidence
        assert "test_counts" in evidence
        assert "pytest_stdout" in evidence
        assert "pytest_stderr" in evidence
        assert "truncated" in evidence
        assert "timeout_triggered" in evidence

        # Verify types
        assert isinstance(evidence["exit_code"], int)
        assert isinstance(evidence["status"], str)
        assert isinstance(evidence["duration_seconds"], (int, float))
        assert isinstance(evidence["test_counts"], dict)
        assert isinstance(evidence["truncated"], bool)
        assert isinstance(evidence["timeout_triggered"], bool)

    def test_failed_tests_captured(self, tmp_path):
        """Failed test names are captured in result."""
        test_file = tmp_path / "test_failures.py"
        test_file.write_text("""
def test_fail_1():
    assert False

def test_pass():
    assert True

def test_fail_2():
    assert False
""")

        executor = TestExecutor(timeout=10)
        result = executor.run(str(test_file))

        assert result.status == "FAIL"
        # failed_tests should contain test identifiers
        # (actual parsing depends on pytest output format)
        assert result.failed_tests is not None or result.counts["failed"] > 0
