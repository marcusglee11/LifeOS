"""
Unit tests for Agent Call Logging (hash chain).

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1.4
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

import pytest

from runtime.agents.logging import (
    HASH_CHAIN_GENESIS,
    AgentCallLogEntry,
    AgentCallLogger,
)
from runtime.agents.api import canonical_json
from runtime.agents.models import DEFAULT_MODEL


class TestHashChainGenesis:
    """Tests for hash chain genesis constant."""
    
    def test_genesis_is_deterministic(self):
        """Genesis should be computed from known constant."""
        expected = hashlib.sha256(b"LIFEOS_LOG_CHAIN_GENESIS_V1").hexdigest()
        assert HASH_CHAIN_GENESIS == expected
    
    def test_genesis_is_64_chars(self):
        """Genesis should be valid SHA-256 hex."""
        assert len(HASH_CHAIN_GENESIS) == 64
        assert all(c in "0123456789abcdef" for c in HASH_CHAIN_GENESIS)


class TestAgentCallLogger:
    """Tests for hash chain logging."""
    
    @pytest.fixture
    def logger(self, tmp_path):
        """Create logger with temp directory."""
        return AgentCallLogger(str(tmp_path / "logs"))
    
    def test_logger_starts_with_genesis(self, logger):
        """New logger should have genesis as prev_hash."""
        assert logger.prev_hash == HASH_CHAIN_GENESIS
    
    def test_log_call_creates_entry(self, logger):
        """log_call should create and return entry."""
        entry = logger.log_call(
            call_id_deterministic="sha256:test123",
            call_id_audit="uuid-456",
            role="designer",
            model_requested="auto",
            model_used="minimax-m2.1-free",
            model_version="minimax-m2.1-free",
            input_packet_hash="sha256:input",
            prompt_hash="sha256:prompt",
            input_tokens=100,
            output_tokens=50,
            latency_ms=1234,
            output_packet_hash="sha256:output",
            status="success",
        )
        
        assert entry.call_id_deterministic == "sha256:test123"
        assert entry.role == "designer"
        assert entry.prev_log_hash == HASH_CHAIN_GENESIS
        assert entry.entry_hash  # Should be computed
        assert entry in logger.entries
    
    def test_log_entries_chain_correctly(self, logger):
        """Each entry's prev_log_hash should match previous entry's hash."""
        entry1 = logger.log_call(
            call_id_deterministic="sha256:first",
            call_id_audit="uuid-1",
            role="designer",
            model_requested="auto",
            model_used="model1",
            model_version="v1",
            input_packet_hash="sha256:in1",
            prompt_hash="sha256:p1",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
            output_packet_hash="sha256:out1",
            status="success",
        )
        
        entry2 = logger.log_call(
            call_id_deterministic="sha256:second",
            call_id_audit="uuid-2",
            role="builder",
            model_requested="auto",
            model_used="model2",
            model_version="v2",
            input_packet_hash="sha256:in2",
            prompt_hash="sha256:p2",
            input_tokens=20,
            output_tokens=10,
            latency_ms=200,
            output_packet_hash="sha256:out2",
            status="success",
        )
        
        # Second entry should chain from first
        assert entry2.prev_log_hash == entry1.entry_hash
        
        # Current prev_hash should be last entry's hash
        assert logger.prev_hash == entry2.entry_hash
    
    def test_verify_chain_passes_for_valid_chain(self, logger):
        """verify_chain should pass for untampered chain."""
        logger.log_call(
            call_id_deterministic="sha256:1",
            call_id_audit="uuid-1",
            role="designer",
            model_requested="auto",
            model_used="model",
            model_version="v1",
            input_packet_hash="sha256:in",
            prompt_hash="sha256:p",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
            output_packet_hash="sha256:out",
            status="success",
        )
        
        logger.log_call(
            call_id_deterministic="sha256:2",
            call_id_audit="uuid-2",
            role="builder",
            model_requested="auto",
            model_used="model",
            model_version="v1",
            input_packet_hash="sha256:in2",
            prompt_hash="sha256:p2",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
            output_packet_hash="sha256:out2",
            status="success",
        )
        
        is_valid, breaks = logger.verify_chain()
        
        assert is_valid
        assert breaks == []
    
    def test_verify_chain_detects_tampered_entry(self, logger):
        """verify_chain should detect modified entries."""
        entry = logger.log_call(
            call_id_deterministic="sha256:original",
            call_id_audit="uuid-1",
            role="designer",
            model_requested="auto",
            model_used="model",
            model_version="v1",
            input_packet_hash="sha256:in",
            prompt_hash="sha256:p",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
            output_packet_hash="sha256:out",
            status="success",
        )
        
        # Tamper with entry
        entry.role = "TAMPERED"
        
        is_valid, breaks = logger.verify_chain()
        
        assert not is_valid
        assert len(breaks) > 0
        assert "entry_hash mismatch" in breaks[0]
    
    def test_verify_chain_detects_broken_link(self, logger):
        """verify_chain should detect if prev_hash is wrong."""
        logger.log_call(
            call_id_deterministic="sha256:1",
            call_id_audit="uuid-1",
            role="designer",
            model_requested="auto",
            model_used="model",
            model_version="v1",
            input_packet_hash="sha256:in",
            prompt_hash="sha256:p",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
            output_packet_hash="sha256:out",
            status="success",
        )
        
        entry2 = logger.log_call(
            call_id_deterministic="sha256:2",
            call_id_audit="uuid-2",
            role="builder",
            model_requested="auto",
            model_used="model",
            model_version="v1",
            input_packet_hash="sha256:in2",
            prompt_hash="sha256:p2",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
            output_packet_hash="sha256:out2",
            status="success",
        )
        
        # Break the chain
        entry2.prev_log_hash = "BROKEN"
        
        is_valid, breaks = logger.verify_chain()
        
        assert not is_valid
        assert len(breaks) > 0
        assert "expected prev_log_hash" in breaks[0]
    
    def test_entries_property_returns_copy(self, logger):
        """entries property should return a copy, not the internal list."""
        logger.log_call(
            call_id_deterministic="sha256:test",
            call_id_audit="uuid",
            role="designer",
            model_requested="auto",
            model_used="model",
            model_version="v1",
            input_packet_hash="sha256:in",
            prompt_hash="sha256:p",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
            output_packet_hash="sha256:out",
            status="success",
        )
        
        entries = logger.entries
        entries.clear()
        
        # Internal list should be unaffected
        assert len(logger.entries) == 1


class TestAgentCallLogEntry:
    """Tests for log entry dataclass."""
    
    def test_entry_has_all_required_fields(self):
        """Entry should have all spec-required fields."""
        entry = AgentCallLogEntry(
            call_id_deterministic="sha256:test",
            call_id_audit="uuid-123",
            timestamp="2026-01-08T12:00:00Z",
            role="designer",
            model_requested="auto",
            model_used="minimax-m2.1-free",
            model_version="minimax-m2.1-free",
            input_packet_hash="sha256:input",
            prompt_hash="sha256:prompt",
            input_tokens=100,
            output_tokens=50,
            latency_ms=1234,
            output_packet_hash="sha256:output",
            status="success",
            prev_log_hash=HASH_CHAIN_GENESIS,
        )
        
        # All fields should be accessible
        assert entry.call_id_deterministic
        assert entry.timestamp
        assert entry.role
        assert entry.status == "success"
