"""
Tests for multi-provider council lens dispatch.

Validates that the multi-provider executor routes lenses to different
providers based on configuration and overrides.
"""

from unittest.mock import patch, MagicMock
from types import SimpleNamespace

import pytest

from runtime.orchestration.council.multi_provider import (
    build_multi_provider_executor,
    _response_to_dict,
)
from runtime.agents.api import AgentResponse
from runtime.agents.models import (
    ModelConfig,
    AgentConfig,
    CLIProviderConfig,
)


def _make_plan_core(
    lenses=("Architecture", "Security"),
    model_assignments=None,
    lens_role_map=None,
):
    """Create a minimal plan_core-like object for testing."""
    return SimpleNamespace(
        required_lenses=lenses,
        model_assignments=model_assignments or {
            "Architecture": "gpt-5.3-codex",
            "Security": "gemini-3-pro",
        },
        lens_role_map=lens_role_map or {
            "Architecture": "council_reviewer",
            "Security": "council_reviewer_security",
        },
        tier="T1",
        run_type="review",
    )


def _make_config_with_cli():
    return ModelConfig(
        default_chain=["claude-sonnet-4-5"],
        agents={
            "council_reviewer": AgentConfig(
                provider="zen", model="claude-sonnet-4-5",
                endpoint="https://example.com", api_key_env="TEST_KEY",
            ),
            "council_reviewer_security": AgentConfig(
                provider="zen", model="claude-sonnet-4-5",
                endpoint="https://example.com", api_key_env="TEST_KEY",
            ),
        },
        cli_providers={
            "codex": CLIProviderConfig(
                binary="codex", default_model="gpt-5.3-codex",
                timeout_seconds=600, sandbox=True, enabled=True,
            ),
            "gemini": CLIProviderConfig(
                binary="gemini", default_model="gemini-3-pro",
                timeout_seconds=600, sandbox=True, enabled=True,
            ),
        },
    )


class TestBuildMultiProviderExecutor:
    """Test executor factory construction."""

    def test_returns_callable(self):
        config = _make_config_with_cli()
        executor = build_multi_provider_executor(config=config)
        assert callable(executor)

    @patch("runtime.orchestration.council.multi_provider.call_agent")
    def test_default_routes_to_api(self, mock_call):
        """Without overrides, all lenses should use API dispatch."""
        mock_call.return_value = AgentResponse(
            call_id="test", call_id_audit="test", role="council_reviewer",
            model_used="claude-sonnet-4-5", model_version="claude-sonnet-4-5",
            content="review complete", packet={"verdict": "Accept"},
        )
        config = _make_config_with_cli()
        executor = build_multi_provider_executor(config=config)
        plan = _make_plan_core()

        result = executor("Architecture", {"task": "review"}, plan, 0)

        mock_call.assert_called_once()
        # v1 packet {"verdict": "Accept"} is normalized to v2 schema by _normalize_v1_to_v2_lens
        assert result["verdict_recommendation"] == "Accept"
        assert result["model_used"] == "claude-sonnet-4-5"
        assert result["model_version"] == "claude-sonnet-4-5"

    @patch("runtime.orchestration.council.multi_provider.call_agent_cli")
    def test_override_routes_to_cli(self, mock_cli_call):
        """Lens with CLI override should route to call_agent_cli."""
        mock_cli_call.return_value = AgentResponse(
            call_id="test", call_id_audit="test", role="council_reviewer",
            model_used="gpt-5.3-codex", model_version="codex/gpt-5.3-codex",
            content="architecture analysis", packet={"verdict": "Accept"},
        )
        config = _make_config_with_cli()
        executor = build_multi_provider_executor(
            config=config,
            provider_overrides={"Architecture": "codex"},
        )
        plan = _make_plan_core()

        result = executor("Architecture", {"task": "review"}, plan, 0)

        mock_cli_call.assert_called_once()
        # v1 packet {"verdict": "Accept"} is normalized to v2 schema by _normalize_v1_to_v2_lens
        assert result["verdict_recommendation"] == "Accept"
        assert result["model_used"] == "gpt-5.3-codex"
        assert result["model_version"] == "codex/gpt-5.3-codex"

    @patch("runtime.orchestration.council.multi_provider.call_agent")
    def test_disabled_cli_falls_back_to_api(self, mock_call):
        """CLI provider that is disabled should fall back to API."""
        mock_call.return_value = AgentResponse(
            call_id="test", call_id_audit="test", role="council_reviewer",
            model_used="claude-sonnet-4-5", model_version="claude-sonnet-4-5",
            content="ok", packet={"verdict": "Accept"},
        )
        config = ModelConfig(
            default_chain=["claude-sonnet-4-5"],
            agents={
                "council_reviewer": AgentConfig(
                    provider="zen", model="claude-sonnet-4-5",
                    endpoint="https://example.com", api_key_env="TEST_KEY",
                ),
            },
            cli_providers={
                "codex": CLIProviderConfig(
                    binary="codex", enabled=False,  # disabled
                ),
            },
        )
        executor = build_multi_provider_executor(
            config=config,
            provider_overrides={"Architecture": "codex"},
        )
        plan = _make_plan_core()

        result = executor("Architecture", {"task": "review"}, plan, 0)

        # Should have fallen back to API
        mock_call.assert_called_once()

    @patch("runtime.orchestration.council.multi_provider.call_agent")
    def test_unconfigured_cli_falls_back_to_api(self, mock_call):
        """CLI provider not in config should fall back to API."""
        mock_call.return_value = AgentResponse(
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
                ),
            },
        )
        executor = build_multi_provider_executor(
            config=config,
            provider_overrides={"Architecture": "nonexistent"},
        )
        plan = _make_plan_core()

        result = executor("Architecture", {"task": "review"}, plan, 0)

        mock_call.assert_called_once()


class TestMultiProviderMixedRouting:
    """Test mixed routing where different lenses go to different providers."""

    @patch("runtime.orchestration.council.multi_provider.call_agent")
    @patch("runtime.orchestration.council.multi_provider.call_agent_cli")
    def test_mixed_routing(self, mock_cli, mock_api):
        """Architecture→codex CLI, Security→API."""
        mock_cli.return_value = AgentResponse(
            call_id="cli", call_id_audit="cli", role="council_reviewer",
            model_used="gpt-5.3-codex", model_version="codex/gpt-5.3-codex",
            content="arch analysis", packet={"lens": "Architecture", "verdict": "Accept"},
        )
        mock_api.return_value = AgentResponse(
            call_id="api", call_id_audit="api", role="council_reviewer_security",
            model_used="claude-sonnet-4-5", model_version="claude-sonnet-4-5",
            content="security review", packet={"lens": "Security", "verdict": "Accept"},
        )
        config = _make_config_with_cli()
        executor = build_multi_provider_executor(
            config=config,
            provider_overrides={"Architecture": "codex"},
            # Security has no override → goes to API
        )
        plan = _make_plan_core()

        # Dispatch Architecture → CLI
        arch_result = executor("Architecture", {"task": "review"}, plan, 0)
        assert arch_result["lens"] == "Architecture"
        mock_cli.assert_called_once()

        # Dispatch Security → API
        sec_result = executor("Security", {"task": "review"}, plan, 0)
        assert sec_result["lens"] == "Security"
        mock_api.assert_called_once()


class TestResponseToDict:
    def test_with_packet(self):
        response = AgentResponse(
            call_id="test", call_id_audit="test", role="reviewer",
            model_used="claude", model_version="claude",
            content="raw text", packet={"verdict": "Accept"},
        )
        assert _response_to_dict(response, "Architecture") == {
            "verdict": "Accept",
            "model_used": "claude",
            "model_version": "claude",
        }

    def test_without_packet(self):
        response = AgentResponse(
            call_id="test", call_id_audit="test", role="reviewer",
            model_used="claude", model_version="claude",
            content="raw analysis text", packet=None,
        )
        result = _response_to_dict(response, "Architecture")
        assert result["lens_name"] == "Architecture"
        assert result["content"] == "raw analysis text"
        assert result["model_used"] == "claude"


class TestDelegatedRoleWithOverride:
    """Test that delegated roles route correctly via multi_provider synthetic config."""

    @patch("runtime.orchestration.council.multi_provider.call_agent_cli")
    def test_delegated_role_with_override_routes_via_synthetic_config(self, mock_cli):
        """Delegated roles: multi_provider injects synthetic dispatch_mode='cli' — no DelegatedDispatchError raised."""
        mock_cli.return_value = AgentResponse(
            call_id="test", call_id_audit="test", role="council_reviewer",
            model_used="claude_code/default", model_version="claude_code/default",
            content="architecture review complete", packet={"verdict": "Accept"},
        )
        # Config has council_reviewer.dispatch_mode="delegated", but override routes it via CLI
        config = ModelConfig(
            default_chain=["claude-sonnet-4-5"],
            agents={
                "council_reviewer": AgentConfig(
                    provider="zen", model="claude-sonnet-4-5",
                    endpoint="https://example.com", api_key_env="TEST_KEY",
                    dispatch_mode="delegated",
                ),
            },
            cli_providers={
                "claude_code": CLIProviderConfig(
                    binary="claude", default_model="",
                    timeout_seconds=600, sandbox=True, enabled=True,
                ),
            },
        )
        executor = build_multi_provider_executor(
            config=config,
            provider_overrides={"Architecture": "claude_code"},
        )
        plan = _make_plan_core(lenses=("Architecture",), lens_role_map={"Architecture": "council_reviewer"})

        # Should NOT raise DelegatedDispatchError — synthetic config overrides dispatch_mode to "cli"
        result = executor("Architecture", {"task": "review"}, plan, 0)

        mock_cli.assert_called_once()
        # Verify synthetic config was used (dispatch_mode="cli" in the call)
        call_args = mock_cli.call_args
        config_arg = call_args.kwargs.get("config")
        if config_arg is None and len(call_args.args) > 1:
            config_arg = call_args.args[1]
        if config_arg is not None:
            assert config_arg.agents["council_reviewer"].dispatch_mode == "cli"
