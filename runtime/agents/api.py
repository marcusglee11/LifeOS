"""
Agent API Layer - Core interfaces and deterministic ID computation.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Optional


def canonical_json(obj: Any) -> bytes:
    """
    Produce canonical JSON for deterministic hashing.
    
    Per v0.3 spec §5.1.4:
    1. Encoding: UTF-8, no BOM
    2. Whitespace: None
    3. Key ordering: Lexicographically sorted
    4. Array ordering: Preserved
    
    [v0.3 Fail-Closed]: Rejects NaN/Infinity values.
    """
    return json.dumps(
        obj,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,  # Fail-closed: reject NaN/Infinity
    ).encode("utf-8")


def compute_run_id_deterministic(
    mission_spec: dict,
    inputs_hash: str,
    governance_surface_hashes: dict,
    code_version_id: str,
) -> str:
    """
    Compute deterministic run identifier.
    
    Per v0.3 spec §5.1.3:
    run_id_deterministic = sha256(
        canonical_json(mission_spec) +
        inputs_hash +
        canonical_json(sorted(governance_surface_hashes.items())) +
        code_version_id
    )
    """
    hasher = hashlib.sha256()
    hasher.update(canonical_json(mission_spec))
    hasher.update(inputs_hash.encode("utf-8"))
    hasher.update(canonical_json(sorted(governance_surface_hashes.items())))
    hasher.update(code_version_id.encode("utf-8"))
    return f"sha256:{hasher.hexdigest()}"


def compute_call_id_deterministic(
    run_id_deterministic: str,
    role: str,
    prompt_hash: str,
    packet_hash: str,
) -> str:
    """
    Compute deterministic call identifier.
    
    Per v0.3 spec §5.1.3:
    call_id_deterministic = sha256(
        run_id_deterministic +
        role +
        prompt_hash +
        packet_hash
    )
    """
    hasher = hashlib.sha256()
    hasher.update(run_id_deterministic.encode("utf-8"))
    hasher.update(role.encode("utf-8"))
    hasher.update(prompt_hash.encode("utf-8"))
    hasher.update(packet_hash.encode("utf-8"))
    return f"sha256:{hasher.hexdigest()}"


@dataclass
class AgentCall:
    """Request to invoke an LLM. Per v0.3 spec §5.1."""
    
    role: str
    packet: dict
    model: str = "auto"
    temperature: float = 0.0
    max_tokens: int = 8192


@dataclass
class AgentResponse:
    """Response from an LLM call. Per v0.3 spec §5.1."""
    
    call_id: str                 # Deterministic ID
    call_id_audit: str           # UUID for audit (metadata only)
    role: str
    model_used: str
    model_version: str
    content: str
    packet: Optional[dict]
    usage: dict = field(default_factory=dict)
    latency_ms: int = 0
    timestamp: str = ""          # Metadata only


class AgentAPIError(Exception):
    """Base exception for Agent API errors."""
    pass


class EnvelopeViolation(AgentAPIError):
    """Role or operation not permitted."""
    pass


class AgentTimeoutError(AgentAPIError):
    """Call exceeded timeout."""
    pass


class AgentResponseInvalid(AgentAPIError):
    """Response failed packet schema validation."""
    pass


def call_agent(call: AgentCall) -> AgentResponse:
    """
    Invoke an LLM via OpenRouter with role-specific system prompt.
    
    STUB: This is a Phase 1a scaffold. Real implementation requires
    OpenRouter integration and model resolution logic.
    
    Raises:
        NotImplementedError: Full implementation pending Phase 2+
    """
    raise NotImplementedError(
        "call_agent requires OpenRouter integration (Phase 2+). "
        "For testing, use fixtures with LIFEOS_TEST_MODE=replay."
    )
