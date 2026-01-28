"""
Tests for P0.4 filesystem path enforcement.
"""
import pytest
from pathlib import Path
from runtime.governance.tool_policy import check_tool_action_allowed, PolicyDecision
from runtime.tools.schemas import ToolInvokeRequest


class TestFilesystemPathEnforcement:
    """Test P0.4 path enforcement requirements."""
    
    def test_filesystem_read_without_path_denied(self):
        """filesystem read_file without path is denied (fail-closed)."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="read_file",
            args={}
        )
        
        allowed, decision = check_tool_action_allowed(request, path=None)
        
        assert allowed is False
        assert "filesystem.read_file requires path" in decision.decision_reason
        assert "filesystem_path_required" in decision.matched_rules
    
    def test_filesystem_write_without_path_denied(self):
        """filesystem write_file without path is denied (fail-closed)."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={}
        )
        
        allowed, decision = check_tool_action_allowed(request, path=None)
        
        assert allowed is False
        assert "filesystem.write_file requires path" in decision.decision_reason
    
    def test_filesystem_list_without_path_denied(self):
        """filesystem list_dir without path is denied (fail-closed)."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="list_dir",
            args={}
        )
        
        allowed, decision = check_tool_action_allowed(request, path=None)
        
        assert allowed is False
        assert "filesystem.list_dir requires path" in decision.decision_reason
    
    def test_filesystem_empty_string_path_denied(self):
        """filesystem operation with empty string path is denied."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="read_file",
            args={}
        )
        
        allowed, decision = check_tool_action_allowed(request, path="")
        
        assert allowed is False
        assert "requires path" in decision.decision_reason


class TestToolPolicyGovernance:
    """Test tool policy governance rules."""
    
    def test_unknown_tool_denied(self):
        """Unknown tool is denied."""
        request = ToolInvokeRequest(
            tool="unknown_tool",
            action="some_action",
            args={}
        )
        
        allowed, decision = check_tool_action_allowed(request)
        
        assert allowed is False
        assert "Unknown tool" in decision.decision_reason
    
    def test_unknown_action_denied(self):
        """Unknown action for known tool is denied."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="delete_everything",
            args={}
        )
        
        allowed, decision = check_tool_action_allowed(request)
        
        assert allowed is False
        assert "not allowed" in decision.decision_reason
