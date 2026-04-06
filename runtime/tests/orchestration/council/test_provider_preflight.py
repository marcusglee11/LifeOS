"""Unit tests for runtime/orchestration/council/provider_preflight.py."""

from __future__ import annotations

import os
from unittest.mock import patch

from runtime.orchestration.council.models import ProviderHealthResult, SeatFailureClass
from runtime.orchestration.council.provider_preflight import (
    _classify_error,
    check_provider,
    is_run_blocked,
    run_preflight,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _ok_probe(model: str, timeout: float) -> tuple[bool, str | None]:
    return True, None


def _fail_probe(model: str, timeout: float) -> tuple[bool, str | None]:
    return False, "connection refused"


def _quota_probe(model: str, timeout: float) -> tuple[bool, str | None]:
    return False, "rate_limit exceeded (429)"


def _timeout_probe(model: str, timeout: float) -> tuple[bool, str | None]:
    # Simulate a latency equal to the full timeout
    import time
    time.sleep(0)  # no real sleep; latency is faked via classify_error directly
    return False, "timed out after 30s"


# ---------------------------------------------------------------------------
# _classify_error
# ---------------------------------------------------------------------------


def test_classify_error_quota():
    assert _classify_error("rate limit exceeded (429)", 0.1, 30) == SeatFailureClass.provider_quota


def test_classify_error_quota_too_many():
    assert _classify_error("too many requests", 0.1, 30) == SeatFailureClass.provider_quota


def test_classify_error_timeout():
    # latency >= 95% of timeout → seat_timeout
    assert _classify_error("some error", 29.5, 30) == SeatFailureClass.seat_timeout


def test_classify_error_unavailable():
    assert _classify_error("connection refused", 0.5, 30) == SeatFailureClass.provider_unavailable


# ---------------------------------------------------------------------------
# check_provider
# ---------------------------------------------------------------------------


def test_check_provider_auth_failure():
    """Missing ZEN_REVIEWER_KEY → provider_unavailable immediately."""
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("ZEN_REVIEWER_KEY", None)
        result = check_provider("openrouter/kimi", "openrouter/moonshotai/kimi-k2.5", echo_probe=_ok_probe)
    assert result.auth_ok is False
    assert result.echo_ok is False
    assert result.status == SeatFailureClass.provider_unavailable


def test_check_provider_success():
    with patch.dict(os.environ, {"ZEN_REVIEWER_KEY": "test-key"}):
        result = check_provider("openrouter/kimi", "openrouter/moonshotai/kimi-k2.5", echo_probe=_ok_probe)
    assert result.auth_ok is True
    assert result.echo_ok is True
    assert result.status == SeatFailureClass.seat_completed


def test_check_provider_network_failure():
    """Echo probe fails twice → provider_unavailable."""
    with patch.dict(os.environ, {"ZEN_REVIEWER_KEY": "test-key"}):
        result = check_provider("openrouter/kimi", "openrouter/moonshotai/kimi-k2.5", echo_probe=_fail_probe)
    assert result.auth_ok is True
    assert result.echo_ok is False
    assert result.status == SeatFailureClass.provider_unavailable


def test_check_provider_quota_failure():
    with patch.dict(os.environ, {"ZEN_REVIEWER_KEY": "test-key"}):
        result = check_provider("openrouter/kimi", "openrouter/moonshotai/kimi-k2.5", echo_probe=_quota_probe)
    assert result.status == SeatFailureClass.provider_quota


def test_check_provider_retries_once_on_failure():
    """Probe is called twice before marking unavailable."""
    call_count = 0

    def counting_probe(model: str, timeout: float) -> tuple[bool, str | None]:
        nonlocal call_count
        call_count += 1
        return False, "error"

    with patch.dict(os.environ, {"ZEN_REVIEWER_KEY": "test-key"}):
        check_provider("p", "m", echo_probe=counting_probe)

    assert call_count == 2


def test_check_provider_succeeds_on_second_attempt():
    """Probe succeeds on second attempt → seat_completed."""
    call_count = 0

    def flaky_probe(model: str, timeout: float) -> tuple[bool, str | None]:
        nonlocal call_count
        call_count += 1
        return call_count >= 2, None if call_count >= 2 else "transient error"

    with patch.dict(os.environ, {"ZEN_REVIEWER_KEY": "test-key"}):
        result = check_provider("p", "m", echo_probe=flaky_probe)

    assert result.status == SeatFailureClass.seat_completed
    assert call_count == 2


# ---------------------------------------------------------------------------
# run_preflight
# ---------------------------------------------------------------------------


def test_run_preflight_all_ok():
    with patch.dict(os.environ, {"ZEN_REVIEWER_KEY": "test-key"}):
        results = run_preflight(
            {"model-a": "model-a", "model-b": "model-b"},
            echo_probe=_ok_probe,
        )
    assert all(r.status == SeatFailureClass.seat_completed for r in results.values())


def test_run_preflight_one_failing():
    probes = {"model-a": _ok_probe, "model-b": _fail_probe}

    def selective_probe(model: str, timeout: float) -> tuple[bool, str | None]:
        return probes[model](model, timeout)

    with patch.dict(os.environ, {"ZEN_REVIEWER_KEY": "test-key"}):
        results = run_preflight(
            {"model-a": "model-a", "model-b": "model-b"},
            echo_probe=selective_probe,
        )
    assert results["model-a"].status == SeatFailureClass.seat_completed
    assert results["model-b"].status == SeatFailureClass.provider_unavailable


# ---------------------------------------------------------------------------
# is_run_blocked
# ---------------------------------------------------------------------------


def _make_health(status: SeatFailureClass) -> ProviderHealthResult:
    return ProviderHealthResult(
        provider="p",
        auth_ok=status == SeatFailureClass.seat_completed,
        echo_ok=status == SeatFailureClass.seat_completed,
        status=status,
    )


def test_is_run_blocked_all_available():
    results = {"p1": _make_health(SeatFailureClass.seat_completed)}
    blocked, _ = is_run_blocked(results, required_providers={"p1"})
    assert not blocked


def test_is_run_blocked_unavailable_no_carry_forward():
    results = {"p1": _make_health(SeatFailureClass.provider_unavailable)}
    blocked, reason = is_run_blocked(results, required_providers={"p1"})
    assert blocked
    assert "blocked_provider" in reason


def test_is_run_blocked_carry_forward_declared():
    results = {"p1": _make_health(SeatFailureClass.provider_unavailable)}
    blocked, _ = is_run_blocked(
        results,
        required_providers={"p1"},
        carry_forward_allowed=True,
        carry_forward_providers={"p1"},
    )
    assert not blocked


def test_is_run_blocked_carry_forward_undeclared():
    """carry_forward_allowed=True but provider not in carry_forward_providers → still blocked."""
    results = {"p1": _make_health(SeatFailureClass.provider_unavailable)}
    blocked, _ = is_run_blocked(
        results,
        required_providers={"p1"},
        carry_forward_allowed=True,
        carry_forward_providers=set(),
    )
    assert blocked
