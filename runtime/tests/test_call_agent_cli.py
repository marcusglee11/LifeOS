"""
Tests for call_agent_cli - CLI dispatch integration in agent API layer.

Validates routing logic (CLI vs API fallback), AgentResponse wrapping,
hash chain logging, and error handling.
"""

import hashlib
from unittest.mock import patch, MagicMock

import pytest

from runtime.agents.api import call_agent_cli, AgentCall, AgentResponse, AgentAPIError
from runtime.agents.cli_dispatch import (
    CLIProvider,
    CLIDispatchConfig,
    CLIDispatchResult,
    CLIProviderNotFound,
)
from runtime.agents.models import (
    ModelConfig,
    AgentConfig,
    CLIProviderConfig,
)


def _make_cli_config() -> ModelConfig:
    """Build a ModelConfig with CLI dispatch enabled for council_reviewer."""
    return ModelConfig(
        default_chain=["claude-sonnet-4-5"],
        agents={
            "council_reviewer": AgentConfig(
                provider="zen",
                model="gpt-5.3-codex",
                endpoint="https://example.com",
                api_key_env="TEST_KEY",
                dispatch_mode="cli",
                cli_provider="codex",
            ),
            "steward": AgentConfig(
                provider="zen",
                model="claude-sonnet-4-5",
                endpoint="https://example.com",
                api_key_env="TEST_KEY",
                dispatch_mode="api",
            ),
        },
        cli_providers={
            "codex": CLIProviderConfig(
                binary="codex",
                default_model="gpt-5.3-codex",
                timeout_seconds=600,
                sandbox=True,
                enabled=True,
            ),
        },
    )


def _make_api_only_config() -> ModelConfig:
    """Build a ModelConfig with only API dispatch."""
    return ModelConfig(
        default_chain=["claude-sonnet-4-5"],
        agents={
            "council_reviewer": AgentConfig(
                provider="zen",
                model="claude-sonnet-4-5",
                endpoint="https://example.com",
                api_key_env="TEST_KEY",
                dispatch_mode="api",
            ),
        },
    )


class TestCallAgentCLIRouting:
    """Test that call_agent_cli routes correctly between CLI and API."""

    @patch("runtime.agents.api.call_agent")
    def test_falls_back_to_api_when_not_cli_dispatch(self, mock_call_agent):
        """Roles with dispatch_mode='api' should fall back to call_agent()."""
        mock_call_agent.return_value = AgentResponse(
            call_id="test", call_id_audit="test", role="steward",
            model_used="claude-sonnet-4-5", model_version="claude-sonnet-4-5",
            content="ok", packet=None,
        )
        config = _make_cli_config()
        call = AgentCall(role="steward", packet={"task": "test"})
        result = call_agent_cli(call, config=config)

        mock_call_agent.assert_called_once()
        assert result.content == "ok"

    @patch("runtime.agents.api.call_agent")
    def test_falls_back_on_unknown_cli_provider(self, mock_call_agent):
        """Unknown cli_provider string should gracefully fall back to API."""
        mock_call_agent.return_value = AgentResponse(
            call_id="test", call_id_audit="test", role="council_reviewer",
            model_used="claude-sonnet-4-5", model_version="claude-sonnet-4-5",
            content="ok", packet=None,
        )
        config = ModelConfig(
            default_chain=["claude-sonnet-4-5"],
            agents={
                "council_reviewer": AgentConfig(
                    provider="zen", model="claude-sonnet-4-5",
                    endpoint="https://example.com", api_key_env="TEST_KEY",
                    dispatch_mode="cli", cli_provider="unknown_provider",
                ),
            },
        )
        call = AgentCall(role="council_reviewer", packet={"task": "test"})
        result = call_agent_cli(call, config=config)

        mock_call_agent.assert_called_once()


class TestCallAgentCLIDispatch:
    """Test successful CLI dispatch and AgentResponse wrapping."""

    @patch("runtime.agents.cli_dispatch.dispatch_cli_agent")
    @patch("runtime.agents.api._load_role_prompt", return_value=("system prompt", "sha256:abc"))
    def test_successful_cli_dispatch(self, mock_prompt, mock_dispatch):
        mock_dispatch.return_value = CLIDispatchResult(
            output="verdict: ACCEPT\nclaims:\n  - architecture is sound",
            exit_code=0,
            latency_ms=5000,
            provider=CLIProvider.CODEX,
            model="gpt-5.3-codex",
        )
        config = _make_cli_config()
        call = AgentCall(role="council_reviewer", packet={"task": "review"})
        result = call_agent_cli(call, config=config)

        assert isinstance(result, AgentResponse)
        assert result.role == "council_reviewer"
        assert result.model_used == "gpt-5.3-codex"
        assert "codex/" in result.model_version
        assert result.latency_ms == 5000
        assert "ACCEPT" in result.content
        assert result.call_id.startswith("sha256:")

    @patch("runtime.agents.cli_dispatch.dispatch_cli_agent")
    @patch("runtime.agents.api._load_role_prompt", return_value=("system prompt", "sha256:abc"))
    def test_partial_output_returns_response(self, mock_prompt, mock_dispatch):
        """Partial results (timeout) should still return an AgentResponse."""
        mock_dispatch.return_value = CLIDispatchResult(
            output="partial analysis...",
            exit_code=-1,
            latency_ms=600000,
            provider=CLIProvider.CODEX,
            model="gpt-5.3-codex",
            partial=True,
            errors=["Timeout after 600s"],
        )
        config = _make_cli_config()
        call = AgentCall(role="council_reviewer", packet={"task": "review"})
        result = call_agent_cli(call, config=config)

        assert isinstance(result, AgentResponse)
        assert "partial analysis" in result.content

    @patch("runtime.agents.cli_dispatch.dispatch_cli_agent")
    @patch("runtime.agents.api._load_role_prompt", return_value=("system prompt", "sha256:abc"))
    def test_complete_failure_raises(self, mock_prompt, mock_dispatch):
        """Non-zero exit with no partial output should raise."""
        mock_dispatch.return_value = CLIDispatchResult(
            output="",
            exit_code=1,
            latency_ms=100,
            provider=CLIProvider.CODEX,
            model="gpt-5.3-codex",
            partial=False,
            errors=["Model not available"],
        )
        config = _make_cli_config()
        call = AgentCall(role="council_reviewer", packet={"task": "review"})

        with pytest.raises(AgentAPIError, match="CLI agent codex failed"):
            call_agent_cli(call, config=config)


class TestCallAgentCLIFallback:
    """Test graceful fallback when CLI provider is not available."""

    @patch("runtime.agents.api.call_agent")
    @patch("runtime.agents.cli_dispatch.dispatch_cli_agent", side_effect=CLIProviderNotFound("codex not found"))
    @patch("runtime.agents.api._load_role_prompt", return_value=("system prompt", "sha256:abc"))
    def test_falls_back_to_api_on_provider_not_found(self, mock_prompt, mock_dispatch, mock_call_agent):
        mock_call_agent.return_value = AgentResponse(
            call_id="test", call_id_audit="test", role="council_reviewer",
            model_used="claude-sonnet-4-5", model_version="claude-sonnet-4-5",
            content="api fallback", packet=None,
        )
        config = _make_cli_config()
        call = AgentCall(role="council_reviewer", packet={"task": "review"})
        result = call_agent_cli(call, config=config)

        mock_call_agent.assert_called_once()
        assert result.content == "api fallback"


class TestCallAgentCLIHashChain:
    """Test that CLI dispatch results are logged to the hash chain."""

    @patch("runtime.agents.cli_dispatch.dispatch_cli_agent")
    @patch("runtime.agents.api._load_role_prompt", return_value=("system prompt", "sha256:abc"))
    def test_logs_to_hash_chain(self, mock_prompt, mock_dispatch):
        from runtime.agents.logging import AgentCallLogger

        mock_dispatch.return_value = CLIDispatchResult(
            output="result", exit_code=0, latency_ms=1000,
            provider=CLIProvider.CODEX, model="gpt-5.3-codex",
        )
        logger_instance = AgentCallLogger()
        config = _make_cli_config()
        call = AgentCall(role="council_reviewer", packet={"task": "review"})
        call_agent_cli(call, logger_instance=logger_instance, config=config)

        assert len(logger_instance.entries) == 1
        entry = logger_instance.entries[0]
        assert entry.role == "council_reviewer"
        assert entry.status == "success"
        assert entry.latency_ms == 1000
