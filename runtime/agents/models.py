"""
Model Resolution - Deterministic model selection for agent calls.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1.5

HOW TO CHANGE MODELS:
- Edit config/models.yaml
- Each agent has: model, endpoint, api_key_env, fallback
- See models.yaml for the full matrix
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml


# =============================================================================
# CANONICAL DEFAULTS (Single Source of Truth)
# =============================================================================
# All scripts and tests MUST import these constants instead of hardcoding.
# To change the default model/provider, edit ONLY here (and config/models.yaml).

DEFAULT_MODEL = "minimax-m2.1-free"
DEFAULT_PROVIDER = "zen_anthropic"
DEFAULT_ENDPOINT = "https://opencode.ai/zen/v1/messages"
DEFAULT_API_KEY_ENV = "ZEN_STEWARD_KEY"

# Fallback key names (in priority order)
API_KEY_FALLBACK_CHAIN = [
    "ZEN_STEWARD_KEY",
    "ZEN_API_KEY",
    "STEWARD_OPENROUTER_KEY",
    "OPENROUTER_API_KEY",
]


def validate_config() -> tuple[bool, str]:
    """
    Validate that required API keys are available.
    
    Returns:
        Tuple of (ok, message). If ok is False, message explains the issue.
    """
    for key_name in API_KEY_FALLBACK_CHAIN:
        if os.environ.get(key_name):
            return True, f"Config valid (using {key_name})"
    return False, f"Missing API key. Set one of: {', '.join(API_KEY_FALLBACK_CHAIN)}"


def get_api_key() -> Optional[str]:
    """Get the first available API key from the fallback chain."""
    for key_name in API_KEY_FALLBACK_CHAIN:
        key = os.environ.get(key_name)
        if key:
            return key
    return None


@dataclass
class AgentConfig:
    """Configuration for a specific agent."""
    provider: str
    model: str
    endpoint: str
    api_key_env: str
    fallback: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ModelConfig:
    """Model configuration per v0.3 spec §5.1.5."""
    
    default_chain: List[str] = field(default_factory=list)
    role_overrides: Dict[str, List[str]] = field(default_factory=dict)
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    
    # Default settings
    base_url: str = "https://opencode.ai/zen/v1/messages"
    timeout_seconds: int = 120
    max_retry_attempts: int = 3
    backoff_base_seconds: float = 1.0
    backoff_multiplier: float = 2.0


def load_model_config(config_path: str = "config/models.yaml") -> ModelConfig:
    """
    Load model configuration from YAML file.
    
    Args:
        config_path: Path to models.yaml relative to repo root
        
    Returns:
        ModelConfig with loaded settings
    """
    path = Path(config_path)
    if not path.exists():
        return ModelConfig(default_chain=["minimax-m2.1-free"])
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    if not data:
        return ModelConfig()
    
    model_selection = data.get("model_selection", {})
    zen_config = data.get("zen", {})
    retry = zen_config.get("retry", {})
    
    # Load per-agent configs
    agents_data = data.get("agents", {})
    agents: Dict[str, AgentConfig] = {}
    for role, cfg in agents_data.items():
        agents[role] = AgentConfig(
            provider=cfg.get("provider", "zen_anthropic"),
            model=cfg.get("model", "minimax-m2.1-free"),
            endpoint=cfg.get("endpoint", "https://opencode.ai/zen/v1/messages"),
            api_key_env=cfg.get("api_key_env", "ZEN_API_KEY"),
            fallback=cfg.get("fallback", []),
        )
    
    return ModelConfig(
        default_chain=model_selection.get("default_chain", []),
        role_overrides=model_selection.get("role_overrides", {}),
        agents=agents,
        base_url=zen_config.get("base_url", "https://opencode.ai/zen/v1/messages"),
        timeout_seconds=zen_config.get("timeout_seconds", 120),
        max_retry_attempts=retry.get("max_attempts", 3),
        backoff_base_seconds=retry.get("backoff_base_seconds", 1.0),
        backoff_multiplier=retry.get("backoff_multiplier", 2.0),
    )


def get_agent_config(role: str, config: Optional[ModelConfig] = None) -> AgentConfig:
    """
    Get the full configuration for a specific agent role.
    
    Args:
        role: Agent role (e.g., "designer", "builder", "steward")
        config: Model configuration (loads from file if None)
        
    Returns:
        AgentConfig with model, endpoint, api_key_env, and fallbacks
    """
    if config is None:
        config = load_model_config()
    
    if role in config.agents:
        return config.agents[role]
    
    # Fallback for unknown roles
    return AgentConfig(
        provider="zen_anthropic",
        model="minimax-m2.1-free",
        endpoint="https://opencode.ai/zen/v1/messages",
        api_key_env="ZEN_API_KEY",
        fallback=[],
    )


def get_api_key_for_role(role: str, config: Optional[ModelConfig] = None) -> Optional[str]:
    """
    Get the API key for a specific agent role.
    
    Args:
        role: Agent role
        config: Model configuration
        
    Returns:
        API key string or None if not found
    """
    agent_config = get_agent_config(role, config)
    return os.environ.get(agent_config.api_key_env)


def resolve_model_auto(
    role: str,
    config: Optional[ModelConfig] = None,
) -> Tuple[str, str, List[str]]:
    """
    Resolve "auto" to specific model deterministically.
    
    Per v0.3 spec §5.1.5:
    1. If role in agents: use that config
    2. If role in role_overrides: use that chain
    3. Otherwise: use default_chain
    
    Args:
        role: Agent role (e.g., "designer", "builder")
        config: Model configuration (loads from file if None)
        
    Returns:
        Tuple of (selected_model, selection_reason, full_chain)
    """
    if config is None:
        config = load_model_config()
    
    # Check for agent-specific config first
    if role in config.agents:
        agent = config.agents[role]
        chain = [agent.model] + [f.get("model", "") for f in agent.fallback if f.get("model")]
        return agent.model, "agent_config", chain
    
    # Check for role-specific override (legacy)
    if role in config.role_overrides:
        chain = config.role_overrides[role]
        if chain:
            return chain[0], "role_override", chain
    
    # Fall back to default chain
    if config.default_chain:
        return config.default_chain[0], "primary", config.default_chain
    
    # Ultimate fallback
    fallback = "minimax-m2.1-free"
    return fallback, "fallback", [fallback]


def get_model_chain(role: str, config: Optional[ModelConfig] = None) -> List[str]:
    """
    Get the full model fallback chain for a role.
    
    Args:
        role: Agent role
        config: Model configuration
        
    Returns:
        List of models in priority order
    """
    _, _, chain = resolve_model_auto(role, config)
    return chain
