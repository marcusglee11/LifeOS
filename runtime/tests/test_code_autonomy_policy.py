"""
Tests for code autonomy policy (Phase 4D).

Coverage:
- Path validation (allowed vs protected)
- Diff budget enforcement
- Syntax validation integration
- Protected paths blocking
- Self-modification protection
"""

import pytest
from runtime.governance.tool_policy import check_code_autonomy_policy
from runtime.governance.protected_paths import (
    validate_write_path,
    validate_diff_budget,
    is_path_protected,
    is_path_in_allowed_scope,
    MAX_DIFF_LINES,
)
from runtime.tools.schemas import ToolInvokeRequest


# =============================================================================
# Path Validation Tests
# =============================================================================

class TestPathValidation:
    """Tests for path validation against allowed/protected lists."""

    def test_allowed_path_runtime(self):
        """Verify runtime/ is in allowed scope."""
        allowed, reason = is_path_in_allowed_scope("runtime/new_module.py")
        assert allowed is True
        assert "runtime/" in reason

    def test_allowed_path_coo(self):
        """Verify coo/ is in allowed scope."""
        allowed, reason = is_path_in_allowed_scope("coo/utils/helper.py")
        assert allowed is True
        assert "coo/" in reason

    def test_allowed_path_tests(self):
        """Verify tests/ is in allowed scope."""
        allowed, reason = is_path_in_allowed_scope("tests/test_new.py")
        assert allowed is True
        assert "tests/" in reason

    def test_allowed_path_tests_doc(self):
        """Verify tests_doc/ is in allowed scope."""
        allowed, reason = is_path_in_allowed_scope("tests_doc/test_doc.py")
        assert allowed is True

    def test_allowed_path_tests_recursive(self):
        """Verify tests_recursive/ is in allowed scope."""
        allowed, reason = is_path_in_allowed_scope("tests_recursive/test_r.py")
        assert allowed is True

    def test_blocked_path_outside_scope(self):
        """Verify paths outside allowed scope are blocked."""
        allowed, reason = is_path_in_allowed_scope("random/file.py")
        assert allowed is False
        assert "PATH_OUTSIDE_ALLOWED_SCOPE" in reason


class TestProtectedPaths:
    """Tests for protected path blocking."""

    def test_protected_governance_foundations(self):
        """Verify docs/00_foundations/ is protected."""
        protected, reason = is_path_protected("docs/00_foundations/test.md")
        assert protected is True
        assert "GOVERNANCE_FOUNDATION" in reason

    def test_protected_governance_rulings(self):
        """Verify docs/01_governance/ is protected."""
        protected, reason = is_path_protected("docs/01_governance/ruling.md")
        assert protected is True
        assert "GOVERNANCE_RULINGS" in reason

    def test_protected_config_governance(self):
        """Verify config/governance/ is protected."""
        protected, reason = is_path_protected("config/governance/baseline.yaml")
        assert protected is True
        assert "GOVERNANCE_CONFIG" in reason

    def test_protected_self_mod_protection_file(self):
        """Verify self_mod_protection.py is protected."""
        protected, reason = is_path_protected(
            "runtime/governance/self_mod_protection.py"
        )
        assert protected is True
        assert "SELF_MOD_PROTECTION" in reason

    def test_protected_envelope_enforcer(self):
        """Verify envelope_enforcer.py is protected."""
        protected, reason = is_path_protected(
            "runtime/governance/envelope_enforcer.py"
        )
        assert protected is True
        assert "ENVELOPE_ENFORCER" in reason

    def test_protected_tool_policy(self):
        """Verify tool_policy.py is protected."""
        protected, reason = is_path_protected(
            "runtime/governance/tool_policy.py"
        )
        assert protected is True
        assert "TOOL_POLICY_GATE" in reason

    def test_protected_agent_instructions(self):
        """Verify CLAUDE.md is protected."""
        protected, reason = is_path_protected("CLAUDE.md")
        assert protected is True
        assert "AGENT_INSTRUCTIONS" in reason

    def test_not_protected_regular_file(self):
        """Verify regular files are not protected."""
        protected, reason = is_path_protected("runtime/cli.py")
        assert protected is False
        assert reason is None


class TestWritePathValidation:
    """Tests for combined write path validation."""

    def test_write_allowed_runtime_file(self):
        """Verify write allowed to runtime/ files."""
        allowed, reason = validate_write_path("runtime/utils/new.py")
        assert allowed is True
        assert reason == "ALLOWED"

    def test_write_allowed_coo_file(self):
        """Verify write allowed to coo/ files."""
        allowed, reason = validate_write_path("coo/helper.py")
        assert allowed is True
        assert reason == "ALLOWED"

    def test_write_blocked_protected_governance(self):
        """Verify write blocked to governance paths."""
        allowed, reason = validate_write_path("docs/01_governance/test.md")
        assert allowed is False
        assert "PROTECTED" in reason
        assert "GOVERNANCE_RULINGS" in reason

    def test_write_blocked_self_modification(self):
        """Verify write blocked to self-mod protection files."""
        allowed, reason = validate_write_path(
            "runtime/governance/self_mod_protection.py"
        )
        assert allowed is False
        assert "PROTECTED" in reason
        assert "SELF_MOD_PROTECTION" in reason

    def test_write_blocked_outside_scope(self):
        """Verify write blocked outside allowed scope."""
        allowed, reason = validate_write_path("config/random.yaml")
        assert allowed is False
        assert "PATH_OUTSIDE_ALLOWED_SCOPE" in reason

    def test_protected_takes_precedence(self):
        """Verify protected check takes precedence over allowed scope.

        Even though runtime/ is allowed, specific files within it can be protected.
        """
        # This file is in runtime/ (allowed) but explicitly protected
        allowed, reason = validate_write_path(
            "runtime/governance/envelope_enforcer.py"
        )
        assert allowed is False
        assert "PROTECTED" in reason


# =============================================================================
# Diff Budget Tests
# =============================================================================

class TestDiffBudget:
    """Tests for diff budget validation."""

    def test_diff_within_budget_small(self):
        """Verify small diffs pass."""
        within_budget, reason = validate_diff_budget(50)
        assert within_budget is True
        assert "50" in reason and str(MAX_DIFF_LINES) in reason

    def test_diff_within_budget_at_limit(self):
        """Verify diff exactly at limit passes."""
        within_budget, reason = validate_diff_budget(MAX_DIFF_LINES)
        assert within_budget is True

    def test_diff_exceeds_budget(self):
        """Verify large diffs are blocked."""
        within_budget, reason = validate_diff_budget(500)
        assert within_budget is False
        assert "DIFF_BUDGET_EXCEEDED" in reason
        assert "500" in reason

    def test_diff_budget_zero(self):
        """Verify zero-line diff passes."""
        within_budget, reason = validate_diff_budget(0)
        assert within_budget is True


# =============================================================================
# Code Autonomy Policy Integration Tests
# =============================================================================

class TestCodeAutonomyPolicy:
    """Tests for the integrated code autonomy policy check."""

    def test_write_allowed_runtime_with_valid_syntax(self):
        """Verify write to runtime/ with valid Python passes all checks."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/new_module.py",
                "content": "def foo(): pass\n"
            }
        )

        allowed, decision = check_code_autonomy_policy(request, diff_lines=1)

        assert allowed is True
        assert decision.allowed is True
        assert "code_autonomy_allowed" in decision.matched_rules

    def test_write_allowed_coo_with_valid_syntax(self):
        """Verify write to coo/ with valid Python passes."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "coo/utils/helper.py",
                "content": "x = 1\n"
            }
        )

        allowed, decision = check_code_autonomy_policy(request, diff_lines=1)

        assert allowed is True
        assert decision.allowed is True

    def test_write_blocked_governance_path(self):
        """Verify write to governance path is blocked."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "docs/01_governance/test.md",
                "content": "# test"
            }
        )

        allowed, decision = check_code_autonomy_policy(request)

        assert allowed is False
        assert decision.allowed is False
        assert "PROTECTED" in decision.decision_reason
        assert "code_autonomy_path_violation" in decision.matched_rules

    def test_write_blocked_self_modification(self):
        """Verify write to self-mod protection file is blocked."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/governance/self_mod_protection.py",
                "content": "# hack attempt"
            }
        )

        allowed, decision = check_code_autonomy_policy(request)

        assert allowed is False
        assert decision.allowed is False
        assert "PROTECTED" in decision.decision_reason
        assert "SELF_MOD_PROTECTION" in decision.decision_reason

    def test_write_blocked_diff_budget_exceeded(self):
        """Verify large diffs are blocked."""
        large_content = "x = 1\n" * 400  # 400 lines
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/big.py",
                "content": large_content
            }
        )

        allowed, decision = check_code_autonomy_policy(request, diff_lines=400)

        assert allowed is False
        assert decision.allowed is False
        assert "DIFF_BUDGET_EXCEEDED" in decision.decision_reason
        assert "code_autonomy_diff_budget_exceeded" in decision.matched_rules

    def test_write_blocked_syntax_error(self):
        """Verify syntax errors block writes."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/bad.py",
                "content": "def broken("
            }
        )

        # v1.1: diff_lines required
        allowed, decision = check_code_autonomy_policy(request, diff_lines=1)

        assert allowed is False
        assert decision.allowed is False
        assert "SYNTAX_VALIDATION_FAILED" in decision.decision_reason
        assert "code_autonomy_syntax_invalid" in decision.matched_rules

    def test_write_yaml_with_syntax_validation(self):
        """Verify YAML files are syntax-validated."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/config.yaml",
                "content": "key: value\nlist:\n  - item"
            }
        )

        allowed, decision = check_code_autonomy_policy(request, diff_lines=3)

        assert allowed is True
        assert decision.allowed is True

    def test_write_json_with_syntax_validation(self):
        """Verify JSON files are syntax-validated."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/data.json",
                "content": '{"key": "value"}'
            }
        )

        allowed, decision = check_code_autonomy_policy(request, diff_lines=1)

        assert allowed is True
        assert decision.allowed is True

    def test_write_invalid_json_blocked(self):
        """Verify invalid JSON is blocked."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/bad.json",
                "content": '{"key": value}'  # Missing quotes
            }
        )

        # v1.1: diff_lines required
        allowed, decision = check_code_autonomy_policy(request, diff_lines=1)

        assert allowed is False
        assert "SYNTAX_VALIDATION_FAILED" in decision.decision_reason

    def test_non_write_operation_passes_through(self):
        """Verify non-write operations are not affected."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="read_file",
            args={"path": "runtime/module.py"}
        )

        allowed, decision = check_code_autonomy_policy(request)

        assert allowed is True
        assert decision.allowed is True
        assert "code_autonomy_not_applicable" in decision.matched_rules

    def test_write_without_path_blocked(self):
        """Verify write without path is blocked (fail-closed)."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={"content": "test"}
        )

        allowed, decision = check_code_autonomy_policy(request)

        assert allowed is False
        assert "requires path" in decision.decision_reason

    def test_diff_budget_none_denied(self):
        """Verify diff budget is required (v1.1: fail-closed)."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/test.py",
                "content": "x = 1\n"
            }
        )

        # v1.1: diff_lines is REQUIRED, None is denied (fail-closed)
        allowed, decision = check_code_autonomy_policy(request, diff_lines=None)

        assert allowed is False
        assert "DIFF_BUDGET_UNKNOWN" in decision.decision_reason


# =============================================================================
# Edge Cases and Cross-Platform Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and cross-platform compatibility."""

    def test_windows_path_separators(self):
        """Verify Windows-style path separators are normalized."""
        allowed, reason = validate_write_path("runtime\\utils\\new.py")
        assert allowed is True

        protected, _ = is_path_protected("docs\\01_governance\\test.md")
        assert protected is True

    def test_path_with_multiple_slashes(self):
        """Verify paths with multiple slashes work correctly."""
        allowed, reason = is_path_in_allowed_scope("runtime/utils/deep/module.py")
        assert allowed is True

    def test_path_case_sensitivity(self):
        """Document path case sensitivity behavior."""
        # On Linux, paths are case-sensitive
        # This test documents current behavior
        allowed, reason = validate_write_path("Runtime/test.py")
        # This will be blocked because "Runtime/" != "runtime/"
        # This is correct behavior - we want exact matches
        assert allowed is False
