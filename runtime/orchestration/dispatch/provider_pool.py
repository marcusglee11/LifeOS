"""
ProviderPool — health-aware provider routing.

Phase 1: Stub with deterministic tie-break logic. No live health monitoring.
Phase 2: Full health monitoring with latency tracking, failure rates, cost tiers.

Deterministic tie-break for "auto" resolution:
  1. available (True first)
  2. failure_rate ASC
  3. latency_ms ASC
  4. cost_tier ASC (free < low < medium < high)
  5. name ASC (lexicographic — guarantees determinism on ties)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.util.atomic_write import atomic_write_json

HEALTH_STATE_RELATIVE_PATH = Path("artifacts/health/provider_state.json")

COST_TIER_ORDER = {"free": 0, "low": 1, "medium": 2, "high": 3}


@dataclass
class ProviderHealth:
    name: str
    available: bool = True
    latency_ms: float = 0.0
    failure_rate: float = 0.0
    cost_tier: str = "free"
    last_checked: Optional[str] = None


class ProviderPool:
    """
    Health-aware provider routing pool.

    Phase 1: Configured providers with deterministic tie-break.
    Phase 2: Live health monitoring via record_call() + smoke_test().
    """

    def __init__(self, repo_root: Path, providers: Optional[Dict[str, Any]] = None):
        self.repo_root = Path(repo_root).resolve()
        self._health: Dict[str, ProviderHealth] = {}

        for name, conf in (providers or {}).items():
            conf = conf or {}
            self._health[name] = ProviderHealth(
                name=name,
                available=bool(conf.get("available", True)),
                cost_tier=str(conf.get("cost_tier", "free")),
            )

    def resolve_provider(self, preference: str, role: str = "") -> str:
        """
        Resolve provider preference to a concrete provider name.

        Returns preference unchanged if it's not "auto".
        For "auto", uses deterministic tie-break over available providers.
        """
        if preference != "auto":
            return preference

        if not self._health:
            return "auto"

        candidates = sorted(
            self._health.values(),
            key=lambda p: (
                not p.available,
                p.failure_rate,
                p.latency_ms,
                COST_TIER_ORDER.get(p.cost_tier, 99),
                p.name,
            ),
        )

        available = [c for c in candidates if c.available]
        if available:
            return available[0].name
        return candidates[0].name

    def snapshot(self) -> Dict[str, Any]:
        """Return serializable, frozen snapshot of current health state for audit."""
        return {
            name: {
                "available": h.available,
                "latency_ms": h.latency_ms,
                "failure_rate": h.failure_rate,
                "cost_tier": h.cost_tier,
                "last_checked": h.last_checked,
            }
            for name, h in self._health.items()
        }

    def record_call(self, provider: str, latency_ms: int, success: bool) -> None:
        """Update health state after a call. Phase 1: records latency only."""
        if provider not in self._health:
            return
        h = self._health[provider]
        h.latency_ms = float(latency_ms)
        h.last_checked = datetime.now(timezone.utc).isoformat()

    def smoke_test(self) -> Dict[str, ProviderHealth]:
        """Pre-cycle health check. Phase 1: returns current configured state."""
        return dict(self._health)

    def persist(self) -> None:
        """Write state to artifacts/health/provider_state.json."""
        state_path = self.repo_root / HEALTH_STATE_RELATIVE_PATH
        atomic_write_json(state_path, self.snapshot())

    def all_providers(self) -> List[str]:
        """Return list of all configured provider names."""
        return list(self._health.keys())
