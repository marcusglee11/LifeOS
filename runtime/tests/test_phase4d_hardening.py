"""
Phase 4D Hardening Tests - Bypass seam closure verification.

Tests the hardening fixes for Phase 4D code autonomy:
- P0.1: Path normalization and escape prevention
- P0.2: Diff budget fail-closed
- P0.3: Empty content validation
- P0.4: Enforcement surface protection
- P1.1: Unknown mutator fail-closed
"""

import pytest
from runtime.governance.tool_policy import check_code_autonomy_policy
from runtime.governance.protected_paths import (
    normalize_rel_path,
    validate_write_path,
    is_path_protected,
    is_path_in_allowed_scope,
)
from runtime.tools.schemas import ToolInvokeRequest


# =============================================================================
# P0.1: Path Normalization and Escape Prevention
# =============================================================================

class TestPathNormalization:
    """Tests for canonical path normalization (P0.1)."""

    def test_normalize_valid_relative_path(self):
        """Valid relative paths are normalized."""
        ok, normalized, reason = normalize_rel_path("runtime/utils/helper.py")
        assert ok is True
        assert normalized == "runtime/utils/helper.py"
        assert reason == ""

    def test_normalize_backslashes(self):
        """Backslashes are converted to forward slashes."""
        ok, normalized, reason = normalize_rel_path("runtime\\utils\\helper.py")
        assert ok is True
        assert normalized == "runtime/utils/helper.py"

    def test_normalize_dot_segments(self):
        """Dot segments are collapsed."""
        ok, normalized, reason = normalize_rel_path("runtime/./utils/./helper.py")
        assert ok is True
        assert normalized == "runtime/utils/helper.py"

    def test_normalize_dot_dot_within_path(self):
        """Parent directory references within path are collapsed."""
        ok, normalized, reason = normalize_rel_path("runtime/foo/../utils/helper.py")
        assert ok is True
        assert normalized == "runtime/utils/helper.py"

    def test_reject_absolute_posix_path(self):
        """Absolute POSIX paths are rejected."""
        ok, normalized, reason = normalize_rel_path("/etc/passwd")
        assert ok is False
        assert "ABSOLUTE_PATH_DENIED" in reason
        assert "POSIX" in reason

    def test_reject_windows_drive_path_colon(self):
        """Windows drive paths (C:/) are rejected."""
        ok, normalized, reason = normalize_rel_path("C:/Windows/System32")
        assert ok is False
        assert "ABSOLUTE_PATH_DENIED" in reason
        assert "Windows drive" in reason

    def test_reject_windows_drive_path_backslash(self):
        """Windows drive paths (C:\\) are rejected."""
        ok, normalized, reason = normalize_rel_path("C:\\Windows\\System32")
        assert ok is False
        assert "ABSOLUTE_PATH_DENIED" in reason

    def test_reject_unc_path_forward_slash(self):
        """UNC paths (//server/share) are rejected."""
        ok, normalized, reason = normalize_rel_path("//server/share/file.txt")
        assert ok is False
        assert "ABSOLUTE_PATH_DENIED" in reason
        # May be caught as UNC or POSIX (both start with //)
        assert "UNC" in reason or "POSIX" in reason

    def test_reject_unc_path_backslash(self):
        """UNC paths (\\\\server\\share) are rejected."""
        ok, normalized, reason = normalize_rel_path("\\\\server\\share\\file.txt")
        assert ok is False
        assert "ABSOLUTE_PATH_DENIED" in reason

    def test_reject_path_escaping_root(self):
        """Paths that escape root via .. are rejected."""
        ok, normalized, reason = normalize_rel_path("../../../etc/passwd")
        assert ok is False
        assert "PATH_TRAVERSAL_DENIED" in reason
        assert "escapes root" in reason

    def test_reject_path_escaping_from_subdir(self):
        """Paths that escape from subdirectory are rejected."""
        ok, normalized, reason = normalize_rel_path("runtime/../../etc/passwd")
        assert ok is False
        assert "PATH_TRAVERSAL_DENIED" in reason

    def test_reject_null_byte(self):
        """Paths with null bytes are rejected."""
        ok, normalized, reason = normalize_rel_path("runtime/file\x00.py")
        assert ok is False
        assert "NULL_BYTE" in reason

    def test_reject_current_dir_as_path(self):
        """Standalone '.' is rejected as ambiguous."""
        ok, normalized, reason = normalize_rel_path(".")
        assert ok is False
        assert "PATH_IS_CURRENT_DIR" in reason


class TestPathTraversalDenial:
    """Tests for path traversal attack prevention."""

    def test_write_blocked_for_governance_traversal(self):
        """Path traversal to governance paths is blocked."""
        # Try to write to governance via traversal
        # This normalizes to docs/01_governance/test.md and is caught as PROTECTED
        allowed, reason = validate_write_path("runtime/../docs/01_governance/test.md")
        assert allowed is False
        # Should be caught either as invalid path, traversal, or protected
        assert any(x in reason for x in ["INVALID_PATH", "PATH_TRAVERSAL", "PROTECTED", "GOVERNANCE"])

    def test_write_blocked_for_deep_traversal(self):
        """Deep path traversal is blocked."""
        allowed, reason = validate_write_path("runtime/foo/../../etc/passwd")
        assert allowed is False
        # Should be caught by path normalization
        assert "INVALID_PATH" in reason or "PATH_TRAVERSAL" in reason or "OUTSIDE" in reason

    def test_protected_path_check_uses_normalized_paths(self):
        """Protected path checks use normalized paths."""
        # Try various traversal attempts
        protected, reason = is_path_protected("runtime/governance/../governance/tool_policy.py")
        assert protected is True  # Should normalize and detect protection

    def test_allowed_scope_check_uses_normalized_paths(self):
        """Allowed scope checks use normalized paths."""
        # Path that looks like it's in runtime/ but actually escapes
        allowed, reason = is_path_in_allowed_scope("runtime/../../docs/test.md")
        assert allowed is False  # Should detect escape via normalization


class TestAbsolutePathDenial:
    """Tests for absolute path attack prevention."""

    def test_absolute_unix_path_blocked(self):
        """Absolute UNIX paths are blocked."""
        allowed, reason = validate_write_path("/etc/passwd")
        assert allowed is False
        assert "ABSOLUTE" in reason or "INVALID" in reason

    def test_absolute_windows_path_blocked(self):
        """Absolute Windows paths are blocked."""
        allowed, reason = validate_write_path("C:/Windows/System32/evil.dll")
        assert allowed is False
        assert "ABSOLUTE" in reason or "INVALID" in reason or "Windows" in reason

    def test_unc_path_blocked(self):
        """UNC paths are blocked."""
        allowed, reason = validate_write_path("//server/share/file.txt")
        assert allowed is False
        assert "UNC" in reason or "ABSOLUTE" in reason or "INVALID" in reason


# =============================================================================
# P0.2: Diff Budget Fail-Closed
# =============================================================================

class TestDiffBudgetFailClosed:
    """Tests for diff budget requirement (P0.2)."""

    def test_missing_diff_lines_denied(self):
        """Write with missing diff_lines is denied."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/test.py",
                "content": "x = 1\n"
            }
        )

        # Call with diff_lines=None (explicitly)
        allowed, decision = check_code_autonomy_policy(request, diff_lines=None)

        assert allowed is False
        assert "DIFF_BUDGET_UNKNOWN" in decision.decision_reason
        assert "diff_lines required" in decision.decision_reason

    def test_diff_lines_zero_allowed(self):
        """Write with diff_lines=0 is allowed (no changes)."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/test.py",
                "content": "x = 1\n"
            }
        )

        allowed, decision = check_code_autonomy_policy(request, diff_lines=0)

        # Should pass diff budget check but may fail syntax validation
        # depending on content
        if not allowed:
            # If denied, should be for syntax, not diff budget
            assert "DIFF_BUDGET" not in decision.decision_reason

    def test_diff_lines_within_budget(self):
        """Write within diff budget passes budget check."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/test.py",
                "content": "x = 1\n"
            }
        )

        allowed, decision = check_code_autonomy_policy(request, diff_lines=100)

        # Should pass diff budget check
        if not allowed:
            assert "DIFF_BUDGET_EXCEEDED" not in decision.decision_reason


# =============================================================================
# P0.3: Empty Content Validation
# =============================================================================

class TestEmptyContentValidation:
    """Tests for empty content validation (P0.3)."""

    def test_empty_string_python_valid(self):
        """Empty Python file is valid (ast.parse('') succeeds)."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/empty.py",
                "content": ""
            }
        )

        allowed, decision = check_code_autonomy_policy(request, diff_lines=1)

        # Empty Python is valid
        assert allowed is True

    def test_empty_string_json_invalid(self):
        """Empty JSON file is invalid (json.loads('') fails)."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/empty.json",
                "content": ""
            }
        )

        allowed, decision = check_code_autonomy_policy(request, diff_lines=1)

        # Empty JSON is invalid
        assert allowed is False
        assert "SYNTAX_VALIDATION_FAILED" in decision.decision_reason


# =============================================================================
# P0.4: Enforcement Surface Protection
# =============================================================================

class TestEnforcementSurfaceProtection:
    """Tests for protection of enforcement modules (P0.4)."""

    def test_syntax_validator_protected(self):
        """syntax_validator.py cannot be modified."""
        protected, reason = is_path_protected("runtime/governance/syntax_validator.py")
        assert protected is True
        assert "SYNTAX_VALIDATOR" in reason or "PROTECTED" in reason

    def test_write_to_syntax_validator_denied(self):
        """Writes to syntax_validator.py are denied."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/governance/syntax_validator.py",
                "content": "# malicious code"
            }
        )

        allowed, decision = check_code_autonomy_policy(request, diff_lines=1)

        assert allowed is False
        assert "PROTECTED" in decision.decision_reason
        assert "SYNTAX_VALIDATOR" in decision.decision_reason

    def test_other_governance_files_protected(self):
        """Other governance enforcement files remain protected."""
        protected_files = [
            "runtime/governance/tool_policy.py",
            "runtime/governance/protected_paths.py",
            "runtime/governance/envelope_enforcer.py",
            "runtime/governance/self_mod_protection.py",
        ]

        for file_path in protected_files:
            protected, reason = is_path_protected(file_path)
            assert protected is True, f"{file_path} should be protected"


# =============================================================================
# P1.1: Unknown Mutator Fail-Closed
# =============================================================================

class TestUnknownMutatorFailClosed:
    """Tests for unknown mutator detection (P1.1)."""

    def test_known_mutator_write_file_processed(self):
        """Known mutator write_file is processed by policy."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "runtime/test.py",
                "content": "x = 1"
            }
        )

        allowed, decision = check_code_autonomy_policy(request, diff_lines=1)

        # Should be processed (not return "not applicable")
        assert "not_applicable" not in decision.matched_rules

    def test_unknown_mutator_denied(self):
        """Unknown filesystem mutator is denied (fail-closed)."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="delete_file",  # Not in KNOWN_FILESYSTEM_MUTATORS
            args={
                "path": "runtime/test.py"
            }
        )

        allowed, decision = check_code_autonomy_policy(request, diff_lines=1)

        assert allowed is False
        assert "Unknown filesystem mutator" in decision.decision_reason
        assert "fail-closed" in decision.decision_reason

    def test_read_operations_pass_through(self):
        """Read operations (non-mutators) pass through."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="read_file",
            args={
                "path": "runtime/test.py"
            }
        )

        allowed, decision = check_code_autonomy_policy(request)

        assert allowed is True
        assert "not_applicable" in decision.matched_rules or "Not a mutator" in decision.decision_reason


# =============================================================================
# Integration: Multiple Bypass Attempts
# =============================================================================

class TestMultipleBypassAttempts:
    """Tests combining multiple bypass techniques."""

    def test_traversal_to_protected_with_backslashes(self):
        """Path traversal with backslashes to protected paths blocked."""
        allowed, reason = validate_write_path("runtime\\..\\docs\\01_governance\\evil.md")
        assert allowed is False

    def test_absolute_path_to_allowed_location(self):
        """Even absolute paths to allowed locations are blocked."""
        # Try to use absolute path to bypass relative path checks
        allowed, reason = validate_write_path("/workspace/runtime/test.py")
        assert allowed is False
        assert "ABSOLUTE" in reason or "INVALID" in reason

    def test_null_byte_injection(self):
        """Null byte injection is blocked."""
        allowed, reason = validate_write_path("runtime/test\x00.py")
        assert allowed is False
        assert "NULL_BYTE" in reason or "INVALID" in reason
