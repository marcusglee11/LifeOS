"""
Tests for Operation Executor.

Per Phase 2 implementation plan.
"""

import hashlib
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from runtime.orchestration.operations import (
    Operation,
    OperationExecutor,
    OperationReceipt,
    ExecutionContext,
    Envelope,
    CompensationType,
    InvalidCompensation,
    EnvelopeViolation,
    validate_compensation,
    compute_state_hash,
    canonical_bytes,
    COMPENSATION_COMMAND_WHITELIST,
)


class TestCompensationType:
    """Test CompensationType enum and validation."""
    
    def test_none_type_accepts_empty_command(self):
        """NONE compensation type accepts empty command."""
        validate_compensation(CompensationType.NONE, "")
        validate_compensation(CompensationType.NONE, "none")
    
    def test_none_type_rejects_non_empty_command(self):
        """NONE compensation type rejects non-empty command."""
        with pytest.raises(InvalidCompensation):
            validate_compensation(CompensationType.NONE, "git reset")
    
    def test_custom_validated_accepts_whitelist_command(self):
        """CUSTOM_VALIDATED accepts commands in whitelist."""
        for cmd in COMPENSATION_COMMAND_WHITELIST:
            validate_compensation(CompensationType.CUSTOM_VALIDATED, cmd)
    
    def test_custom_validated_rejects_unknown_command(self):
        """CUSTOM_VALIDATED rejects commands not in whitelist."""
        with pytest.raises(InvalidCompensation):
            validate_compensation(CompensationType.CUSTOM_VALIDATED, "rm -rf /")
    
    def test_other_types_require_non_empty_command(self):
        """Non-NONE types require non-empty command."""
        with pytest.raises(InvalidCompensation):
            validate_compensation(CompensationType.GIT_CHECKOUT, "")


class TestStateHash:
    """Test deterministic state hashing."""
    
    def test_stable_hash_same_content(self, tmp_path):
        """Same content produces same hash."""
        f1 = tmp_path / "file1.txt"
        f1.write_text("hello world")
        
        hash1 = compute_state_hash(["file1.txt"], tmp_path)
        hash2 = compute_state_hash(["file1.txt"], tmp_path)
        
        assert hash1 == hash2
        assert hash1.startswith("sha256:")
    
    def test_different_content_different_hash(self, tmp_path):
        """Different content produces different hash."""
        f1 = tmp_path / "file1.txt"
        
        f1.write_text("hello")
        hash1 = compute_state_hash(["file1.txt"], tmp_path)
        
        f1.write_text("world")
        hash2 = compute_state_hash(["file1.txt"], tmp_path)
        
        assert hash1 != hash2
    
    def test_missing_file_handled(self, tmp_path):
        """Missing files are handled deterministically."""
        hash1 = compute_state_hash(["nonexistent.txt"], tmp_path)
        hash2 = compute_state_hash(["nonexistent.txt"], tmp_path)
        
        assert hash1 == hash2
    
    def test_order_independent(self, tmp_path):
        """Path order doesn't affect hash (sorted internally)."""
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("a")
        f2.write_text("b")
        
        hash1 = compute_state_hash(["a.txt", "b.txt"], tmp_path)
        hash2 = compute_state_hash(["b.txt", "a.txt"], tmp_path)
        
        assert hash1 == hash2


class TestCanonicalBytes:
    """Test canonical JSON serialization."""
    
    def test_sorted_keys(self):
        """Keys are sorted lexicographically."""
        obj = {"z": 1, "a": 2, "m": 3}
        result = canonical_bytes(obj).decode("utf-8")
        assert result == '{"a":2,"m":3,"z":1}'
    
    def test_no_whitespace(self):
        """No spaces or newlines in output."""
        obj = {"a": [1, 2, 3], "b": {"c": 4}}
        result = canonical_bytes(obj).decode("utf-8")
        assert " " not in result
        assert "\n" not in result
    
    def test_rejects_nan(self):
        """NaN values are rejected."""
        import math
        with pytest.raises(ValueError):
            canonical_bytes({"x": float("nan")})
    
    def test_rejects_infinity(self):
        """Infinity values are rejected."""
        import math
        with pytest.raises(ValueError):
            canonical_bytes({"x": float("inf")})
    
    def test_deterministic(self):
        """Same input produces same output."""
        obj = {"a": 1, "b": [1, 2, 3]}
        result1 = canonical_bytes(obj)
        result2 = canonical_bytes(obj)
        assert result1 == result2


class TestOperationExecutor:
    """Test OperationExecutor."""
    
    @pytest.fixture
    def executor(self):
        return OperationExecutor()
    
    @pytest.fixture
    def context(self, tmp_path):
        return ExecutionContext(
            run_id="sha256:test123",
            run_id_audit="test-uuid",
            mission_id="test-mission",
            mission_type="test",
            step_id="step-1",
            repo_root=tmp_path,
            baseline_commit="abc123",
            envelope=Envelope(allowed_tools=["filesystem", "git"]),
            journal=None,
        )
    
    def test_execute_returns_receipt(self, executor, context):
        """Execute returns OperationResult with receipt."""
        op = Operation(
            operation_id="op-1",
            type="gate_check",
            params={"check": "test"},
            compensation_type=CompensationType.NONE,
            compensation_command="",
        )
        
        result = executor.execute(op, context)
        
        assert result.operation_id == "op-1"
        assert result.receipt is not None
        assert result.receipt.operation_id == "op-1"
        assert result.receipt.pre_state_hash.startswith("sha256:")
        assert result.receipt.post_state_hash.startswith("sha256:")
    
    def test_execute_validates_compensation(self, executor, context):
        """Execute validates compensation before execution."""
        op = Operation(
            operation_id="op-1",
            type="gate_check",
            params={},
            compensation_type=CompensationType.CUSTOM_VALIDATED,
            compensation_command="rm -rf /",  # Not in whitelist
        )
        
        with pytest.raises(InvalidCompensation):
            executor.execute(op, context)
    
    def test_tool_invoke_checks_envelope(self, executor, context):
        """tool_invoke checks allowed_tools in envelope."""
        op = Operation(
            operation_id="op-1",
            type="tool_invoke",
            params={"tool": "opencode", "action": "run"},  # Not in allowed_tools
            compensation_type=CompensationType.NONE,
        )
        
        result = executor.execute(op, context)
        assert result.status == "failed"
        assert "not allowed" in result.evidence.get("error", "")
