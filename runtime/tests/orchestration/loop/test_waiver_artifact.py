"""
Test suite for waiver_artifact.py

Tests cover:
- WaiverGrant creation and validation
- Round-trip write/read operations (module-level functions)
- Expiry and validity checks
- Context binding and mismatch detection
- Error handling for missing/malformed data
- Path determinism
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

import pytest

from runtime.orchestration.loop.waiver_artifact import (
    WaiverGrant,
    WaiverValidationError,
    check_waiver_for_context,
    get_waiver_path,
    is_valid,
    read,
    write,
)


_CTX: Dict[str, Any] = {"failure_class": "test_failure", "path": "runtime/foo.py"}
_NOW = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)


def test_waiver_grant_create():
    """Verify WaiverGrant.create() produces valid instance with all 8 fields."""
    grant = WaiverGrant.create(
        context=_CTX,
        reason="Testing waiver creation",
        granted_by="test_user",
        ttl_seconds=3600,
        now=_NOW,
    )

    assert grant.schema_version == "1.0"
    assert grant.context == _CTX
    assert grant.reason == "Testing waiver creation"
    assert grant.granted_by == "test_user"
    assert grant.granted_at == _NOW.isoformat()
    assert grant.expires_at == (_NOW + timedelta(seconds=3600)).isoformat()
    assert grant.ttl_seconds == 3600
    assert isinstance(grant.waiver_id, str)


def test_round_trip_write_read(tmp_path: Path):
    """Create grant -> write() -> read() -> validate all fields match."""
    original = WaiverGrant.create(
        context=_CTX,
        reason="Round trip validation",
        granted_by="test_system",
        ttl_seconds=7200,
        now=_NOW,
    )

    waiver_file = tmp_path / "waiver.json"
    write(waiver_file, original)

    assert waiver_file.exists()

    loaded = read(waiver_file)

    assert loaded.schema_version == original.schema_version
    assert loaded.context == original.context
    assert loaded.reason == original.reason
    assert loaded.granted_by == original.granted_by
    assert loaded.granted_at == original.granted_at
    assert loaded.expires_at == original.expires_at
    assert loaded.ttl_seconds == original.ttl_seconds
    assert loaded.waiver_id == original.waiver_id


def test_is_valid_fresh_waiver(tmp_path: Path):
    """Create waiver, verify is_valid() returns True."""
    grant = WaiverGrant.create(
        context=_CTX,
        reason="Testing fresh waiver",
        granted_by="test_user",
        ttl_seconds=3600,
        now=_NOW,
    )

    waiver_file = tmp_path / "fresh_waiver.json"
    write(waiver_file, grant)

    assert is_valid(waiver_file, context=_CTX, now=_NOW) is True

    # 1 hour in, still within ttl
    future = _NOW + timedelta(seconds=1800)
    assert is_valid(waiver_file, context=_CTX, now=future) is True


def test_is_valid_expired_waiver(tmp_path: Path):
    """Create waiver with ttl_seconds=3600, check is_valid(now=future) returns False."""
    grant = WaiverGrant.create(
        context=_CTX,
        reason="Testing expiry",
        granted_by="test_user",
        ttl_seconds=3600,
        now=_NOW,
    )

    waiver_file = tmp_path / "expiry_waiver.json"
    write(waiver_file, grant)

    future = _NOW + timedelta(seconds=3601)
    assert is_valid(waiver_file, context=_CTX, now=future) is False


def test_read_missing_file(tmp_path: Path):
    """Verify read() raises WaiverValidationError for non-existent file."""
    non_existent = tmp_path / "does_not_exist.json"

    with pytest.raises(WaiverValidationError, match="Waiver artifact not found"):
        read(non_existent)


def test_read_missing_required_field(tmp_path: Path):
    """Write JSON missing 'reason' field, verify read() raises WaiverValidationError."""
    waiver_file = tmp_path / "missing_field.json"

    waiver_file.write_text(json.dumps({
        "schema_version": "1.0",
        "context": {"k": "v"},
        "granted_by": "user",
        "granted_at": "2024-01-15T12:00:00+00:00",
        "expires_at": "2024-01-15T13:00:00+00:00",
        "ttl_seconds": 3600,
        "waiver_id": "abc123",
        # 'reason' intentionally missing
    }))

    with pytest.raises(WaiverValidationError, match="Missing required field"):
        read(waiver_file)


def test_read_schema_version_mismatch(tmp_path: Path):
    """Write JSON with schema_version='99.0', verify read() raises WaiverValidationError."""
    waiver_file = tmp_path / "wrong_schema.json"

    waiver_file.write_text(json.dumps({
        "schema_version": "99.0",
        "context": {"k": "v"},
        "reason": "test",
        "granted_by": "user",
        "granted_at": "2024-01-15T12:00:00+00:00",
        "expires_at": "2024-01-15T13:00:00+00:00",
        "ttl_seconds": 3600,
        "waiver_id": "abc123",
    }))

    with pytest.raises(WaiverValidationError, match="Schema version mismatch"):
        read(waiver_file)


def test_is_valid_context_mismatch(tmp_path: Path):
    """Create waiver for context A, verify is_valid(context=B) returns False."""
    ctx_a = {"failure_class": "context_a"}
    ctx_b = {"failure_class": "context_b"}

    grant = WaiverGrant.create(
        context=ctx_a,
        reason="Testing context binding",
        granted_by="test_user",
        ttl_seconds=3600,
        now=_NOW,
    )

    waiver_file = tmp_path / "context_waiver.json"
    write(waiver_file, grant)

    assert is_valid(waiver_file, context=ctx_a, now=_NOW) is True
    assert is_valid(waiver_file, context=ctx_b, now=_NOW) is False


def test_check_waiver_for_context_valid(tmp_path: Path):
    """Use check_waiver_for_context() convenience wrapper for valid waiver."""
    grant = WaiverGrant.create(
        context=_CTX,
        reason="Testing convenience function",
        granted_by="test_user",
        ttl_seconds=3600,
        now=_NOW,
    )

    waiver_path = get_waiver_path(_CTX, base_dir=tmp_path)
    write(waiver_path, grant)

    result = check_waiver_for_context(_CTX, now=_NOW, base_dir=tmp_path)
    assert result is True


def test_check_waiver_for_context_missing(tmp_path: Path):
    """Use check_waiver_for_context() for non-existent waiver."""
    ctx = {"failure_class": "no_waiver_here"}
    result = check_waiver_for_context(ctx, now=_NOW, base_dir=tmp_path)
    assert result is False


def test_get_waiver_path_deterministic(tmp_path: Path):
    """Verify same context produces same path twice."""
    ctx = {"failure_class": "deterministic_test"}

    path1 = get_waiver_path(ctx, base_dir=tmp_path)
    path2 = get_waiver_path(ctx, base_dir=tmp_path)

    assert path1 == path2
    assert path1.name.startswith("WAIVER_")
    assert path1.name.endswith(".json")

    # Different context produces different path
    ctx2 = {"failure_class": "different_context"}
    path3 = get_waiver_path(ctx2, base_dir=tmp_path)
    assert path3 != path1
