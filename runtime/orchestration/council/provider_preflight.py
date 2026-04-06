"""
Provider preflight health checks for the council runner.

Checks each configured provider before any seat prompt is sent.
Classifies availability so the runner can block early on
provider_unavailable rather than burning seat budget.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Mapping

from runtime.orchestration.council.models import ProviderHealthResult, SeatFailureClass

# Default timeouts (seconds)
DEFAULT_PREFLIGHT_TIMEOUT = 30
_ECHO_PROMPT = "Reply with the single word: ready"

# Callable type for the echo-prompt function (injectable for tests)
EchoProbe = Callable[[str, float], tuple[bool, str | None]]


def _auth_check(provider: str) -> bool:
    """Return True if auth credentials are present for this provider."""
    # All current council providers route through ZEN_REVIEWER_KEY (OpenRouter gateway)
    return bool(os.environ.get("ZEN_REVIEWER_KEY"))


def _make_api_echo_probe() -> EchoProbe:
    """Return an echo probe that calls the provider API via call_agent."""

    def probe(model: str, timeout: float) -> tuple[bool, str | None]:
        try:
            from runtime.agents.api import AgentCall, call_agent
            from runtime.agents.models import AgentConfig

            agent_cfg = AgentConfig(
                model=model,
                role="council_reviewer",
                max_tokens=16,
                temperature=0.0,
                fallback=[],
            )
            call = AgentCall(
                agent_config=agent_cfg,
                messages=[{"role": "user", "content": _ECHO_PROMPT}],
                system=None,
                metadata={},
            )
            resp = call_agent(call, timeout=timeout)
            return bool(resp and resp.content), None
        except Exception as exc:
            return False, str(exc)

    return probe


def check_provider(
    provider: str,
    model: str,
    *,
    timeout: float = DEFAULT_PREFLIGHT_TIMEOUT,
    echo_probe: EchoProbe | None = None,
    skip_echo: bool = False,
) -> ProviderHealthResult:
    """
    Run a full health check for one provider/model combination.

    Auth is checked first; network/echo probe is skipped if auth is absent.
    Echo probe is retried once on failure before classifying unavailable.

    Args:
        provider: Human-readable provider name (e.g. "openrouter/kimi-k2.5").
        model: Full model ID to probe.
        timeout: Seconds allowed for the echo prompt (each attempt).
        echo_probe: Injectable callable for testing; defaults to live API probe.

    Returns:
        ProviderHealthResult with status classified as one of SeatFailureClass.
    """
    if echo_probe is None:
        echo_probe = _make_api_echo_probe()

    auth_ok = _auth_check(provider)
    if not auth_ok:
        return ProviderHealthResult(
            provider=provider,
            auth_ok=False,
            echo_ok=False,
            status=SeatFailureClass.provider_unavailable,
            error="auth credentials absent",
        )

    if skip_echo:
        # Dry-run / auth-only mode: skip network echo probe
        return ProviderHealthResult(
            provider=provider,
            auth_ok=True,
            echo_ok=True,
            status=SeatFailureClass.seat_completed,
        )

    # Attempt echo probe (up to 2 tries)
    for attempt in range(2):
        t0 = time.monotonic()
        ok, err = echo_probe(model, timeout)
        latency = time.monotonic() - t0

        if ok:
            return ProviderHealthResult(
                provider=provider,
                auth_ok=True,
                echo_ok=True,
                status=SeatFailureClass.seat_completed,
                latency_seconds=latency,
            )

        # Classify the error on the last attempt
        if attempt == 1:
            status = _classify_error(err or "", latency, timeout)
            return ProviderHealthResult(
                provider=provider,
                auth_ok=True,
                echo_ok=False,
                status=status,
                latency_seconds=latency,
                error=err,
            )

    # Unreachable but satisfies type checker
    return ProviderHealthResult(  # pragma: no cover
        provider=provider,
        auth_ok=True,
        echo_ok=False,
        status=SeatFailureClass.provider_unavailable,
    )


def _classify_error(error: str, latency: float, timeout: float) -> SeatFailureClass:
    """Map an error string + latency to a SeatFailureClass."""
    lower = error.lower()
    if latency >= timeout * 0.95:
        return SeatFailureClass.seat_timeout
    if any(k in lower for k in ("quota", "rate_limit", "rate limit", "429", "too many")):
        return SeatFailureClass.provider_quota
    return SeatFailureClass.provider_unavailable


def run_preflight(
    provider_models: Mapping[str, str],
    *,
    timeout: float = DEFAULT_PREFLIGHT_TIMEOUT,
    echo_probe: EchoProbe | None = None,
    skip_echo: bool = False,
) -> dict[str, ProviderHealthResult]:
    """
    Run preflight checks for all providers.

    Args:
        provider_models: Mapping of provider_name → model_id.
        timeout: Per-provider echo-probe timeout in seconds.
        echo_probe: Injectable probe for testing.

    Returns:
        Dict mapping provider_name → ProviderHealthResult.
    """
    results: dict[str, ProviderHealthResult] = {}
    for provider, model in provider_models.items():
        results[provider] = check_provider(
            provider, model, timeout=timeout, echo_probe=echo_probe, skip_echo=skip_echo
        )
    return results


def is_run_blocked(
    health_results: Mapping[str, ProviderHealthResult],
    required_providers: set[str],
    carry_forward_allowed: bool = False,
    carry_forward_providers: set[str] | None = None,
) -> tuple[bool, str]:
    """
    Determine if a council run should be blocked based on preflight results.

    A run is blocked if any required provider is not seat_completed AND
    carry-forward is either not allowed or not declared for that provider.

    Args:
        health_results: Results from run_preflight().
        required_providers: Set of provider names that must be available.
        carry_forward_allowed: Whether the CCP allows prior-seat carry-forward.
        carry_forward_providers: Providers explicitly declared for carry-forward.

    Returns:
        (blocked: bool, reason: str)
    """
    cf_set = carry_forward_providers or set()
    unavailable = []
    for provider in sorted(required_providers):
        result = health_results.get(provider)
        if result is None or result.status != SeatFailureClass.seat_completed:
            if carry_forward_allowed and provider in cf_set:
                continue
            unavailable.append(provider)

    if unavailable:
        return True, f"blocked_provider: unavailable={unavailable}"
    return False, ""


def provider_health_to_dict(
    results: Mapping[str, ProviderHealthResult],
) -> dict[str, Any]:
    """Serialize health results to a JSON-safe dict for provider_health.json."""
    return {name: result.to_dict() for name, result in sorted(results.items())}
