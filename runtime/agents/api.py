"""
Agent API Layer - Core interfaces and deterministic ID computation.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1
"""

from __future__ import annotations

import hashlib
import logging
import time
import uuid
import warnings
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from runtime.errors import EnvelopeViolation
from runtime.receipts.invocation_receipt import record_invocation_receipt
from runtime.util.canonical import canonical_json

from .models import ModelConfig, load_model_config, resolve_model_auto

# Configure logger
logger = logging.getLogger(__name__)


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
    require_usage: bool = False


@dataclass
class AgentResponse:
    """Response from an LLM call. Per v0.3 spec §5.1."""

    call_id: str  # Deterministic ID
    call_id_audit: str  # UUID for audit (metadata only)
    role: str
    model_used: str
    model_version: str
    content: str
    packet: Optional[dict]
    usage: dict = field(default_factory=dict)
    latency_ms: int = 0
    timestamp: str = ""  # Metadata only


class AgentAPIError(Exception):
    """Base exception for Agent API errors."""

    pass


class AgentTimeoutError(AgentAPIError):
    """Call exceeded timeout."""

    pass


class AgentResponseInvalid(AgentAPIError):
    """Response failed packet schema validation."""

    pass


class DelegatedDispatchError(AgentAPIError):
    """
    Raised when a role configured as delegated dispatch is called directly.
    These roles must be routed via provider_overrides through the lens executor.
    """

    pass


def _normalize_usage(usage: Any) -> dict[str, int]:
    """Normalize provider usage payload into canonical token fields."""
    if not isinstance(usage, dict):
        return {}

    def _pick_int(*keys: str) -> int | None:
        for key in keys:
            value = usage.get(key)
            if isinstance(value, int) and value >= 0:
                return value
        return None

    input_tokens = _pick_int("input_tokens", "prompt_tokens", "promptTokenCount", "inputTokenCount")
    output_tokens = _pick_int(
        "output_tokens", "completion_tokens", "candidatesTokenCount", "outputTokenCount"
    )
    total_tokens = _pick_int("total_tokens", "totalTokenCount")

    normalized: dict[str, int] = {}
    if input_tokens is not None:
        normalized["input_tokens"] = input_tokens
    if output_tokens is not None:
        normalized["output_tokens"] = output_tokens
    if total_tokens is not None:
        normalized["total_tokens"] = total_tokens
    elif input_tokens is not None and output_tokens is not None:
        normalized["total_tokens"] = input_tokens + output_tokens

    return normalized


def _provider_id_from_model(model_version: str, model_used: str, fallback: str = "unknown") -> str:
    """Infer provider id from a model string like 'provider/model'."""
    for candidate in (model_version, model_used):
        if isinstance(candidate, str) and candidate.strip():
            token = candidate.strip().split("/", 1)[0]
            return token or fallback
    return fallback


def _receipt_token_usage(usage: dict[str, int]) -> Optional[dict[str, int]]:
    """Map normalized usage keys to invocation receipt schema keys."""
    if not usage:
        return None

    mapped: dict[str, int] = {}
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    total_tokens = usage.get("total_tokens")
    if isinstance(input_tokens, int) and input_tokens >= 0:
        mapped["prompt_tokens"] = input_tokens
    if isinstance(output_tokens, int) and output_tokens >= 0:
        mapped["completion_tokens"] = output_tokens
    if isinstance(total_tokens, int) and total_tokens >= 0:
        mapped["total_tokens"] = total_tokens
    elif "prompt_tokens" in mapped and "completion_tokens" in mapped:
        mapped["total_tokens"] = mapped["prompt_tokens"] + mapped["completion_tokens"]
    return mapped or None


def _record_agent_receipt(
    *,
    run_id: str,
    provider_id: str,
    mode: str,
    seat_id: str,
    start_ts: str,
    end_ts: str,
    exit_status: int,
    output_content: str,
    schema_validation: str,
    token_usage: Optional[dict[str, int]] = None,
    truncation: Optional[dict[str, bool]] = None,
    error: Optional[str] = None,
    input_hash: Optional[str] = None,
) -> None:
    """Best-effort invocation receipt recording. Never raises."""
    if not run_id:
        return
    try:
        record_invocation_receipt(
            run_id=run_id,
            provider_id=provider_id,
            mode=mode,
            seat_id=seat_id,
            start_ts=start_ts,
            end_ts=end_ts,
            exit_status=exit_status,
            output_content=output_content,
            schema_validation=schema_validation,
            token_usage=token_usage,
            truncation=truncation,
            error=error,
            input_hash=input_hash,
        )
    except Exception:
        logger.debug("Invocation receipt recording failed", exc_info=True)


def _write_replay_cache(call_id: str, content: str, model_version: str) -> None:
    """
    Phase 3C: Write successful LLM response to replay cache.

    Keyed by deterministic call_id so identical inputs (same call_id) hit
    the cache on retry or recovery, making re-runs idempotent.

    Best-effort: failure is logged, not raised.
    """
    try:
        from pathlib import Path

        from runtime.util.atomic_write import atomic_write_json

        # Derive cache dir relative to repo root (best-effort detect)
        try:
            import subprocess

            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            repo_root = Path(result.stdout.strip()) if result.returncode == 0 else Path.cwd()
        except Exception:
            repo_root = Path.cwd()

        # Sanitize call_id to safe filename (replace : with -)
        safe_id = call_id.replace(":", "-")
        cache_path = repo_root / "artifacts" / "replay_cache" / f"{safe_id}.json"
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        atomic_write_json(
            cache_path,
            {
                "call_id": call_id,
                "model_version": model_version,
                "response_content": content,
            },
        )
    except Exception:
        logger.debug("Replay cache write failed", exc_info=True)


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

    Robust parsing:
    1. Try parsing full content.
    2. Try extracting from ```yaml ... ``` or ```json ... ``` blocks.
    3. Returns None if parsing fails.
    """
    import re

    # 1. Try full content
    try:
        packet = yaml.safe_load(content)
        if isinstance(packet, dict):
            return packet
    except Exception:
        pass

    # 2. Try extracting from code blocks
    # regex for ```[language]\n[content]\n```
    pattern = r"```(?:yaml|json)?\s*\n(.*?)\n\s*```"
    match = re.search(pattern, content, re.DOTALL)
    if match:
        block_content = match.group(1)
        try:
            packet = yaml.safe_load(block_content)
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
    from .fixtures import get_cached_response, is_replay_mode
    from .logging import AgentCallLogger

    invocation_start_ts = datetime.now(timezone.utc).isoformat()
    resolved_model = call.model

    # Load config if not provided
    if config is None:
        config = load_model_config()

    # Delegated dispatch guard — delegated roles must go via lens executor
    from .models import get_agent_config as _get_agent_config

    if _get_agent_config(call.role, config).dispatch_mode == "delegated":
        raise DelegatedDispatchError(
            f"Role '{call.role}' is configured for delegated dispatch — "
            "routing must be provided via council.provider_overrides. "
            "Direct dispatch via call_agent() is not permitted for this role."
        )

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
    call_id_audit = str(uuid.uuid4())  # AUDIT-ONLY: non-deterministic trace ID for correlation logs

    # Check replay mode first
    if is_replay_mode():
        try:
            cached = get_cached_response(call_id)
            if call.require_usage:
                raise AgentAPIError(
                    "TOKEN_ACCOUNTING_UNAVAILABLE: replay fixtures do not include usage"
                )
            response = AgentResponse(
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
            _record_agent_receipt(
                run_id=run_id,
                provider_id="replay",
                mode="api",
                seat_id=call.role,
                start_ts=invocation_start_ts,
                end_ts=datetime.now(timezone.utc).isoformat(),
                exit_status=0,
                output_content=response.content,
                schema_validation="pass" if response.packet is not None else "n/a",
            )
            return response
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
    resolved_model = model

    # [HARDENING] Use OpenCodeClient for robust protocol and provider handling.
    # It handles both OpenRouter (OpenAI style) and Zen (Anthropic style) logic.
    from .opencode_client import LLMCall, OpenCodeClient

    # Build client with role for key selection
    client = OpenCodeClient(
        role=call.role,
        timeout=config.timeout_seconds,
        log_calls=True,  # Enable local logs for debugging
    )

    try:
        start_time = time.monotonic()

        # Prepare request
        # Note: OpenCodeClient expects the full prompt (system + user) internally
        # but LLMCall has a system_prompt field.
        prompt = yaml.safe_dump(call.packet, default_flow_style=False)
        llm_request = LLMCall(
            prompt=prompt, model=model, system_prompt=system_prompt, role=call.role
        )

        # Execute call via client (handles retry and fallback internally)
        response = client.call(llm_request)
        normalized_usage = _normalize_usage(getattr(response, "usage", {}))
        if call.require_usage and not normalized_usage:
            raise AgentAPIError("TOKEN_ACCOUNTING_UNAVAILABLE: upstream usage missing")

        latency_ms = int((time.monotonic() - start_time) * 1000)

        # Parse response
        content = response.content
        model_version = response.model_used

        # Parse response as packet if possible
        packet = _parse_response_packet(content)
        output_packet_hash = (
            f"sha256:{hashlib.sha256(canonical_json(packet)).hexdigest()}" if packet else ""
        )

        timestamp = datetime.now(timezone.utc).isoformat()

        # Log to hash chain if logger provided
        if logger_instance is None:
            from .logging import AgentCallLogger

            logger_instance = AgentCallLogger()

        logger_instance.log_call(
            call_id_deterministic=call_id,
            call_id_audit=response.call_id,
            role=call.role,
            model_requested=call.model,
            model_used=model,
            model_version=model_version,
            input_packet_hash=packet_hash,
            prompt_hash=prompt_hash,
            input_tokens=normalized_usage.get("input_tokens", 0),
            output_tokens=normalized_usage.get("output_tokens", 0),
            latency_ms=latency_ms,
            output_packet_hash=output_packet_hash,
            status="success",
        )

        agent_response = AgentResponse(
            call_id=call_id,
            call_id_audit=response.call_id,
            role=call.role,
            model_used=model,
            model_version=model_version,
            content=content,
            packet=packet,
            usage=normalized_usage,
            latency_ms=latency_ms,
            timestamp=timestamp,
        )
        _record_agent_receipt(
            run_id=run_id,
            provider_id=_provider_id_from_model(model_version, model, fallback="api"),
            mode="api",
            seat_id=call.role,
            start_ts=invocation_start_ts,
            end_ts=timestamp,
            exit_status=0,
            output_content=content,
            schema_validation="pass" if packet is not None else "n/a",
            token_usage=_receipt_token_usage(normalized_usage),
            input_hash=packet_hash,  # Phase 4A: capture input prompt hash
        )

        # Phase 3C: Write response to replay cache keyed by deterministic call_id.
        # Same inputs → same call_id → cache hit on retry/recovery.
        _write_replay_cache(call_id, content, model_version)

        return agent_response

    except Exception as e:
        _record_agent_receipt(
            run_id=run_id,
            provider_id=_provider_id_from_model("", resolved_model, fallback="api"),
            mode="api",
            seat_id=call.role,
            start_ts=invocation_start_ts,
            end_ts=datetime.now(timezone.utc).isoformat(),
            exit_status=1,
            output_content="",
            schema_validation="fail",
            error=str(e),
        )
        logger.error(f"Agent call failed: {e}")
        raise AgentAPIError(f"Agent call failed: {str(e)}")


def _try_cli_dispatch(
    prompt: str,
    cli_provider_name: str,
    config: "ModelConfig",
    run_id: str = "",
) -> Optional["CLIDispatchResult"]:
    """Try dispatching to a single CLI provider. Returns CLIDispatchResult or None."""
    from .cli_dispatch import (
        CLIDispatchConfig,
        CLIDispatchError,
        CLIProvider,
        CLIProviderNotFound,
        dispatch_cli_agent,
    )
    from .models import get_cli_provider_config

    cli_cfg = get_cli_provider_config(cli_provider_name, config)
    if not cli_cfg or not cli_cfg.enabled:
        logger.info("CLI provider %s not available or disabled", cli_provider_name)
        return None

    try:
        cli_provider = CLIProvider(cli_provider_name)
    except ValueError:
        logger.warning("Unknown CLI provider enum value: %s", cli_provider_name)
        return None

    dispatch_config = CLIDispatchConfig(
        provider=cli_provider,
        timeout_seconds=cli_cfg.timeout_seconds,
        sandbox=cli_cfg.sandbox,
        model="",  # CLI tools use their own default SOTA
    )

    try:
        result = dispatch_cli_agent(
            prompt, dispatch_config, binary_override=cli_cfg.binary, run_id=run_id
        )
        if result.success or result.partial:
            return result
        logger.warning(
            "CLI provider %s returned exit=%d; trying next", cli_provider_name, result.exit_code
        )
        return None
    except CLIProviderNotFound:
        logger.warning("CLI binary for %s not found on PATH", cli_provider_name)
        return None
    except CLIDispatchError as exc:
        logger.warning("CLI dispatch error for %s: %s", cli_provider_name, exc)
        return None


def call_agent_cli(
    call: AgentCall,
    run_id: str = "",
    logger_instance: Optional["AgentCallLogger"] = None,
    config: Optional[ModelConfig] = None,
) -> AgentResponse:
    """
    Invoke an LLM via CLI agent dispatch (Codex, Gemini, Claude Code).

    Same contract as call_agent() but routes through subprocess-based
    CLI agents that have full tool use, file access, and sandbox capabilities.

    Falls back to call_agent() if the role is not configured for CLI dispatch,
    the primary CLI provider is not available, or all CLI providers fail.

    Args:
        call: AgentCall specification
        run_id: Deterministic run ID for logging
        logger_instance: Optional AgentCallLogger for hash chain logging
        config: Optional ModelConfig (loads from file if None)

    Returns:
        AgentResponse with parsed content and metadata
    """
    from .logging import AgentCallLogger
    from .models import get_agent_config, is_cli_dispatch

    invocation_start_ts = datetime.now(timezone.utc).isoformat()

    if config is None:
        config = load_model_config()

    # Delegated dispatch guard — delegated roles must go via lens executor
    if get_agent_config(call.role, config).dispatch_mode == "delegated":
        raise DelegatedDispatchError(
            f"Role '{call.role}' is configured for delegated dispatch — "
            "routing must be provided via council.provider_overrides. "
            "Direct dispatch via call_agent_cli() is not permitted for this role."
        )

    if not is_cli_dispatch(call.role, config):
        logger.info("Role %s not configured for CLI; falling back to API", call.role)
        return call_agent(call, run_id, logger_instance, config)

    # CLI providers do not currently expose token usage in a canonical schema.
    # Preserve call_agent() semantics by using the API path when usage is required.
    if call.require_usage:
        logger.info(
            "Role %s requested require_usage; falling back to API for token accounting",
            call.role,
        )
        return call_agent(call, run_id, logger_instance, config)

    agent_cfg = get_agent_config(call.role, config)
    cli_provider_name = agent_cfg.cli_provider

    # Compute deterministic IDs
    system_prompt, prompt_hash = _load_role_prompt(call.role)
    packet_hash = f"sha256:{hashlib.sha256(canonical_json(call.packet)).hexdigest()}"
    call_id = compute_call_id_deterministic(
        run_id_deterministic=run_id or "no_run",
        role=call.role,
        prompt_hash=prompt_hash,
        packet_hash=packet_hash,
    )
    call_id_audit = str(uuid.uuid4())
    prompt = f"{system_prompt}\n\n---\n\n{yaml.safe_dump(call.packet, default_flow_style=False)}"

    # Try primary CLI provider
    result = _try_cli_dispatch(prompt, cli_provider_name, config, run_id=run_id)
    used_provider = cli_provider_name

    # Try secondary CLI fallback if primary failed
    if result is None and agent_cfg.cli_fallback:
        logger.info(
            "Primary CLI %s failed; trying fallback %s", cli_provider_name, agent_cfg.cli_fallback
        )
        result = _try_cli_dispatch(prompt, agent_cfg.cli_fallback, config, run_id=run_id)
        used_provider = agent_cfg.cli_fallback

    # All CLI providers failed → fall back to API
    if result is None:
        logger.warning("All CLI providers failed for %s; falling back to API", call.role)
        return call_agent(call, run_id, logger_instance, config)

    if result.partial:
        logger.warning("CLI agent %s returned partial output (timeout)", used_provider)

    content = result.output
    packet = _parse_response_packet(content)
    output_packet_hash = (
        f"sha256:{hashlib.sha256(canonical_json(packet)).hexdigest()}" if packet else ""
    )
    timestamp = datetime.now(timezone.utc).isoformat()

    # Provenance: CLI tools use their own default SOTA
    model_used = f"{used_provider}/default"
    model_version = f"{used_provider}/default"

    if logger_instance is None:
        logger_instance = AgentCallLogger()

    logger_instance.log_call(
        call_id_deterministic=call_id,
        call_id_audit=call_id_audit,
        role=call.role,
        model_requested=call.model,
        model_used=model_used,
        model_version=model_version,
        input_packet_hash=packet_hash,
        prompt_hash=prompt_hash,
        input_tokens=0,
        output_tokens=0,
        latency_ms=result.latency_ms,
        output_packet_hash=output_packet_hash,
        status="success" if result.success else "partial",
    )

    agent_response = AgentResponse(
        call_id=call_id,
        call_id_audit=call_id_audit,
        role=call.role,
        model_used=model_used,
        model_version=model_version,
        content=content,
        packet=packet,
        usage={},
        latency_ms=result.latency_ms,
        timestamp=timestamp,
    )
    _record_agent_receipt(
        run_id=run_id,
        provider_id=used_provider,
        mode="cli",
        seat_id=call.role,
        start_ts=invocation_start_ts,
        end_ts=timestamp,
        exit_status=result.exit_code,
        output_content=content,
        schema_validation="pass" if packet is not None else "n/a",
        truncation={"input_truncated": False, "output_truncated": bool(result.partial)},
    )
    return agent_response
