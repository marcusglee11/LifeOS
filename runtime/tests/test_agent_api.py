"""
Tests for Agent API - Deterministic IDs and hash chain logging.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1
"""

import pytest

from runtime.agents.api import (
    canonical_json,
    compute_run_id_deterministic,
    compute_call_id_deterministic,
    AgentCall,
    AgentResponse,
)
from runtime.agents.agent_logging import (
    HASH_CHAIN_GENESIS,
    AgentCallLogger,
    AgentCallLogEntry,
)


class TestCanonicalJson:
    """Tests for canonical_json per v0.3 §5.1.4."""
    
    def test_deterministic_output(self):
        """Same input should always produce same output."""
        obj = {"b": 2, "a": 1, "c": [3, 1, 2]}
        result1 = canonical_json(obj)
        result2 = canonical_json(obj)
        assert result1 == result2
    
    def test_sorted_keys(self):
        """Keys should be sorted lexicographically."""
        obj = {"z": 1, "a": 2, "m": 3}
        result = canonical_json(obj)
        assert result == b'{"a":2,"m":3,"z":1}'
    
    def test_no_whitespace(self):
        """Should have no whitespace (no spaces after colons/commas)."""
        obj = {"key": "value", "list": [1, 2, 3]}
        result = canonical_json(obj)
        assert b" " not in result
        assert b"\n" not in result
    
    def test_utf8_encoding(self):
        """Should encode as UTF-8."""
        obj = {"emoji": "🎉", "text": "héllo"}
        result = canonical_json(obj)
        assert isinstance(result, bytes)
        # Should contain UTF-8 bytes for emoji and accented char
        assert "🎉".encode("utf-8") in result
        assert "héllo".encode("utf-8") in result
    
    def test_preserves_array_order(self):
        """Arrays should preserve order (not sorted)."""
        obj = {"arr": [3, 1, 2]}
        result = canonical_json(obj)
        assert result == b'{"arr":[3,1,2]}'
    
    def test_rejects_nan_fail_closed(self):
        """[v0.3 Fail-Closed] NaN values should raise ValueError."""
        import math
        obj = {"value": float("nan")}
        with pytest.raises(ValueError) as exc_info:
            canonical_json(obj)
        assert "Out of range float values" in str(exc_info.value) or "NaN" in str(exc_info.value).upper()
    
    def test_rejects_infinity_fail_closed(self):
        """[v0.3 Fail-Closed] Infinity values should raise ValueError."""
        import math
        obj = {"value": float("inf")}
        with pytest.raises(ValueError) as exc_info:
            canonical_json(obj)
        assert "Out of range float values" in str(exc_info.value) or "Infinity" in str(exc_info.value)


class TestDeterministicIds:
    """Tests for deterministic ID generation per v0.3 §5.1.3."""
    
    def test_run_id_deterministic_stability(self):
        """Same inputs should produce same run_id."""
        mission_spec = {"mission": "test", "version": "1.0"}
        inputs_hash = "sha256:abc123"
        governance_hashes = {"file1": "hash1", "file2": "hash2"}
        code_version = "abc123def"
        
        id1 = compute_run_id_deterministic(
            mission_spec, inputs_hash, governance_hashes, code_version
        )
        id2 = compute_run_id_deterministic(
            mission_spec, inputs_hash, governance_hashes, code_version
        )
        
        assert id1 == id2
        assert id1.startswith("sha256:")
    
    def test_run_id_changes_with_different_inputs(self):
        """Different inputs should produce different run_id."""
        mission_spec = {"mission": "test", "version": "1.0"}
        code_version = "abc123def"
        
        id1 = compute_run_id_deterministic(
            mission_spec, "hash1", {"f": "h1"}, code_version
        )
        id2 = compute_run_id_deterministic(
            mission_spec, "hash2", {"f": "h1"}, code_version
        )
        
        assert id1 != id2
    
    def test_call_id_deterministic_stability(self):
        """Same inputs should produce same call_id."""
        run_id = "sha256:abc123"
        role = "designer"
        prompt_hash = "sha256:prompt123"
        packet_hash = "sha256:packet456"
        
        id1 = compute_call_id_deterministic(run_id, role, prompt_hash, packet_hash)
        id2 = compute_call_id_deterministic(run_id, role, prompt_hash, packet_hash)
        
        assert id1 == id2
        assert id1.startswith("sha256:")
    
    def test_call_id_changes_with_different_role(self):
        """Different role should produce different call_id."""
        run_id = "sha256:abc123"
        prompt_hash = "sha256:prompt123"
        packet_hash = "sha256:packet456"
        
        id1 = compute_call_id_deterministic(run_id, "designer", prompt_hash, packet_hash)
        id2 = compute_call_id_deterministic(run_id, "reviewer", prompt_hash, packet_hash)
        
        assert id1 != id2


class TestHashChainLogging:
    """Tests for hash chain logging per v0.3 §5.1.4 and §5.8."""
    
    def test_genesis_constant(self):
        """HASH_CHAIN_GENESIS should be a fixed constant."""
        # Verify it's the SHA256 of the expected string
        import hashlib
        expected = hashlib.sha256(b"LIFEOS_LOG_CHAIN_GENESIS_V1").hexdigest()
        assert HASH_CHAIN_GENESIS == expected
    
    def test_first_entry_uses_genesis(self):
        """First log entry should have prev_log_hash = HASH_CHAIN_GENESIS."""
        logger = AgentCallLogger()
        
        entry = logger.log_call(
            call_id_deterministic="sha256:test",
            call_id_audit="uuid-1",
            role="designer",
            model_requested="auto",
            model_used="claude-3-sonnet",
            model_version="20240229",
            input_packet_hash="sha256:input",
            prompt_hash="sha256:prompt",
            input_tokens=100,
            output_tokens=50,
            latency_ms=1000,
            output_packet_hash="sha256:output",
            status="success",
        )
        
        assert entry.prev_log_hash == HASH_CHAIN_GENESIS
        assert entry.entry_hash != ""
    
    def test_chain_integrity(self):
        """Hash chain should be verifiable."""
        logger = AgentCallLogger()
        
        # Log multiple entries
        for i in range(5):
            logger.log_call(
                call_id_deterministic=f"sha256:test{i}",
                call_id_audit=f"uuid-{i}",
                role="designer",
                model_requested="auto",
                model_used="claude-3-sonnet",
                model_version="20240229",
                input_packet_hash=f"sha256:input{i}",
                prompt_hash=f"sha256:prompt{i}",
                input_tokens=100 + i,
                output_tokens=50 + i,
                latency_ms=1000 + i,
                output_packet_hash=f"sha256:output{i}",
                status="success",
            )
        
        is_valid, breaks = logger.verify_chain()
        assert is_valid is True
        assert breaks == []
    
    def test_chain_detects_tampering(self):
        """Should detect if chain is tampered with."""
        logger = AgentCallLogger()
        
        # Log an entry
        logger.log_call(
            call_id_deterministic="sha256:test1",
            call_id_audit="uuid-1",
            role="designer",
            model_requested="auto",
            model_used="claude-3-sonnet",
            model_version="20240229",
            input_packet_hash="sha256:input",
            prompt_hash="sha256:prompt",
            input_tokens=100,
            output_tokens=50,
            latency_ms=1000,
            output_packet_hash="sha256:output",
            status="success",
        )
        
        # Tamper with the entry
        logger._entries[0].prev_log_hash = "tampered_hash"
        
        is_valid, breaks = logger.verify_chain()
        assert is_valid is False
        assert len(breaks) > 0
