"""
LifeOS Agent API Layer.

This package provides the agent call infrastructure for the Build Loop.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1
"""

# Core API
from .api import (
    AgentAPIError,
    AgentCall,
    AgentResponse,
    AgentResponseInvalid,
    AgentTimeoutError,
    DelegatedDispatchError,
    EnvelopeViolation,
    call_agent,
    call_agent_cli,
    canonical_json,
    compute_call_id_deterministic,
    compute_run_id_deterministic,
)

# CLI dispatch
from .cli_dispatch import (
    CLIDispatchConfig,
    CLIDispatchError,
    CLIDispatchResult,
    CLIDispatchTimeout,
    CLIProvider,
    CLIProviderNotFound,
    dispatch_cli_agent,
)

# Fixtures (replay mode)
from .fixtures import (
    CachedResponse,
    ReplayFixtureCache,
    ReplayMissError,
    get_cached_response,
    is_replay_mode,
)

# Health monitoring
from .health import (
    HealthReport,
    LatencyTracker,
    ProviderStatus,
    check_all_providers,
)

# Logging (hash chain)
from .logging import (
    HASH_CHAIN_GENESIS,
    AgentCallLogEntry,
    AgentCallLogger,
)

# Model resolution
from .models import (
    CLIProviderConfig,
    ModelConfig,
    get_cli_provider_config,
    get_model_chain,
    is_cli_dispatch,
    load_model_config,
    resolve_model_auto,
)

# OpenCode client
from .opencode_client import (
    LLMCall,
    LLMResponse,
    OpenCodeClient,
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
    "DelegatedDispatchError",
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
