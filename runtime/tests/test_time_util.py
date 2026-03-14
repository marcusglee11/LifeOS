"""Tests: runtime.util.time timestamp discipline (Phase 2B — Constitutional Compliance)."""
from __future__ import annotations

import pytest

from runtime.util.time import audit_timestamp, deterministic_timestamp


# ---------------------------------------------------------------------------
# 2B-1: audit_timestamp returns valid ISO 8601
# ---------------------------------------------------------------------------

def test_audit_timestamp_is_valid_iso():
    from datetime import datetime
    ts = audit_timestamp()
    dt = datetime.fromisoformat(ts)  # raises if invalid
    assert dt is not None


def test_audit_timestamp_is_utc():
    ts = audit_timestamp()
    assert "+" in ts or ts.endswith("Z") or "+00:00" in ts or ts.endswith("+00:00")


# ---------------------------------------------------------------------------
# 2B-2: deterministic_timestamp validates and returns the pinned value
# ---------------------------------------------------------------------------

def test_deterministic_timestamp_returns_pinned():
    pinned = "2026-01-01T00:00:00+00:00"
    result = deterministic_timestamp(pinned)
    assert result == pinned


def test_deterministic_timestamp_rejects_empty():
    with pytest.raises(ValueError, match="must not be empty"):
        deterministic_timestamp("")


def test_deterministic_timestamp_rejects_whitespace():
    with pytest.raises(ValueError, match="must not be empty"):
        deterministic_timestamp("   ")


def test_deterministic_timestamp_rejects_invalid():
    with pytest.raises(ValueError, match="invalid ISO 8601"):
        deterministic_timestamp("not-a-date")


# ---------------------------------------------------------------------------
# 2C: Envelope post-hoc check returns list (empty when clean)
# ---------------------------------------------------------------------------

def test_envelope_post_hoc_returns_list():
    from runtime.envelope.execution_envelope import ExecutionEnvelope
    envelope = ExecutionEnvelope()
    result = envelope.verify_network_restrictions_post_hoc()
    assert isinstance(result, list)
