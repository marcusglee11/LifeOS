"""
Integration Tests for Tool Invoke Substrate.

Per Plan_Tool_Invoke_MVP_v0.2:
- Golden workflow: write → read (hash match) → pytest
- Schema fields verified: timestamp_utc, size_bytes, truncated
- No LLM calls, offline deterministic test
"""

import hashlib
import os
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import patch

from runtime.tools.registry import ToolRegistry, get_registry, reset_global_registry
from runtime.tools.schemas import (
    ToolInvokeRequest,
    ToolInvokeResult,
    OUTPUT_CAP_BYTES,
)


class TestGoldenWorkflow:
    """
    Golden workflow integration test.
    
    Hardcoded subpath + filename under sandbox.
    write_file → read_file (hash match) → pytest run
    """
    
    @pytest.fixture
    def sandbox(self, tmp_path):
        """Create sandbox with test file."""
        # Reset global registry to ensure clean state
        reset_global_registry()
        return tmp_path
    
    def test_golden_workflow_write_read_pytest(self, sandbox):
        """
        Integration test: write → read → pytest.
        
        1. Write a test file
        2. Read it back and verify hash match
        3. Run pytest on a simple test
        """
        registry = get_registry(sandbox_root=sandbox)
        
        # Step 1: Write a test file
        test_content = "def test_integration(): assert 1 + 1 == 2"
        write_request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "test_integration.py",
                "content": test_content,
            },
            meta={"request_id": "write-001"},
        )
        
        write_result = registry.dispatch(write_request)
        
        # Verify write success
        assert write_result.ok is True
        assert write_result.timestamp_utc is not None
        assert write_result.request_id == "write-001"
        
        # Verify effects
        assert write_result.effects is not None
        assert write_result.effects.files_written is not None
        assert len(write_result.effects.files_written) == 1
        
        written_effect = write_result.effects.files_written[0]
        assert written_effect.size_bytes == len(test_content.encode("utf-8"))
        expected_hash = hashlib.sha256(test_content.encode("utf-8")).hexdigest()
        assert written_effect.sha256 == expected_hash
        
        # Step 2: Read the file back
        read_request = ToolInvokeRequest(
            tool="filesystem",
            action="read_file",
            args={"path": "test_integration.py"},
            meta={"request_id": "read-001"},
        )
        
        read_result = registry.dispatch(read_request)
        
        # Verify read success
        assert read_result.ok is True
        assert read_result.output.stdout == test_content
        assert read_result.request_id == "read-001"
        
        # Verify hash match
        assert read_result.effects is not None
        assert read_result.effects.files_read is not None
        read_effect = read_result.effects.files_read[0]
        assert read_effect.sha256 == expected_hash  # Same hash as written
        
        # Step 3: Run pytest
        pytest_request = ToolInvokeRequest(
            tool="pytest",
            action="run",
            args={"target": "runtime/tests/test_integration.py", "args": ["-v"]},
            meta={"request_id": "pytest-001"},
        )
        
        pytest_result = registry.dispatch(pytest_request)
        
        # Verify pytest success
        assert pytest_result.ok is True
        assert pytest_result.request_id == "pytest-001"
        assert pytest_result.effects is not None
        assert pytest_result.effects.process is not None
        assert pytest_result.effects.process.exit_code == 0
        assert pytest_result.effects.process.duration_ms > 0
        assert "pytest" in " ".join(pytest_result.effects.process.cmd)


class TestSchemaCompliance:
    """Tests for schema field compliance per spec."""
    
    @pytest.fixture
    def sandbox(self, tmp_path):
        reset_global_registry()
        return tmp_path
    
    def test_timestamp_utc_present_and_parseable(self, sandbox):
        """timestamp_utc field is present and ISO 8601 parseable."""
        registry = get_registry(sandbox_root=sandbox)
        
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={"path": "test.txt", "content": "test"},
        )
        
        result = registry.dispatch(request)
        
        assert result.timestamp_utc is not None
        # Should be parseable as ISO 8601
        parsed = datetime.fromisoformat(result.timestamp_utc.replace("Z", "+00:00"))
        assert parsed is not None
    
    def test_size_bytes_is_int(self, sandbox):
        """Effects use size_bytes as int, not bytes."""
        registry = get_registry(sandbox_root=sandbox)
        
        content = "Hello, World!"
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={"path": "test.txt", "content": content},
        )
        
        result = registry.dispatch(request)
        
        assert result.effects.files_written[0].size_bytes == len(content.encode("utf-8"))
        assert isinstance(result.effects.files_written[0].size_bytes, int)
    
    def test_truncated_bool_present(self, sandbox):
        """output.truncated is a bool and present."""
        registry = get_registry(sandbox_root=sandbox)
        
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={"path": "test.txt", "content": "test"},
        )
        
        result = registry.dispatch(request)
        
        assert isinstance(result.output.truncated, bool)


class TestPolicyEnforcement:
    """Tests for policy enforcement in integration."""
    
    @pytest.fixture
    def sandbox(self, tmp_path):
        reset_global_registry()
        return tmp_path
    
    def test_unknown_tool_denied(self, sandbox):
        """Unknown tool is denied with PolicyDenied."""
        registry = get_registry(sandbox_root=sandbox)
        
        request = ToolInvokeRequest(
            tool="git",
            action="commit",
            args={"message": "should not work"},
        )
        
        result = registry.dispatch(request)
        
        assert result.ok is False
        assert result.error is not None
        assert result.error.type == "PolicyDenied"
    
    def test_unknown_action_denied(self, sandbox):
        """Unknown action on known tool is denied."""
        registry = get_registry(sandbox_root=sandbox)
        
        request = ToolInvokeRequest(
            tool="filesystem",
            action="delete",  # Not allowed
            args={"path": "test.txt"},
        )
        
        result = registry.dispatch(request)
        
        assert result.ok is False
        assert result.error is not None
        assert result.error.type == "PolicyDenied"
    
    def test_path_escape_no_side_effects(self, sandbox):
        """Path escape attempt has no side effects."""
        registry = get_registry(sandbox_root=sandbox)
        
        # Path that would escape sandbox
        escape_path = sandbox.parent / "escape.txt"
        if escape_path.exists():
            escape_path.unlink()
        
        request = ToolInvokeRequest(
            tool="filesystem",
            action="write_file",
            args={
                "path": "../escape.txt",
                "content": "should not write",
            },
        )
        
        result = registry.dispatch(request)
        
        # Should fail
        assert result.ok is False
        
        # No file should be created
        assert not escape_path.exists()


class TestGovernanceUnavailable:
    """Tests for GovernanceUnavailable scenarios."""
    
    def test_missing_sandbox_root_env(self):
        """Missing LIFEOS_SANDBOX_ROOT returns GovernanceUnavailable."""
        reset_global_registry()
        
        # Reset the global scope roots cache to ensure clean state
        from runtime.governance.tool_policy import reset_scope_roots
        reset_scope_roots()
        
        # Create registry without explicit sandbox_root
        # and ensure env var is not set
        with patch.dict(os.environ, {}, clear=True):
            if "LIFEOS_SANDBOX_ROOT" in os.environ:
                del os.environ["LIFEOS_SANDBOX_ROOT"]
            
            registry = ToolRegistry()  # No sandbox_root override
            
            request = ToolInvokeRequest(
                tool="filesystem",
                action="read_file",
                args={"path": "test.txt"},
            )
            
            result = registry.dispatch(request)
            
            assert result.ok is False
            assert result.error is not None
            assert result.error.type == "GovernanceUnavailable"

