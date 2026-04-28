from pathlib import Path
from unittest.mock import patch

import pytest

from runtime.agents.api import AgentAPIError, AgentCall, call_agent_cli
from runtime.agents.cli_dispatch import CLIDispatchResult, CLIProvider
from runtime.agents.models import load_model_config


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_configured_cli_dispatch_policy_is_codex_only() -> None:
    config = load_model_config(str(REPO_ROOT / "config" / "models.yaml"))

    cli_roles = {
        role: agent
        for role, agent in config.agents.items()
        if agent.dispatch_mode == "cli"
    }
    assert cli_roles, "expected at least one CLI-dispatched role"

    for role, agent in cli_roles.items():
        assert agent.cli_provider == "codex", f"{role} must dispatch through Codex"
        assert agent.cli_fallback == "", f"{role} must not fall back to another CLI EA"
        assert getattr(agent, "allow_api_fallback", None) is False, (
            f"{role} must fail closed instead of falling back to API dispatch"
        )

    enabled_cli_providers = [
        name for name, provider in config.cli_providers.items() if provider.enabled
    ]
    assert enabled_cli_providers == ["codex"]

    assert config.council_provider_overrides
    assert set(config.council_provider_overrides.values()) == {"codex"}


def test_build_loop_workflow_requires_codex_only_cli() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "build_loop_nightly.yml").read_text(
        encoding="utf-8"
    )

    assert "command -v codex" in workflow
    assert "for tool in claude codex gemini" not in workflow
    assert "At least one of (claude, codex, gemini)" not in workflow


@patch("runtime.agents.api.call_agent")
@patch("runtime.agents.cli_dispatch.dispatch_cli_agent")
@patch("runtime.agents.api._load_role_prompt", return_value=("system prompt", "sha256:abc"))
def test_cli_dispatch_can_fail_closed_when_api_fallback_is_disabled(
    mock_prompt, mock_dispatch, mock_call_agent
) -> None:
    config = load_model_config(str(REPO_ROOT / "config" / "models.yaml"))
    agent = config.agents["builder"]
    assert agent.cli_provider == "codex"
    setattr(agent, "allow_api_fallback", False)

    mock_dispatch.return_value = CLIDispatchResult(
        output="",
        exit_code=1,
        latency_ms=100,
        provider=CLIProvider.CODEX,
        model="",
        partial=False,
        errors=["usage limit"],
    )

    with pytest.raises(AgentAPIError, match="API fallback disabled"):
        call_agent_cli(AgentCall(role="builder", packet={"task": "test"}), config=config)

    mock_call_agent.assert_not_called()
