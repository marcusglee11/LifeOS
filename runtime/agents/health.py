"""
Provider Health Monitoring - Pre-mission smoke tests and latency tracking.

Provides:
  - Per-provider health checks (API ping or CLI binary availability)
  - Latency tracking with simple moving average
  - Auto-fallback recommendations when providers are unresponsive
"""

from __future__ import annotations

import collections
import logging
import shutil
import time
from dataclasses import dataclass, field
from typing import Optional

from .models import (
    CLIProviderConfig,
    ModelConfig,
    load_model_config,
)

logger = logging.getLogger(__name__)

# Default moving average window size
_DEFAULT_WINDOW = 10


@dataclass
class ProviderStatus:
    """Health status for a single provider."""

    name: str
    available: bool
    latency_ms: float = 0.0
    error: str = ""
    checked_at: float = 0.0  # monotonic timestamp


@dataclass
class HealthReport:
    """Aggregate health report for all configured providers."""

    providers: list[ProviderStatus]
    all_healthy: bool
    recommended_fallbacks: list[str] = field(default_factory=list)

    @property
    def available_providers(self) -> list[str]:
        return [p.name for p in self.providers if p.available]

    @property
    def unavailable_providers(self) -> list[str]:
        return [p.name for p in self.providers if not p.available]


class LatencyTracker:
    """Track per-provider latency with a simple moving average."""

    def __init__(self, window: int = _DEFAULT_WINDOW):
        self._window = window
        self._samples: dict[str, collections.deque[float]] = {}

    def record(self, provider: str, latency_ms: float) -> None:
        if provider not in self._samples:
            self._samples[provider] = collections.deque(maxlen=self._window)
        self._samples[provider].append(latency_ms)

    def average(self, provider: str) -> Optional[float]:
        samples = self._samples.get(provider)
        if not samples:
            return None
        return sum(samples) / len(samples)

    def all_averages(self) -> dict[str, float]:
        return {p: self.average(p) for p in self._samples if self.average(p) is not None}

    def fastest(self) -> Optional[str]:
        avgs = self.all_averages()
        if not avgs:
            return None
        return min(avgs, key=avgs.get)


def check_cli_provider(name: str, cli_config: CLIProviderConfig) -> ProviderStatus:
    """Check if a CLI provider binary is available on PATH."""
    start = time.monotonic()
    binary_path = shutil.which(cli_config.binary)
    elapsed = (time.monotonic() - start) * 1000

    if binary_path is None:
        return ProviderStatus(
            name=name,
            available=False,
            latency_ms=elapsed,
            error=f"Binary '{cli_config.binary}' not found on PATH",
            checked_at=start,
        )

    return ProviderStatus(
        name=name,
        available=True,
        latency_ms=elapsed,
        checked_at=start,
    )


def check_api_provider(name: str, endpoint: str, timeout: float = 5.0) -> ProviderStatus:
    """
    Check if an API provider endpoint is reachable.

    Performs a lightweight HEAD/GET to the base URL (not a full LLM call).
    """
    start = time.monotonic()
    try:
        import httpx

        # Use a short timeout for health checks
        with httpx.Client(timeout=timeout) as client:
            client.head(endpoint)
            elapsed = (time.monotonic() - start) * 1000
            # Any response (even 4xx) means the endpoint is reachable
            return ProviderStatus(
                name=name,
                available=True,
                latency_ms=elapsed,
                checked_at=start,
            )
    except Exception as exc:
        elapsed = (time.monotonic() - start) * 1000
        return ProviderStatus(
            name=name,
            available=False,
            latency_ms=elapsed,
            error=str(exc),
            checked_at=start,
        )


def check_all_providers(
    config: Optional[ModelConfig] = None,
    api_timeout: float = 5.0,
) -> HealthReport:
    """
    Run health checks on all configured providers.

    Checks:
      - API providers (zen, openrouter) via endpoint reachability
      - CLI providers (codex, gemini, claude_code) via binary availability

    Args:
        config: ModelConfig (loaded from file if None).
        api_timeout: Timeout in seconds for API health checks.

    Returns:
        HealthReport with per-provider status and fallback recommendations.
    """
    if config is None:
        config = load_model_config()

    statuses: list[ProviderStatus] = []

    # Check API providers
    if config.base_url:
        statuses.append(check_api_provider("zen", config.base_url, api_timeout))

    # Check CLI providers
    for name, cli_cfg in config.cli_providers.items():
        if cli_cfg.enabled:
            statuses.append(check_cli_provider(name, cli_cfg))

    all_healthy = all(s.available for s in statuses)

    # Build fallback recommendations: available providers sorted by latency
    available = sorted(
        [s for s in statuses if s.available],
        key=lambda s: s.latency_ms,
    )
    recommended = [s.name for s in available]

    report = HealthReport(
        providers=statuses,
        all_healthy=all_healthy,
        recommended_fallbacks=recommended,
    )

    if not all_healthy:
        unavailable = report.unavailable_providers
        logger.warning("Unhealthy providers: %s", unavailable)

    return report
