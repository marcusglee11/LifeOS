"""
Tests for Tool Policy Gate.

Per Plan_Tool_Invoke_MVP_v0.2:
- Allowed tool/action combinations
- Denied unknown tools/actions
- GovernanceUnavailable when sandbox root missing/invalid/symlink
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch

from runtime.governance.tool_policy import (
    resolve_sandbox_root,
    check_tool_action_allowed,
    is_tool_allowed,
    is_action_allowed,
    get_allowed_tools,
    get_allowed_actions,
    GovernanceUnavailable,
    ALLOWED_ACTIONS,
    clear_workspace_cache,
)
from runtime.tools.schemas import ToolInvokeRequest


class TestAllowedToolsActions:
    """Tests for allowlist validation."""
    
    def test_allowed_tool_filesystem(self):
        """filesystem tool is allowed."""
        assert is_tool_allowed("filesystem")
    
    def test_allowed_tool_pytest(self):
        """pytest tool is allowed."""
        assert is_tool_allowed("pytest")
    
    def test_denied_unknown_tool(self):
        """Unknown tool is denied."""
        assert not is_tool_allowed("unknown_tool")
        assert not is_tool_allowed("git")  # Explicitly out of scope
    
    def test_allowed_filesystem_read_file(self):
        """filesystem.read_file is allowed."""
        assert is_action_allowed("filesystem", "read_file")
    
    def test_allowed_filesystem_write_file(self):
        """filesystem.write_file is allowed."""
        assert is_action_allowed("filesystem", "write_file")
    
    def test_allowed_filesystem_list_dir(self):
        """filesystem.list_dir is allowed."""
        assert is_action_allowed("filesystem", "list_dir")
    
    def test_allowed_pytest_run(self):
        """pytest.run is allowed."""
        assert is_action_allowed("pytest", "run")
    
    def test_denied_unknown_action(self):
        """Unknown action on known tool is denied."""
        assert not is_action_allowed("filesystem", "delete")
        assert not is_action_allowed("filesystem", "execute")
        assert not is_action_allowed("pytest", "watch")
    
    def test_denied_action_on_unknown_tool(self):
        """Any action on unknown tool is denied."""
        assert not is_action_allowed("git", "commit")
        assert not is_action_allowed("unknown", "anything")


class TestCheckToolActionAllowed:
    """Tests for policy decision generation."""
    
    def test_allowed_returns_true_and_allowed_decision(self):
        """Allowed tool/action returns True and ALLOWED decision."""
        # P0.4: filesystem operations now require path in args
        # Use relative path which will be resolved against workspace
        request = ToolInvokeRequest(tool="filesystem", action="read_file", args={"path": "README.md"})
        allowed, decision = check_tool_action_allowed(request)
        
        assert allowed is True
        assert decision.allowed is True
        assert "ALLOWED" in decision.decision_reason
        assert decision.matched_rules == ["filesystem.read_file"]
    
    def test_denied_unknown_tool_returns_false(self):
        """Unknown tool returns False and DENIED decision."""
        request = ToolInvokeRequest(tool="unknown", action="anything")
        allowed, decision = check_tool_action_allowed(request)
        
        assert allowed is False
        assert decision.allowed is False
        assert "DENIED" in decision.decision_reason
        assert "unknown" in decision.decision_reason.lower() or "Unknown" in decision.decision_reason
    
    def test_denied_unknown_action_returns_false(self):
        """Unknown action on known tool returns False."""
        request = ToolInvokeRequest(tool="filesystem", action="delete")
        allowed, decision = check_tool_action_allowed(request)
        
        assert allowed is False
        assert decision.allowed is False
        assert "DENIED" in decision.decision_reason


class TestSandboxRootResolution:
    """Tests for sandbox root resolution with fail-closed semantics."""

    def setup_method(self):
        """Clear workspace cache before each test."""
        clear_workspace_cache()

    def test_missing_env_var_raises_governance_unavailable(self):
        """Missing LIFEOS_SANDBOX_ROOT raises GovernanceUnavailable."""
        with patch.dict(os.environ, {}, clear=True):
            # Ensure env var is not set
            if "LIFEOS_SANDBOX_ROOT" in os.environ:
                del os.environ["LIFEOS_SANDBOX_ROOT"]
            
            with pytest.raises(GovernanceUnavailable) as exc_info:
                resolve_sandbox_root()
            
            assert "not set" in str(exc_info.value).lower()
    
    def test_nonexistent_path_raises_governance_unavailable(self):
        """Non-existent path raises GovernanceUnavailable."""
        with patch.dict(os.environ, {"LIFEOS_SANDBOX_ROOT": "/nonexistent/path/xyz123"}):
            with pytest.raises(GovernanceUnavailable) as exc_info:
                resolve_sandbox_root()
            
            assert "does not exist" in str(exc_info.value).lower()
    
    def test_file_not_directory_raises_governance_unavailable(self, tmp_path):
        """File path (not directory) raises GovernanceUnavailable."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        
        with patch.dict(os.environ, {"LIFEOS_SANDBOX_ROOT": str(file_path)}):
            with pytest.raises(GovernanceUnavailable) as exc_info:
                resolve_sandbox_root()
            
            assert "not a directory" in str(exc_info.value).lower()
    
    def test_valid_directory_returns_canonical_path(self, tmp_path):
        """Valid directory returns canonical Path."""
        with patch.dict(os.environ, {"LIFEOS_SANDBOX_ROOT": str(tmp_path)}):
            result = resolve_sandbox_root()
            
            assert result.exists()
            assert result.is_dir()
            assert result == tmp_path.resolve()
    
    def test_symlink_root_raises_governance_unavailable(self, tmp_path):
        """Symlink as sandbox root raises GovernanceUnavailable (root symlink denied)."""
        real_dir = tmp_path / "real"
        real_dir.mkdir()
        symlink = tmp_path / "link"
        
        try:
            symlink.symlink_to(real_dir)
        except OSError:
            pytest.skip("Symlinks not supported on this platform")
        
        with patch.dict(os.environ, {"LIFEOS_SANDBOX_ROOT": str(symlink)}):
            with pytest.raises(GovernanceUnavailable) as exc_info:
                resolve_sandbox_root()
            
            assert "symlink" in str(exc_info.value).lower()


class TestDeterminism:
    """Tests for deterministic behavior."""
    
    def test_get_allowed_tools_sorted(self):
        """get_allowed_tools returns sorted list."""
        tools = get_allowed_tools()
        assert tools == sorted(tools)
    
    def test_get_allowed_actions_sorted(self):
        """get_allowed_actions returns sorted list."""
        for tool in ALLOWED_ACTIONS:
            actions = get_allowed_actions(tool)
            assert actions == sorted(actions)
    
    def test_unknown_tool_returns_empty_actions(self):
        """Unknown tool returns empty action list."""
        actions = get_allowed_actions("unknown")
        assert actions == []
