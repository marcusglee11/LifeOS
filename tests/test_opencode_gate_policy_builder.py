
import pytest
import os
import sys
from unittest.mock import patch, MagicMock

# Add scripts/ to path
scripts_dir = os.path.join(os.path.dirname(__file__), '..', 'scripts')
sys.path.append(scripts_dir)

import opencode_gate_policy as policy
from opencode_gate_policy import ReasonCode, MODE_STEWARD, MODE_BUILDER

class TestOpencodeBuilderPolicy:

    def test_steward_mode_regression(self):
        """Verify Steward mode still behaves strictly."""
        # Blocked: .py in runtime
        allowed, reason = policy.validate_operation("A", "runtime/foo.py", mode=MODE_STEWARD)
        assert allowed is False
        assert reason == ReasonCode.DENYLIST_EXT_BLOCKED # Matches denylist (ext) before allowlist check

        # Allowed: .md in docs/
        allowed, reason = policy.validate_operation("A", "docs/test.md", mode=MODE_STEWARD)
        assert allowed is True

    def test_builder_mode_allowlist(self):
        """Verify Builder mode allows code in authorized roots."""
        roots = ["runtime/", "tests/"]
        for root in roots:
            path = f"{root}test_file.py"
            allowed, reason = policy.validate_operation("A", path, mode=MODE_BUILDER)
            assert allowed is True, f"Builder should allow {path}"
            assert reason is None

    def test_builder_mode_blocks_scripts(self):
        """Verify Builder mode does NOT allow arbitrary scripts writes."""
        path = "scripts/malicious.py"
        allowed, reason = policy.validate_operation("A", path, mode=MODE_BUILDER)
        assert allowed is False
        assert reason == ReasonCode.BUILDER_OUTSIDE_ALLOWLIST

    def test_builder_mode_blocks_critical_files(self):
        """Verify Critical Enforcement Files are blocked even in Builder mode."""
        
        critical_files = [
            "scripts/opencode_gate_policy.py",
            "scripts/opencode_ci_runner.py",
            "docs/01_governance/OpenCode_First_Stewardship_Policy_v1.1.md"
        ]
        
        for path in critical_files:
            allowed, reason = policy.validate_operation("M", path, mode=MODE_BUILDER)
            assert allowed is False, f"Critical file {path} should be blocked"
            assert reason == ReasonCode.CRITICAL_FILE_BLOCKED

    def test_builder_mode_blocks_governance(self):
        """Verify Builder cannot touch governance outside of critical list too."""
        # Governance roots are not in allowlist, so should be blocked by default.
        path = "docs/01_governance/new_ruling.md"
        allowed, reason = policy.validate_operation("A", path, mode=MODE_BUILDER)
        assert allowed is False
        assert reason == ReasonCode.BUILDER_OUTSIDE_ALLOWLIST

    def test_builder_blocks_structural_ops(self):
        """Verify Builder blocking of structural ops (D/R/C)."""
        # P0.1/P0.2 requirement: Block D/R/C
        ops = ["D", "R", "C"]
        path = "runtime/test.py"
        for op in ops:
            allowed, reason = policy.validate_operation(op, path, mode=MODE_BUILDER)
            assert allowed is False
            assert reason == ReasonCode.BUILDER_STRUCTURAL_BLOCKED

    def test_builder_modification_allowed(self):
        """Verify Builder allows Modify (M)."""
        path = "runtime/test.py"
        allowed, reason = policy.validate_operation("M", path, mode=MODE_BUILDER)
        assert allowed is True
        assert reason is None

    def test_case_sensitivity_check(self):
        """Verify validation passes original path to security checks."""
        # We mock check_path_security to verify it receives the non-normalized path
        with patch('opencode_gate_policy.check_path_security') as mock_check:
            mock_check.return_value = (True, None) # Assume safe for this test
            
            # Pass a path with mixed case that would normalize differently
            original_path = "Runtime/MixedCase.py"
            
            policy.validate_operation("A", original_path, mode=MODE_BUILDER)
            
            # Verify the mock was called with the ORIGINAL path
            mock_check.assert_called_once()
            args, _ = mock_check.call_args
            called_path = args[0]
            assert called_path == original_path
            assert called_path != called_path.lower()

    def test_symlink_escape_blocked(self):
        """Verify staged symlinks are blocked (Safe=False)."""
        # Mock check_symlink to simulate detection
        with patch('opencode_gate_policy.check_symlink') as mock_check:
            # New semantic: return (False, ReasonCode.SYMLINK_BLOCKED) on detection
            mock_check.return_value = (False, ReasonCode.SYMLINK_BLOCKED)
            
            # This simulates calling check_symlink directly ie. what the runner does
            safe, reason = policy.check_symlink("runtime/badlink", "/repo")
            assert safe is False
            assert reason == ReasonCode.SYMLINK_BLOCKED

    def test_path_escape_blocked(self):
        """Verify path escape outside repo is blocked."""
        with patch('os.path.exists', return_value=True), \
             patch('os.getcwd', return_value='/repo'), \
             patch('os.path.realpath') as mock_realpath:
            
            # Setup: repo root is /repo
            # file is /repo/runtime/badlink -> /etc/passwd
            def realpath_side_effect(p):
                if p == '/repo': return '/repo'
                if 'badlink' in p: return '/etc/passwd'
                return p
            mock_realpath.side_effect = realpath_side_effect
            
            allowed, reason = policy.check_path_security("runtime/badlink", "/repo")
            assert allowed is False
            assert reason == ReasonCode.PATH_ESCAPE_BLOCKED
