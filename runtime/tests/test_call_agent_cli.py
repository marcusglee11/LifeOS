"""
Tests for call_agent_cli - CLI dispatch integration in agent API layer.

Validates routing logic (CLI vs API fallback), AgentResponse wrapping,
hash chain logging, and error handling.
"""

import hashlib
from unittest.mock import patch, MagicMock

import pytest


from runtime.agents.api import call_agent, call_agent_cli, AgentCall, AgentResponse, AgentAPIError, DelegatedDispatchError
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

    @patch("runtime.agents.api.call_agent")
    @patch("runtime.agents.cli_dispatch.dispatch_cli_agent")
    def test_require_usage_forces_api_path(self, mock_dispatch, mock_call_agent):
        """CLI path should defer to API when token usage accounting is required."""
        mock_call_agent.return_value = AgentResponse(
            call_id="test",
            call_id_audit="test",
            role="council_reviewer",
            model_used="claude-sonnet-4-5",
            model_version="claude-sonnet-4-5",
            content="api usage response",
            packet=None,
            usage={"input_tokens": 5, "output_tokens": 3, "total_tokens": 8},
        )
        config = _make_cli_config()
        call = AgentCall(
            role="council_reviewer",
            packet={"task": "review"},
            require_usage=True,
        )

        result = call_agent_cli(call, config=config)

        mock_call_agent.assert_called_once()
        mock_dispatch.assert_not_called()
        assert result.usage["total_tokens"] == 8


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
        assert result.model_used == "codex/default"
        assert result.model_version == "codex/default"
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

    @patch("runtime.agents.api.call_agent")
    @patch("runtime.agents.cli_dispatch.dispatch_cli_agent")
    @patch("runtime.agents.api._load_role_prompt", return_value=("system prompt", "sha256:abc"))
    def test_complete_failure_falls_back_to_api(self, mock_prompt, mock_dispatch, mock_call_agent):
        """Non-zero exit with no partial should fall back to API (not raise)."""
        mock_dispatch.return_value = CLIDispatchResult(
            output="", exit_code=1, latency_ms=100,
            provider=CLIProvider.CODEX, model="",
            partial=False, errors=["Model not available"],
        )
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

    @patch("runtime.agents.api.call_agent")
    @patch("runtime.agents.cli_dispatch.dispatch_cli_agent")
    @patch("runtime.agents.api._load_role_prompt", return_value=("system prompt", "sha256:abc"))
    def test_secondary_cli_fallback(self, mock_prompt, mock_dispatch, mock_call_agent):
        """When primary CLI fails, secondary CLI (cli_fallback) is tried."""
        from runtime.agents.models import ModelConfig, AgentConfig, CLIProviderConfig
        # First call (primary codex) → non-zero exit; second call (gemini) → success
        mock_dispatch.side_effect = [
            CLIDispatchResult(output="", exit_code=1, latency_ms=50,
                              provider=CLIProvider.CODEX, model="", partial=False, errors=["fail"]),
            CLIDispatchResult(output="gemini output", exit_code=0, latency_ms=2000,
                              provider=CLIProvider.GEMINI, model="", partial=False),
        ]
        config = ModelConfig(
            default_chain=["claude-sonnet-4-5"],
            agents={
                "council_reviewer": AgentConfig(
                    provider="zen", model="claude-sonnet-4-5",
                    endpoint="https://example.com", api_key_env="TEST_KEY",
                    dispatch_mode="cli", cli_provider="codex", cli_fallback="gemini",
                ),
            },
            cli_providers={
                "codex": CLIProviderConfig(binary="codex", enabled=True, timeout_seconds=600, sandbox=True),
                "gemini": CLIProviderConfig(binary="gemini", enabled=True, timeout_seconds=600, sandbox=True),
            },
        )
        call = AgentCall(role="council_reviewer", packet={"task": "review"})
        result = call_agent_cli(call, config=config)

        assert mock_dispatch.call_count == 2
        assert result.model_used == "gemini/default"
        assert "gemini output" in result.content
        mock_call_agent.assert_not_called()


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


def _make_delegated_config() -> ModelConfig:
    """Build a ModelConfig with dispatch_mode='delegated' for council_reviewer."""
    return ModelConfig(
        default_chain=["claude-sonnet-4-5"],
        agents={
            "council_reviewer": AgentConfig(
                provider="zen",
                model="claude-sonnet-4-5",
                endpoint="https://example.com",
                api_key_env="TEST_KEY",
                dispatch_mode="delegated",
            ),
        },
    )


class TestDelegatedDispatchError:
    """Test that delegated roles raise DelegatedDispatchError when called directly."""

    def test_delegated_dispatch_error_is_agent_api_error(self):
        """Delegated dispatch failures should preserve AgentAPIError contract."""
        assert issubclass(DelegatedDispatchError, AgentAPIError)

    def test_delegated_dispatch_direct_call_agent_raises(self):
        """call_agent() with delegated role raises DelegatedDispatchError."""
        config = _make_delegated_config()
        call = AgentCall(role="council_reviewer", packet={})
        with pytest.raises(DelegatedDispatchError, match="delegated dispatch"):
            call_agent(call, config=config)

    def test_delegated_dispatch_direct_call_agent_cli_raises(self):
        """call_agent_cli() with delegated role raises DelegatedDispatchError."""
        config = _make_delegated_config()
        call = AgentCall(role="council_reviewer", packet={})
        with pytest.raises(DelegatedDispatchError, match="delegated dispatch"):
            call_agent_cli(call, config=config)
