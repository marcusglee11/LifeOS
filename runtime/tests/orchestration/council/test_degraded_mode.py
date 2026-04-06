"""Unit tests for degraded-mode decision logic in provider_preflight.py."""

from __future__ import annotations

from runtime.orchestration.council.models import ProviderHealthResult, SeatFailureClass
from runtime.orchestration.council.provider_preflight import is_run_blocked


def _health(status: SeatFailureClass) -> ProviderHealthResult:
    return ProviderHealthResult(
        provider="p",
        auth_ok=status == SeatFailureClass.seat_completed,
        echo_ok=status == SeatFailureClass.seat_completed,
        status=status,
    )


# ---------------------------------------------------------------------------
# Block rules
# ---------------------------------------------------------------------------


def test_all_available_not_blocked():
    results = {
        "p1": _health(SeatFailureClass.seat_completed),
        "p2": _health(SeatFailureClass.seat_completed),
    }
    blocked, _ = is_run_blocked(results, required_providers={"p1", "p2"})
    assert not blocked


def test_one_unavailable_blocks_run():
    results = {
        "p1": _health(SeatFailureClass.seat_completed),
        "p2": _health(SeatFailureClass.provider_unavailable),
    }
    blocked, reason = is_run_blocked(results, required_providers={"p1", "p2"})
    assert blocked
    assert "blocked_provider" in reason
    assert "p2" in reason


def test_quota_failure_blocks_run():
    results = {"p1": _health(SeatFailureClass.provider_quota)}
    blocked, _ = is_run_blocked(results, required_providers={"p1"})
    assert blocked


def test_timeout_blocks_run():
    results = {"p1": _health(SeatFailureClass.seat_timeout)}
    blocked, _ = is_run_blocked(results, required_providers={"p1"})
    assert blocked


def test_non_required_provider_unavailable_does_not_block():
    """Providers not in required_providers set are not gating."""
    results = {
        "p1": _health(SeatFailureClass.seat_completed),
        "p2": _health(SeatFailureClass.provider_unavailable),  # not required
    }
    blocked, _ = is_run_blocked(results, required_providers={"p1"})
    assert not blocked


# ---------------------------------------------------------------------------
# Carry-forward rules
# ---------------------------------------------------------------------------


def test_ccp_declared_carry_forward_allows_unavailable():
    results = {"p1": _health(SeatFailureClass.provider_unavailable)}
    blocked, _ = is_run_blocked(
        results,
        required_providers={"p1"},
        carry_forward_allowed=True,
        carry_forward_providers={"p1"},
    )
    assert not blocked


def test_undeclared_carry_forward_still_blocks():
    """carry_forward_allowed=True but provider not declared → still blocked."""
    results = {"p1": _health(SeatFailureClass.provider_unavailable)}
    blocked, _ = is_run_blocked(
        results,
        required_providers={"p1"},
        carry_forward_allowed=True,
        carry_forward_providers={"p2"},  # p1 not declared
    )
    assert blocked


def test_carry_forward_false_ignores_declared_set():
    """Even if carry_forward_providers is set, allowed=False means block."""
    results = {"p1": _health(SeatFailureClass.provider_unavailable)}
    blocked, _ = is_run_blocked(
        results,
        required_providers={"p1"},
        carry_forward_allowed=False,
        carry_forward_providers={"p1"},
    )
    assert blocked


def test_carry_forward_partial_one_declared_one_not():
    """One provider declared for carry-forward, another not → still blocked."""
    results = {
        "p1": _health(SeatFailureClass.provider_unavailable),
        "p2": _health(SeatFailureClass.provider_unavailable),
    }
    blocked, reason = is_run_blocked(
        results,
        required_providers={"p1", "p2"},
        carry_forward_allowed=True,
        carry_forward_providers={"p1"},  # only p1 declared
    )
    assert blocked
    assert "p2" in reason


def test_missing_provider_in_results_treated_as_unavailable():
    """Provider in required_providers but absent from health_results → blocked."""
    blocked, reason = is_run_blocked(
        {},
        required_providers={"missing-provider"},
    )
    assert blocked
    assert "missing-provider" in reason
