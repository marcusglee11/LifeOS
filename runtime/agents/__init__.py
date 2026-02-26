"""
LifeOS Agent API Layer.

This package provides the agent call infrastructure for the Build Loop.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1
"""

# Core API
from .api import (
    canonical_json,
    compute_run_id_deterministic,
    compute_call_id_deterministic,
    AgentCall,
    AgentResponse,
    AgentAPIError,
    EnvelopeViolation,
    AgentTimeoutError,
    AgentResponseInvalid,
    call_agent,
    call_agent_cli,
)

# Logging (hash chain)
from .logging import (
    HASH_CHAIN_GENESIS,
    AgentCallLogEntry,
    AgentCallLogger,
)

# Fixtures (replay mode)
from .fixtures import (
    ReplayMissError,
    CachedResponse,
    ReplayFixtureCache,
    is_replay_mode,
    get_cached_response,
)

# Model resolution
from .models import (
    ModelConfig,
    CLIProviderConfig,
    load_model_config,
    resolve_model_auto,
    get_model_chain,
    get_cli_provider_config,
    is_cli_dispatch,
)

# Health monitoring
from .health import (
    ProviderStatus,
    HealthReport,
    LatencyTracker,
    check_all_providers,
)

# CLI dispatch
from .cli_dispatch import (
    CLIProvider,
    CLIDispatchConfig,
    CLIDispatchResult,
    CLIDispatchError,
    CLIProviderNotFound,
    CLIDispatchTimeout,
    dispatch_cli_agent,
)

# OpenCode client
from .opencode_client import (
    OpenCodeClient,
    LLMCall,
    LLMResponse,
    OpenCodeError,
    OpenCodeServerError,
    OpenCodeTimeoutError,
)

__all__ = [
    # api.py
    "canonical_json",
    "compute_run_id_deterministic",
    "compute_call_id_deterministic",
    "AgentCall",
    "AgentResponse",
    "AgentAPIError",
    "EnvelopeViolation",
    "AgentTimeoutError",
    "AgentResponseInvalid",
    "call_agent",
    "call_agent_cli",
    # logging.py
    "HASH_CHAIN_GENESIS",
    "AgentCallLogEntry",
    "AgentCallLogger",
    # fixtures.py
    "ReplayMissError",
    "CachedResponse",
    "ReplayFixtureCache",
    "is_replay_mode",
    "get_cached_response",
    # models.py
    "ModelConfig",
    "CLIProviderConfig",
    "load_model_config",
    "resolve_model_auto",
    "get_model_chain",
    "get_cli_provider_config",
    "is_cli_dispatch",
    # health.py
    "ProviderStatus",
    "HealthReport",
    "LatencyTracker",
    "check_all_providers",
    # cli_dispatch.py
    "CLIProvider",
    "CLIDispatchConfig",
    "CLIDispatchResult",
    "CLIDispatchError",
    "CLIProviderNotFound",
    "CLIDispatchTimeout",
    "dispatch_cli_agent",
    # opencode_client.py
    "OpenCodeClient",
    "LLMCall",
    "LLMResponse",
    "OpenCodeError",
    "OpenCodeServerError",
    "OpenCodeTimeoutError",
]
