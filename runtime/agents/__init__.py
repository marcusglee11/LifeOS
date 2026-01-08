"""
LifeOS Agent API Layer — Phase 1a Scaffold.

This package provides the agent call infrastructure for the Build Loop.
Phase 1a exports only scaffold surfaces; OpenCode client integration
is deferred to Phase 2+.
"""

# Phase 1a exports: deterministic IDs, canonical JSON, logging
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
)

from .logging import (
    HASH_CHAIN_GENESIS,
    AgentCallLogEntry,
    AgentCallLogger,
)

from .fixtures import (
    ReplayMissError,
    CachedResponse,
    ReplayFixtureCache,
    is_replay_mode,
    get_cached_response,
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
]
