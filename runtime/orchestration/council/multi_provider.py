"""
Multi-provider lens executor for Council Runtime v2.

Creates lens executors that can route different council lenses to different
LLM providers (API or CLI), enabling heterogeneous council reviews where
e.g. Codex handles architecture review, Gemini handles security, and
Claude handles synthesis.

Architecture:
  - Sits alongside lenses.py (per-lens dispatch with retry/waiver)
  - Provides a factory function that returns a LensExecutor compatible
    with CouncilFSMv2's constructor
  - Uses config/models.yaml provider_assignments to route lenses
  - Falls back to API dispatch when CLI provider is unavailable
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Mapping, Optional

from runtime.agents.api import AgentCall, AgentResponse, call_agent, call_agent_cli
from runtime.agents.models import (
    AgentConfig,
    CLIProviderConfig,
    ModelConfig,
    get_agent_config,
    get_cli_provider_config,
    load_model_config,
)

logger = logging.getLogger(__name__)


# Type matching CouncilFSMv2's LensExecutor signature
LensExecutor = Callable[
    [str, Mapping[str, Any], Any, int],  # lens_name, ccp, plan_core, retry_count
    dict[str, Any] | str,
]


def build_multi_provider_executor(
    config: Optional[ModelConfig] = None,
    provider_overrides: Optional[dict[str, str]] = None,
) -> LensExecutor:
    """
    Build a lens executor that routes lenses to different providers.

    Each lens can be dispatched to a different provider/model combination
    based on config. Provider routing is determined by:
      1. provider_overrides dict (lens_name → cli_provider_name)
      2. Agent config dispatch_mode for the lens's mapped role
      3. Default: API dispatch via call_agent()

    Args:
        config: ModelConfig (loaded from file if None).
        provider_overrides: Optional dict mapping lens names to CLI provider
            names (e.g. {"Architecture": "codex", "Security": "gemini"}).

    Returns:
        A callable compatible with CouncilFSMv2's LensExecutor type.
    """
    if config is None:
        config = load_model_config()

    overrides = provider_overrides or {}

    def executor(
        lens_name: str,
        ccp: Mapping[str, Any],
        plan_core: Any,
        retry_count: int,
    ) -> dict[str, Any] | str:
        """
        Execute a single lens, routing to the appropriate provider.

        Checks provider_overrides first, then agent config dispatch_mode,
        and falls back to standard API dispatch.
        """
        model = plan_core.model_assignments.get(lens_name, "auto")
        role = plan_core.lens_role_map.get(lens_name, "council_reviewer")

        # Build the AgentCall
        call = AgentCall(
            role=role,
            packet={
                "lens": lens_name,
                "ccp": dict(ccp) if isinstance(ccp, Mapping) else ccp,
                "retry": retry_count,
                "tier": getattr(plan_core, "tier", "T1"),
                "run_type": getattr(plan_core, "run_type", "review"),
            },
            model=model,
        )

        # Check if this lens has a CLI provider override
        cli_provider_name = overrides.get(lens_name)

        if cli_provider_name:
            # Verify the CLI provider is configured and enabled
            cli_cfg = get_cli_provider_config(cli_provider_name, config)
            if cli_cfg and cli_cfg.enabled:
                logger.info(
                    "Lens %s → CLI provider %s (override)",
                    lens_name, cli_provider_name,
                )
                # Temporarily set the agent config for CLI dispatch
                temp_agent = AgentConfig(
                    provider="cli",
                    model=model,
                    endpoint="",
                    api_key_env="",
                    dispatch_mode="cli",
                    cli_provider=cli_provider_name,
                )
                # Inject into config for this call
                original = config.agents.get(role)
                config.agents[role] = temp_agent
                try:
                    response = call_agent_cli(call, config=config)
                finally:
                    # Restore original config
                    if original:
                        config.agents[role] = original
                    else:
                        config.agents.pop(role, None)

                return _response_to_dict(response, lens_name)

            logger.warning(
                "CLI provider %s not available for lens %s; using API",
                cli_provider_name, lens_name,
            )

        # Standard API dispatch (default path)
        logger.info("Lens %s → API dispatch (role=%s, model=%s)", lens_name, role, model)
        response = call_agent(call, config=config)
        return _response_to_dict(response, lens_name)

    return executor


def _response_to_dict(response: AgentResponse, lens_name: str) -> dict[str, Any]:
    """Convert AgentResponse to dict suitable for schema gate validation."""
    if response.packet:
        return response.packet

    # If no structured packet, wrap raw content
    return {
        "lens_name": lens_name,
        "content": response.content,
        "model_used": response.model_used,
    }
