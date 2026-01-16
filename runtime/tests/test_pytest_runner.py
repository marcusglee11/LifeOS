"""
Tests for Pytest Runner Tool Handler.

Per Plan_Tool_Invoke_MVP_v0.2:
- Timeout enforcement (5s for tests)
- Output capture with 64KB combined cap
- Deterministic truncation: stdout first, then stderr
- Minimal structured output: cmd, exit_code, duration_ms, stdout, stderr, truncated
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from runtime.tools.pytest_runner import (
    handle_pytest_run,
    DEFAULT_TIMEOUT_SECONDS,
    TEST_TIMEOUT_SECONDS,
)
from runtime.tools.schemas import ToolErrorType, OUTPUT_CAP_BYTES, truncate_output


class TestPytestRunSuccess:
    """Tests for successful pytest execution."""
    
    def test_pytest_run_returns_structured_result(self, tmp_path):
        """Pytest run returns structured result with required fields."""
        # Create a minimal passing test
        test_file = tmp_path / "test_pass.py"
        test_file.write_text("def test_pass(): assert True")
        
        result = handle_pytest_run({"args": [str(test_file), "-v"]}, tmp_path)
        
        assert result.ok is True
        assert result.tool == "pytest"
        assert result.action == "run"
        assert result.timestamp_utc is not None
        assert result.output is not None
        assert isinstance(result.output.truncated, bool)
        
        # Check effects
        assert result.effects is not None
        assert result.effects.process is not None
        assert result.effects.process.exit_code == 0
        assert result.effects.process.duration_ms > 0
        assert "pytest" in result.effects.process.cmd[2]
    
    def test_pytest_run_failure_returns_nonzero_exit(self, tmp_path):
        """Failing test returns non-zero exit code."""
        test_file = tmp_path / "test_fail.py"
        test_file.write_text("def test_fail(): assert False")
        
        result = handle_pytest_run({"args": [str(test_file)]}, tmp_path)
        
        assert result.ok is True  # Execution succeeded, test failed
        assert result.effects.process.exit_code != 0


class TestPytestTimeout:
    """Tests for timeout enforcement."""
    
    def test_pytest_timeout_returns_timeout_error(self, tmp_path):
        """Hanging test with short timeout returns Timeout error."""
        # Create a test that hangs
        test_file = tmp_path / "test_hang.py"
        test_file.write_text("""
import time
def test_hang():
    time.sleep(60)  # Sleep longer than timeout
""")
        
        result = handle_pytest_run({
            "args": [str(test_file)],
            "timeout": 2  # Very short timeout
        }, tmp_path)
        
        assert result.ok is False
        assert result.error is not None
        assert result.error.type == ToolErrorType.TIMEOUT
        assert "timed out" in result.error.message.lower()


class TestOutputTruncation:
    """Tests for output capture and truncation."""
    
    def test_truncate_output_under_cap_not_truncated(self):
        """Output under cap is not truncated."""
        stdout = "short stdout"
        stderr = "short stderr"
        
        result = truncate_output(stdout, stderr, OUTPUT_CAP_BYTES)
        
        assert result.stdout == stdout
        assert result.stderr == stderr
        assert result.truncated is False
    
    def test_truncate_output_over_cap_is_truncated(self):
        """Output over cap is truncated with flag set."""
        # Create output larger than cap
        stdout = "x" * (OUTPUT_CAP_BYTES + 1000)
        stderr = "y" * 1000
        
        result = truncate_output(stdout, stderr, OUTPUT_CAP_BYTES)
        
        assert result.truncated is True
        total_size = len(result.stdout.encode("utf-8")) + len(result.stderr.encode("utf-8"))
        assert total_size <= OUTPUT_CAP_BYTES
    
    def test_truncate_output_deterministic_allocation(self):
        """Truncation follows deterministic rule: stdout first, then stderr."""
        # stdout takes priority
        stdout = "s" * 50000
        stderr = "e" * 50000
        cap = 60000
        
        result = truncate_output(stdout, stderr, cap)
        
        # stdout should be preserved up to budget
        assert len(result.stdout.encode("utf-8")) == 50000  # Full stdout
        assert len(result.stderr.encode("utf-8")) == cap - 50000  # Remainder for stderr
        assert result.truncated is True
    
    def test_truncation_is_deterministic(self):
        """Same input produces same output (determinism)."""
        stdout = "x" * 100000
        stderr = "y" * 100000
        
        result1 = truncate_output(stdout, stderr, OUTPUT_CAP_BYTES)
        result2 = truncate_output(stdout, stderr, OUTPUT_CAP_BYTES)
        
        assert result1.stdout == result2.stdout
        assert result1.stderr == result2.stderr
        assert result1.truncated == result2.truncated


class TestPytestArguments:
    """Tests for argument handling."""
    
    def test_invalid_args_type_returns_schema_error(self, tmp_path):
        """Non-list args returns SchemaError."""
        result = handle_pytest_run({"args": "not a list"}, tmp_path)
        
        assert result.ok is False
        assert result.error is not None
        assert result.error.type == ToolErrorType.SCHEMA_ERROR
    
    def test_empty_args_runs_pytest(self, tmp_path):
        """Empty args runs pytest in sandbox root."""
        result = handle_pytest_run({"args": []}, tmp_path)
        
        # Pytest runs (may find no tests, but executes)
        assert result.effects is not None
        assert result.effects.process is not None
