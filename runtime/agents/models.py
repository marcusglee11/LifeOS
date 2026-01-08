"""
Model Resolution - Deterministic model selection for agent calls.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1.5
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml


@dataclass
class ModelConfig:
    """Model configuration per v0.3 spec §5.1.5."""
    
    default_chain: List[str] = field(default_factory=list)
    role_overrides: Dict[str, List[str]] = field(default_factory=dict)
    
    # OpenRouter settings
    base_url: str = "https://openrouter.ai/api/v1"
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
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is malformed
    """
    path = Path(config_path)
    if not path.exists():
        # Return defaults if config doesn't exist
        return ModelConfig(
            default_chain=["x-ai/grok-4.1-fast"],
        )
    
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    if not data:
        return ModelConfig()
    
    model_selection = data.get("model_selection", {})
    openrouter = data.get("openrouter", {})
    retry = openrouter.get("retry", {})
    
    return ModelConfig(
        default_chain=model_selection.get("default_chain", []),
        role_overrides=model_selection.get("role_overrides", {}),
        base_url=openrouter.get("base_url", "https://openrouter.ai/api/v1"),
        timeout_seconds=openrouter.get("timeout_seconds", 120),
        max_retry_attempts=retry.get("max_attempts", 3),
        backoff_base_seconds=retry.get("backoff_base_seconds", 1.0),
        backoff_multiplier=retry.get("backoff_multiplier", 2.0),
    )


def resolve_model_auto(
    role: str,
    config: Optional[ModelConfig] = None,
) -> Tuple[str, str, List[str]]:
    """
    Resolve "auto" to specific model deterministically.
    
    Per v0.3 spec §5.1.5:
    1. If role in role_overrides: use that chain
    2. Otherwise: use default_chain
    3. Return first model in chain (availability check deferred to call time)
    
    Args:
        role: Agent role (e.g., "designer", "builder")
        config: Model configuration (loads from file if None)
        
    Returns:
        Tuple of (selected_model, selection_reason, full_chain)
        - selected_model: First model in chain
        - selection_reason: "primary" or "role_override"
        - full_chain: Complete fallback chain for retry logic
    """
    if config is None:
        config = load_model_config()
    
    # Check for role-specific override
    if role in config.role_overrides:
        chain = config.role_overrides[role]
        if chain:
            return chain[0], "role_override", chain
    
    # Fall back to default chain
    if config.default_chain:
        return config.default_chain[0], "primary", config.default_chain
    
    # Ultimate fallback
    fallback = "minimax/minimax-m2.1"
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
