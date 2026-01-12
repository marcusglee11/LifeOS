"""
Agent Logging Compatibility Shim.

DEPRECATED: This file is a compatibility shim. The canonical implementation
is in runtime/agents/logging.py per spec §5.1.4.

Import from runtime.agents.logging for new code.
"""

# Re-export everything from canonical logging module
from .logging import (
    HASH_CHAIN_GENESIS,
    AgentCallLogEntry,
    AgentCallLogger,
)

__all__ = [
    "HASH_CHAIN_GENESIS",
    "AgentCallLogEntry",
    "AgentCallLogger",
]
