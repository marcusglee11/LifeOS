"""
Tests for ToolInvokeRequest compatibility - 'args' vs 'arguments' payload keys.

P0.2 Regression Test: Ensures both payload shapes work end-to-end.
"""
import pytest
from runtime.tools.schemas import ToolInvokeRequest


class TestToolInvokeRequestCompatibility:
    """Regression tests for args/arguments payload compatibility."""
    
    def test_from_dict_with_arguments_key(self):
        """
        P0.2 REGRESSION: from_dict() accepts 'arguments' key and normalizes to .args
        
        This test FAILS if 'arguments' is not accepted/normalized.
        """
        payload = {
            "tool": "filesystem",
            "action": "read_file",
            "arguments": {"path": "README.md"}
        }
        
        request = ToolInvokeRequest.from_dict(payload)
        
        assert request.tool == "filesystem"
        assert request.action == "read_file"
        assert request.args["path"] == "README.md"
        assert request.arguments["path"] == "README.md"  # alias works
        assert request.get_path() == "README.md"
    
    def test_from_dict_with_args_key(self):
        """Standard 'args' key still works."""
        payload = {
            "tool": "pytest",
            "action": "run",
            "args": {"target": "runtime/tests"}
        }
        
        request = ToolInvokeRequest.from_dict(payload)
        
        assert request.tool == "pytest"
        assert request.action == "run"
        assert request.args["target"] == "runtime/tests"
    
    def test_from_dict_with_both_keys_same_value(self):
        """Both keys present with same value - no error."""
        payload = {
            "tool": "filesystem",
            "action": "list_dir",
            "args": {"path": "/tmp"},
            "arguments": {"path": "/tmp"}
        }
        
        request = ToolInvokeRequest.from_dict(payload)
        
        assert request.args["path"] == "/tmp"
    
    def test_from_dict_with_both_keys_different_value_raises(self):
        """Both keys present with different values - raises ValueError."""
        payload = {
            "tool": "filesystem",
            "action": "read_file",
            "args": {"path": "/a"},
            "arguments": {"path": "/b"}
        }
        
        with pytest.raises(ValueError, match="Both 'args' and 'arguments' present"):
            ToolInvokeRequest.from_dict(payload)
    
    def test_from_dict_empty_payload(self):
        """Empty args defaults to empty dict."""
        payload = {
            "tool": "test",
            "action": "check"
        }
        
        request = ToolInvokeRequest.from_dict(payload)
        
        assert request.args == {}
        assert request.arguments == {}
    
    def test_direct_construction_with_args(self):
        """Direct construction with args= keyword works."""
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={"path": "out.txt", "content": "hello"}
        )
        
        assert request.args["path"] == "out.txt"
        assert request.arguments["content"] == "hello"
    
    def test_arguments_property_is_alias(self):
        """The .arguments property returns the same object as .args."""
        request = ToolInvokeRequest(
            tool="test",
            action="run",
            args={"key": "value"}
        )
        
        # They should be the same dict object
        assert request.args is request.arguments
