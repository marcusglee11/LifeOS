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

                raw = _response_to_dict(response, lens_name)
                run_type = getattr(plan_core, "run_type", "review")
                if isinstance(raw, dict) and "claims" not in raw and "verdict" in raw:
                    raw = _normalize_v1_to_v2_lens(raw, lens_name, run_type)
                return raw

            logger.warning(
                "CLI provider %s not available for lens %s; using API",
                cli_provider_name, lens_name,
            )

        # Standard API dispatch (default path)
        logger.info("Lens %s → API dispatch (role=%s, model=%s)", lens_name, role, model)
        response = call_agent(call, config=config)
        raw = _response_to_dict(response, lens_name)
        # Normalize v1 seat format → v2 lens format if the model returned the old schema.
        # Some models ignore the updated prompt and produce verdict/key_findings/risks/fixes
        # instead of the required run_type/lens_name/notes/claims schema.
        run_type = getattr(plan_core, "run_type", "review")
        if isinstance(raw, dict) and "claims" not in raw and "verdict" in raw:
            raw = _normalize_v1_to_v2_lens(raw, lens_name, run_type)
        return raw

    return executor


def _normalize_v1_to_v2_lens(
    output: dict[str, Any], lens_name: str, run_type: str
) -> dict[str, Any]:
    """Convert v1 seat output (verdict/key_findings/risks/fixes) to v2 lens format.

    Called when a model ignores the updated prompt and returns the old schema.
    Preserves all substantive content; translates structure to satisfy validate_lens_output.
    """
    claims: list[dict[str, Any]] = []
    for section, category in [
        ("key_findings", "finding"),
        ("risks", "risk"),
        ("fixes", "fix"),
    ]:
        items = output.get(section) or []
        if not isinstance(items, list):
            continue
        for idx, item in enumerate(items):
            statement = str(item)
            evidence_refs: list[str] = []
            if "REF:" in statement:
                # Extract inline REF: tokens
                for part in statement.split("REF:")[1:]:
                    token = part.split()[0] if part.split() else ""
                    if token:
                        evidence_refs.append(f"REF:{token}")
            claims.append({
                "claim_id": f"{category[0].upper()}{idx + 1}",
                "statement": statement,
                "evidence_refs": evidence_refs,
                "category": category,
            })

    op_view = output.get("operator_view", "")
    notes_text: str
    if isinstance(op_view, str):
        notes_text = op_view[:200].strip() or f"{lens_name} review complete."
    elif isinstance(op_view, list) and op_view:
        notes_text = str(op_view[0])[:200]
    else:
        notes_text = f"{lens_name} review complete."

    normalized: dict[str, Any] = {
        "run_type": run_type,
        "lens_name": lens_name,
        "verdict_recommendation": output.get("verdict", ""),
        "confidence": output.get("confidence", "medium"),
        "notes": notes_text,
        "operator_view": op_view or notes_text,
        "claims": claims,
    }
    # Preserve non-conflicting extra fields (complexity_budget, assumptions, etc.)
    skip = {"verdict", "key_findings", "risks", "fixes", "run_type", "lens_name",
            "claims", "notes", "confidence", "operator_view", "verdict_recommendation"}
    for k, v in output.items():
        if k not in skip:
            normalized[k] = v
    return normalized


def _response_to_dict(response: AgentResponse, lens_name: str) -> dict[str, Any]:
    """Convert AgentResponse to dict suitable for schema gate validation."""
    if response.packet:
        # Preserve actual execution metadata even when provider returned a structured packet.
        packet = dict(response.packet)
        packet.setdefault("model_used", response.model_used)
        packet.setdefault("model_version", response.model_version)
        return packet

    # If no structured packet, wrap raw content
    return {
        "lens_name": lens_name,
        "content": response.content,
        "model_used": response.model_used,
    }
