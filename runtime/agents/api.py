"""
Agent API Layer - Core interfaces and deterministic ID computation.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import uuid
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx
import yaml

from .models import load_model_config, resolve_model_auto, ModelConfig

# Configure logger
logger = logging.getLogger(__name__)


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


def _load_role_prompt(role: str, config_dir: str = "config/agent_roles") -> tuple[str, str]:
    """
    Load system prompt for a role.
    
    Args:
        role: Agent role name
        config_dir: Directory containing role prompt files
        
    Returns:
        Tuple of (prompt_content, prompt_hash)
        
    Raises:
        EnvelopeViolation: If role prompt file doesn't exist
    """
    prompt_path = Path(config_dir) / f"{role}.md"
    
    if not prompt_path.exists():
        raise EnvelopeViolation(f"Role prompt not found: {prompt_path}")
    
    content = prompt_path.read_text(encoding="utf-8")
    prompt_hash = f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}"
    
    # Log warning if governance baseline is missing (per plan: don't fail)
    baseline_path = Path("config/governance_baseline.yaml")
    if not baseline_path.exists():
        warnings.warn(
            f"Governance baseline missing at {baseline_path}. "
            "Role prompt hash verification skipped.",
            UserWarning,
        )
    
    return content, prompt_hash


def _parse_response_packet(content: str) -> Optional[dict]:
    """
    Attempt to parse response content as YAML packet.
    
    Returns None if parsing fails (not all responses are structured).
    """
    try:
        # Try to parse as YAML
        packet = yaml.safe_load(content)
        if isinstance(packet, dict):
            return packet
    except Exception:
        pass
    return None


def call_agent(
    call: AgentCall,
    run_id: str = "",
    logger_instance: Optional["AgentCallLogger"] = None,
    config: Optional[ModelConfig] = None,
) -> AgentResponse:
    """
    Invoke an LLM via OpenRouter with role-specific system prompt.
    
    Per v0.3 spec §5.1:
    1. Check replay mode — return cached response if available
    2. Load role prompt in and compute hashes
    3. Resolve model if "auto"
    4. Call OpenRouter API with retry/backoff
    5. Parse response
    6. Log to hash chain
    7. Return AgentResponse
    
    Args:
        call: AgentCall specification
        run_id: Deterministic run ID for logging (empty string if not in a run)
        logger_instance: Optional AgentCallLogger for hash chain logging
        config: Optional ModelConfig (loads from file if None)
        
    Returns:
        AgentResponse with parsed content and metadata
        
    Raises:
        AgentTimeoutError: If call exceeds timeout after retries
        EnvelopeViolation: If role not permitted or prompt missing
        AgentResponseInvalid: If response fails validation
    """
    from .fixtures import is_replay_mode, get_cached_response, CachedResponse
    from .logging import AgentCallLogger
    
    # Load config if not provided
    if config is None:
        config = load_model_config()
    
    # Load role prompt and compute hashes
    system_prompt, prompt_hash = _load_role_prompt(call.role)
    packet_hash = f"sha256:{hashlib.sha256(canonical_json(call.packet)).hexdigest()}"
    
    # Compute deterministic call ID
    call_id = compute_call_id_deterministic(
        run_id_deterministic=run_id or "no_run",
        role=call.role,
        prompt_hash=prompt_hash,
        packet_hash=packet_hash,
    )
    call_id_audit = str(uuid.uuid4())
    
    # Check replay mode first
    if is_replay_mode():
        try:
            cached = get_cached_response(call_id)
            return AgentResponse(
                call_id=call_id,
                call_id_audit=call_id_audit,
                role=call.role,
                model_used=cached.model_version,
                model_version=cached.model_version,
                content=cached.response_content,
                packet=cached.response_packet,
                usage={},
                latency_ms=0,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        except Exception:
            # ReplayMissError will propagate
            raise
    
    # Resolve model
    if call.model == "auto":
        model, selection_reason, model_chain = resolve_model_auto(call.role, config)
    else:
        model = call.model
        selection_reason = "explicit"
        model_chain = [model]
    
    # Get API key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise AgentAPIError("OPENROUTER_API_KEY environment variable not set")
    
    # Build request
    user_message = yaml.safe_dump(call.packet, default_flow_style=False)
    
    request_body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": call.temperature,
        "max_tokens": call.max_tokens,
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://lifeos.local",
        "X-Title": "LifeOS Agent API",
    }
    
    # Execute with retry
    start_time = time.monotonic()
    last_error: Optional[Exception] = None
    response_data: Optional[dict] = None
    
    for attempt in range(config.max_retry_attempts):
        try:
            with httpx.Client(timeout=config.timeout_seconds) as client:
                response = client.post(
                    f"{config.base_url}/chat/completions",
                    headers=headers,
                    json=request_body,
                )
                response.raise_for_status()
                response_data = response.json()
                break
                
        except httpx.TimeoutException as e:
            last_error = AgentTimeoutError(f"Request timed out after {config.timeout_seconds}s")
            logger.warning(f"Attempt {attempt + 1} timed out: {e}")
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:  # Rate limited
                wait_time = config.backoff_base_seconds * (config.backoff_multiplier ** attempt)
                logger.warning(f"Rate limited, waiting {wait_time}s before retry")
                time.sleep(wait_time)
                last_error = e
            else:
                raise AgentAPIError(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
                
        except httpx.RequestError as e:
            wait_time = config.backoff_base_seconds * (config.backoff_multiplier ** attempt)
            logger.warning(f"Request error on attempt {attempt + 1}, waiting {wait_time}s: {e}")
            time.sleep(wait_time)
            last_error = e
    
    if response_data is None:
        if isinstance(last_error, AgentTimeoutError):
            raise last_error
        raise AgentAPIError(f"All {config.max_retry_attempts} attempts failed: {last_error}")
    
    latency_ms = int((time.monotonic() - start_time) * 1000)
    
    # Parse response
    choices = response_data.get("choices", [])
    if not choices:
        raise AgentResponseInvalid("OpenRouter returned no choices")
    
    content = choices[0].get("message", {}).get("content", "")
    model_version = response_data.get("model", model)
    
    usage = response_data.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    
    # Parse response as packet if possible
    packet = _parse_response_packet(content)
    output_packet_hash = (
        f"sha256:{hashlib.sha256(canonical_json(packet)).hexdigest()}"
        if packet else ""
    )
    
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Log to hash chain if logger provided
    if logger_instance is None:
        logger_instance = AgentCallLogger()
    
    logger_instance.log_call(
        call_id_deterministic=call_id,
        call_id_audit=call_id_audit,
        role=call.role,
        model_requested=call.model,
        model_used=model,
        model_version=model_version,
        input_packet_hash=packet_hash,
        prompt_hash=prompt_hash,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        latency_ms=latency_ms,
        output_packet_hash=output_packet_hash,
        status="success",
    )
    
    return AgentResponse(
        call_id=call_id,
        call_id_audit=call_id_audit,
        role=call.role,
        model_used=model,
        model_version=model_version,
        content=content,
        packet=packet,
        usage={"input_tokens": input_tokens, "output_tokens": output_tokens},
        latency_ms=latency_ms,
        timestamp=timestamp,
    )
