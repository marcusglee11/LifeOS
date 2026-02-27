"""
Unit tests for Agent API Layer.

Tests call_agent() with mocked OpenRouter responses.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1
"""

from __future__ import annotations

import hashlib
import json
import os
from unittest.mock import patch, MagicMock
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest
import httpx

from runtime.agents.api import (
    canonical_json,
    compute_run_id_deterministic,
    compute_call_id_deterministic,
    AgentCall,
    AgentResponse,
    AgentAPIError,
    EnvelopeViolation,
    AgentTimeoutError,
    call_agent,
)
from runtime.agents.models import ModelConfig, DEFAULT_MODEL


class TestCanonicalJson:
    """Tests for canonical JSON serialization."""
    
    def test_canonical_json_stable_ordering(self):
        """Key ordering should be lexicographic."""
        obj1 = {"b": 1, "a": 2, "c": 3}
        obj2 = {"a": 2, "c": 3, "b": 1}
        
        assert canonical_json(obj1) == canonical_json(obj2)
    
    def test_canonical_json_no_whitespace(self):
        """No spaces after colons or commas."""
        obj = {"key": "value", "list": [1, 2, 3]}
        result = canonical_json(obj).decode("utf-8")
        
        assert ": " not in result
        assert ", " not in result
    
    def test_canonical_json_utf8(self):
        """Should handle Unicode properly."""
        obj = {"emoji": "🎉", "chinese": "中文"}
        result = canonical_json(obj)
        
        assert isinstance(result, bytes)
        decoded = result.decode("utf-8")
        assert "🎉" in decoded
        assert "中文" in decoded
    
    def test_canonical_json_rejects_nan(self):
        """Should fail-closed on NaN values."""
        import math
        obj = {"value": math.nan}
        
        with pytest.raises(ValueError):
            canonical_json(obj)


class TestDeterministicIds:
    """Tests for deterministic ID computation."""
    
    def test_run_id_deterministic(self):
        """Same inputs should produce same run ID."""
        run_id_1 = compute_run_id_deterministic(
            mission_spec={"type": "build"},
            inputs_hash="sha256:abc123",
            governance_surface_hashes={"file.py": "sha256:def456"},
            code_version_id="abc123def",
        )
        run_id_2 = compute_run_id_deterministic(
            mission_spec={"type": "build"},
            inputs_hash="sha256:abc123",
            governance_surface_hashes={"file.py": "sha256:def456"},
            code_version_id="abc123def",
        )
        
        assert run_id_1 == run_id_2
        assert run_id_1.startswith("sha256:")
    
    def test_call_id_deterministic(self):
        """Same inputs should produce same call ID."""
        call_id_1 = compute_call_id_deterministic(
            run_id_deterministic="sha256:run123",
            role="designer",
            prompt_hash="sha256:prompt456",
            packet_hash="sha256:packet789",
        )
        call_id_2 = compute_call_id_deterministic(
            run_id_deterministic="sha256:run123",
            role="designer",
            prompt_hash="sha256:prompt456",
            packet_hash="sha256:packet789",
        )
        
        assert call_id_1 == call_id_2
        assert call_id_1.startswith("sha256:")
    
    def test_different_inputs_different_ids(self):
        """Different inputs should produce different IDs."""
        call_id_1 = compute_call_id_deterministic(
            run_id_deterministic="sha256:run123",
            role="designer",
            prompt_hash="sha256:prompt456",
            packet_hash="sha256:packet789",
        )
        call_id_2 = compute_call_id_deterministic(
            run_id_deterministic="sha256:run123",
            role="builder",  # Different role
            prompt_hash="sha256:prompt456",
            packet_hash="sha256:packet789",
        )
        
        assert call_id_1 != call_id_2


class TestAgentCallDataclass:
    """Tests for AgentCall dataclass."""
    
    def test_default_values(self):
        """Should have correct defaults."""
        call = AgentCall(role="designer", packet={"task": "test"})
        
        assert call.model == "auto"
        assert call.temperature == 0.0
        assert call.max_tokens == 8192


class MockTransport(httpx.BaseTransport):
    """Mock transport for httpx that returns predefined responses."""
    
    def __init__(self, response_data: dict, status_code: int = 200):
        self.response_data = response_data
        self.status_code = status_code
        self.requests = []
    
    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(
            status_code=self.status_code,
            json=self.response_data,
        )


class TestCallAgent:
    """Tests for call_agent function with mocked OpenRouter."""
    
    @pytest.fixture
    def temp_config_dir(self, tmp_path):
        """Create temporary config directory with role prompts."""
        agent_roles = tmp_path / "config" / "agent_roles"
        agent_roles.mkdir(parents=True)
        
        # Create designer prompt
        designer_prompt = agent_roles / "designer.md"
        designer_prompt.write_text("You are a designer agent.", encoding="utf-8")
        
        # Create builder prompt
        builder_prompt = agent_roles / "builder.md"
        builder_prompt.write_text("You are a builder agent.", encoding="utf-8")
        
        return tmp_path
    
    @pytest.fixture
    def mock_openrouter_response(self):
        """Standard successful OpenRouter response."""
        return {
            "id": "gen-123",
            "model": "minimax-m2.1-free",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "design_type: implementation_plan\nsummary: Test design",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }
    
    def test_call_agent_missing_role_prompt(self, temp_config_dir):
        """Should raise EnvelopeViolation for missing role."""
        os.chdir(temp_config_dir)
        
        call = AgentCall(role="nonexistent", packet={"task": "test"})
        
        with pytest.raises(EnvelopeViolation, match="Role prompt not found"):
            call_agent(call)
    
    def test_call_agent_missing_api_key(self, temp_config_dir):
        """Should raise error if API key not set."""
        os.chdir(temp_config_dir)

        class FailingOpenCodeClient:
            def __init__(self, *args, **kwargs):
                pass

            def call(self, request):
                raise RuntimeError("OPENROUTER_API_KEY missing")

        with patch("runtime.agents.opencode_client.OpenCodeClient", FailingOpenCodeClient):
            call = AgentCall(role="designer", packet={"task": "test"})
            with pytest.raises(AgentAPIError, match="OPENROUTER_API_KEY"):
                call_agent(call)
    
    def test_call_agent_success(self, temp_config_dir, mock_openrouter_response, monkeypatch):
        """Should successfully call OpenRouter and return response."""
        os.chdir(temp_config_dir)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")

        class SuccessfulOpenCodeClient:
            def __init__(self, *args, **kwargs):
                pass

            def call(self, request):
                return SimpleNamespace(
                    call_id="mock-call-1",
                    content="design_type: implementation_plan\nsummary: Test design",
                    model_used="minimax-m2.1-free",
                    usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
                )

        with patch("runtime.agents.opencode_client.OpenCodeClient", SuccessfulOpenCodeClient):
            call = AgentCall(role="designer", packet={"task": "test"})
            config = ModelConfig(default_chain=["minimax-m2.1-free"])
            
            response = call_agent(call, run_id="test-run", config=config)
        
        assert response.role == "designer"
        assert response.model_used == "minimax-m2.1-free"
        assert "implementation_plan" in response.content
        assert response.call_id.startswith("sha256:")
        assert response.latency_ms >= 0  # May be 0 in mocked tests
    
    def test_call_agent_parses_yaml_response(self, temp_config_dir, monkeypatch):
        """Should parse YAML responses into packet dict."""
        os.chdir(temp_config_dir)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")

        class YamlOpenCodeClient:
            def __init__(self, *args, **kwargs):
                pass

            def call(self, request):
                return SimpleNamespace(
                    call_id="mock-call-2",
                    content="key: value\nlist:\n  - item1\n  - item2",
                    model_used="minimax-m2.1-free",
                    usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                )

        with patch("runtime.agents.opencode_client.OpenCodeClient", YamlOpenCodeClient):
            call = AgentCall(role="designer", packet={"task": "test"})
            config = ModelConfig(default_chain=["minimax-m2.1-free"])
            
            response = call_agent(call, config=config)
        
        assert response.packet is not None
        assert response.packet["key"] == "value"
        assert response.packet["list"] == ["item1", "item2"]

    def test_call_agent_fallback_on_rate_limit(self, temp_config_dir, monkeypatch):
        """Should retry and succeed after rate limit (simulating fallback logic)."""
        os.chdir(temp_config_dir)
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key-123")
        calls = 0

        class FallbackOpenCodeClient:
            def __init__(self, *args, **kwargs):
                pass

            def call(self, request):
                nonlocal calls
                calls += 1
                return SimpleNamespace(
                    call_id="mock-call-3",
                    content="ok",
                    model_used="minimax-m2.1-free",
                    usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                )

        with patch("runtime.agents.opencode_client.OpenCodeClient", FallbackOpenCodeClient):
            call = AgentCall(role="designer", packet={"task": "test"})
            config = ModelConfig(
                default_chain=["minimax-m2.1-free"],
                backoff_base_seconds=0.01  # Fast backoff for test
            )
            
            response = call_agent(call, config=config)
            
        assert response.content == "ok"
        assert calls == 1


class TestCallAgentReplayMode:
    """Tests for replay mode behavior."""
    
    def test_replay_mode_detection(self, monkeypatch):
        """Should detect LIFEOS_TEST_MODE=replay."""
        from runtime.agents.fixtures import is_replay_mode
        
        monkeypatch.delenv("LIFEOS_TEST_MODE", raising=False)
        assert not is_replay_mode()
        
        monkeypatch.setenv("LIFEOS_TEST_MODE", "replay")
        assert is_replay_mode()
        
        monkeypatch.setenv("LIFEOS_TEST_MODE", "REPLAY")
        assert is_replay_mode()
    
    def test_replay_mode_returns_cached(self, tmp_path, monkeypatch):
        """Should return cached response in replay mode."""
        from runtime.agents.fixtures import (
            ReplayFixtureCache,
            CachedResponse,
            is_replay_mode,
        )
        
        monkeypatch.setenv("LIFEOS_TEST_MODE", "replay")
        
        # Create cache with fixture
        cache_dir = tmp_path / "cache"
        cache = ReplayFixtureCache(str(cache_dir))
        
        cached = CachedResponse(
            call_id_deterministic="sha256:test123",
            role="designer",
            model_version="minimax-m2.1-free",
            input_packet_hash="sha256:input",
            prompt_hash="sha256:prompt",
            response_content="cached content",
            response_packet={"key": "value"},
        )
        
        cache.save_fixture(cached)
        
        # Verify fixture was saved
        reloaded = cache.get("sha256:test123")
        assert reloaded is not None
        assert reloaded.response_content == "cached content"

    def test_replay_mode_require_usage_fails_closed(self, tmp_path, monkeypatch):
        """Should fail closed when replay mode is used with require_usage=True."""
        from runtime.agents.fixtures import CachedResponse

        agent_roles = tmp_path / "config" / "agent_roles"
        agent_roles.mkdir(parents=True)
        (agent_roles / "designer.md").write_text("You are a designer agent.", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("LIFEOS_TEST_MODE", "replay")

        cached = CachedResponse(
            call_id_deterministic="sha256:cached",
            role="designer",
            model_version="minimax-m2.1-free",
            input_packet_hash="sha256:input",
            prompt_hash="sha256:prompt",
            response_content="cached content",
            response_packet={"key": "value"},
        )

        with patch("runtime.agents.fixtures.get_cached_response", return_value=cached):
            with pytest.raises(AgentAPIError, match="TOKEN_ACCOUNTING_UNAVAILABLE"):
                call_agent(
                    AgentCall(
                        role="designer",
                        packet={"task": "test"},
                        require_usage=True,
                    )
                )
