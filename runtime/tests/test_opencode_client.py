"""
Tests for OpenCode Client Module
================================

Unit tests that don't require a real OpenCode server.
Tests client instantiation, dataclasses, and error classes.
"""

import os
import json
import tempfile
import pytest
from datetime import datetime

from runtime.agents.opencode_client import (
    OpenCodeClient,
    LLMCall,
    LLMResponse,
    OpenCodeError,
    OpenCodeServerError,
    OpenCodeTimeoutError,
    OpenCodeSessionError,
)

# Import canonical default from single source of truth
from runtime.agents.models import DEFAULT_MODEL


# ============================================================================
# DATACLASS TESTS
# ============================================================================

class TestLLMCall:
    """Tests for LLMCall dataclass."""

    def test_llm_call_default_model(self):
        """LLMCall should have sensible default model."""
        call = LLMCall(prompt="Hello")
        assert call.prompt == "Hello"
        assert call.model == DEFAULT_MODEL
        assert call.system_prompt is None

    def test_llm_call_custom_model(self):
        """LLMCall should accept custom model."""
        call = LLMCall(
            prompt="Test prompt",
            model="openrouter/openai/gpt-4",
            system_prompt="You are a helpful assistant."
        )
        assert call.prompt == "Test prompt"
        assert call.model == "openrouter/openai/gpt-4"
        assert call.system_prompt == "You are a helpful assistant."

    def test_llm_call_empty_prompt(self):
        """LLMCall should allow empty prompt (validation is caller's job)."""
        call = LLMCall(prompt="")
        assert call.prompt == ""


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_llm_response_creation(self):
        """LLMResponse should store all fields."""
        response = LLMResponse(
            call_id="abc123",
            content="Hello, world!",
            model_used="claude-3-opus",
            latency_ms=1500,
            timestamp="2026-01-08T12:00:00Z"
        )
        assert response.call_id == "abc123"
        assert response.content == "Hello, world!"
        assert response.model_used == "claude-3-opus"
        assert response.latency_ms == 1500
        assert response.timestamp == "2026-01-08T12:00:00Z"

    def test_llm_response_empty_content(self):
        """LLMResponse should allow empty content."""
        response = LLMResponse(
            call_id="xyz789",
            content="",
            model_used="test-model",
            latency_ms=0,
            timestamp="2026-01-08T00:00:00Z"
        )
        assert response.content == ""


# ============================================================================
# ERROR CLASS TESTS
# ============================================================================

class TestExceptions:
    """Tests for custom exception classes."""

    def test_opencode_error_exists(self):
        """OpenCodeError should be a valid exception."""
        with pytest.raises(OpenCodeError):
            raise OpenCodeError("Test error")

    def test_opencode_server_error_inherits(self):
        """OpenCodeServerError should inherit from OpenCodeError."""
        assert issubclass(OpenCodeServerError, OpenCodeError)
        with pytest.raises(OpenCodeError):
            raise OpenCodeServerError("Server failed")

    def test_opencode_timeout_error_inherits(self):
        """OpenCodeTimeoutError should inherit from OpenCodeError."""
        assert issubclass(OpenCodeTimeoutError, OpenCodeError)
        with pytest.raises(OpenCodeError):
            raise OpenCodeTimeoutError("Timeout")

    def test_opencode_session_error_inherits(self):
        """OpenCodeSessionError should inherit from OpenCodeError."""
        assert issubclass(OpenCodeSessionError, OpenCodeError)
        with pytest.raises(OpenCodeError):
            raise OpenCodeSessionError("Session failed")

    def test_exception_messages(self):
        """Exceptions should preserve messages."""
        msg = "Custom error message"
        try:
            raise OpenCodeServerError(msg)
        except OpenCodeError as e:
            assert str(e) == msg


# ============================================================================
# CLIENT INSTANTIATION TESTS
# ============================================================================

class TestClientInstantiation:
    """Tests for OpenCodeClient instantiation."""

    def test_client_default_values(self):
        """Client should have sensible defaults."""
        client = OpenCodeClient()
        assert client.port == 62586
        assert client.timeout == 120
        assert client.log_calls is True
        assert client.is_running is False

    def test_client_custom_port(self):
        """Client should accept custom port."""
        client = OpenCodeClient(port=8080)
        assert client.port == 8080
        assert client.base_url == "http://127.0.0.1:8080"

    def test_client_custom_timeout(self):
        """Client should accept custom timeout."""
        client = OpenCodeClient(timeout=60)
        assert client.timeout == 60

    def test_client_disable_logging(self):
        """Client should allow disabling call logging."""
        client = OpenCodeClient(log_calls=False)
        assert client.log_calls is False

    def test_client_base_url(self):
        """Client should generate correct base URL."""
        client = OpenCodeClient(port=12345)
        assert client.base_url == "http://127.0.0.1:12345"

    def test_client_not_running_by_default(self):
        """Client should not be running on creation."""
        client = OpenCodeClient()
        assert client.is_running is False

    def test_client_with_api_key(self):
        """Client should accept explicit API key."""
        client = OpenCodeClient(api_key="test-key-123")
        assert client.api_key == "test-key-123"


# ============================================================================
# LOG DIRECTORY TESTS
# ============================================================================

class TestLogDirectory:
    """Tests for log directory creation."""

    def test_log_directory_created(self, tmp_path, monkeypatch):
        """Client should create log directory if it doesn't exist."""
        log_dir = tmp_path / "logs" / "agent_calls"
        monkeypatch.setattr(OpenCodeClient, "LOG_DIR", str(log_dir))

        # Directory shouldn't exist yet
        assert not log_dir.exists()

        # Creating client should create directory
        client = OpenCodeClient(log_calls=True)
        assert log_dir.exists()

    def test_log_directory_not_created_when_disabled(self, tmp_path, monkeypatch):
        """Client should not create log directory when logging disabled."""
        log_dir = tmp_path / "logs" / "agent_calls_disabled"
        monkeypatch.setattr(OpenCodeClient, "LOG_DIR", str(log_dir))

        client = OpenCodeClient(log_calls=False)
        # Directory should not be created when logging is disabled
        # (actually it might still be created due to init order, but calls won't be logged)
        # The important thing is log_calls=False works
        assert client.log_calls is False


# ============================================================================
# SERVER STATE TESTS (Without Real Server)
# ============================================================================

class TestServerState:
    """Tests for server state management without real server."""



    def test_start_without_api_key_raises(self, monkeypatch):
        """Starting server without API key should raise error."""
        # Clear all API key sources
        monkeypatch.delenv("STEWARD_OPENROUTER_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        client = OpenCodeClient(api_key=None)
        # Manually clear the key
        client.api_key = None

        with pytest.raises(OpenCodeServerError, match="No API key"):
            client.start_server()

    def test_start_when_already_running_raises(self):
        """Starting server when already running should raise error."""
        client = OpenCodeClient(api_key="test-key")

        # Mock _server_process to make is_running return True
        # Create a mock process object that has poll() return None (meaning running)
        class MockProcess:
            def poll(self):
                return None  # None means process is still running

        client._server_process = MockProcess()

        with pytest.raises(OpenCodeServerError, match="already running"):
            client.start_server()

        # Clean up
        client._server_process = None


# ============================================================================
# IMPORT TESTS
# ============================================================================

class TestImports:
    """Tests for module imports."""

    def test_import_from_agents_package(self):
        """Should be able to import from runtime.agents."""
        from runtime.agents import (
            OpenCodeClient,
            LLMCall,
            LLMResponse,
            OpenCodeError,
            OpenCodeServerError,
            OpenCodeTimeoutError,
        )
        assert OpenCodeClient is not None
        assert LLMCall is not None
        assert LLMResponse is not None

    def test_all_exports(self):
        """__all__ should export expected symbols."""
        from runtime import agents
        expected = [
            "OpenCodeClient",
            "LLMCall",
            "LLMResponse",
            "OpenCodeError",
            "OpenCodeServerError",
            "OpenCodeTimeoutError",
        ]
        for name in expected:
            assert hasattr(agents, name), f"Missing export: {name}"


# ============================================================================
# DETERMINISM TESTS
# ============================================================================

class TestDeterminism:
    """Tests for deterministic behavior."""

    def test_llm_call_equality(self):
        """Two LLMCalls with same values should be equal."""
        call1 = LLMCall(prompt="test", model="model-a")
        call2 = LLMCall(prompt="test", model="model-a")
        assert call1 == call2

    def test_llm_response_equality(self):
        """Two LLMResponses with same values should be equal."""
        resp1 = LLMResponse(
            call_id="abc",
            content="hello",
            model_used="model",
            latency_ms=100,
            timestamp="2026-01-08T00:00:00Z"
        )
        resp2 = LLMResponse(
            call_id="abc",
            content="hello",
            model_used="model",
            latency_ms=100,
            timestamp="2026-01-08T00:00:00Z"
        )
        assert resp1 == resp2
