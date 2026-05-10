from datetime import datetime, timedelta, timezone

import pytest

from runtime.receipts.intent_fidelity import (
    NOT_AUTHORIZED_FOR,
    _bypass_registry,
    check_bypass_valid,
    create_bypass,
    get_active_bypasses,
    use_bypass,
)


@pytest.fixture(autouse=True)
def clear_registry():
    _bypass_registry.clear()
    yield
    _bypass_registry.clear()


def test_bypass_expires_within_24h():
    before = datetime.now(timezone.utc)
    bypass_id = create_bypass("W-1", "tool", "conductor", "known false positive", "warning-only")
    expires_at = datetime.fromisoformat(_bypass_registry[bypass_id]["expires_at"])
    assert expires_at - before <= timedelta(hours=24, seconds=1)


def test_bypass_is_single_use():
    bypass_id = create_bypass("W-1", "tool", "conductor", "known false positive", "warning-only")
    assert use_bypass(bypass_id) == (True, "used")
    assert check_bypass_valid(bypass_id) == (False, "already_used")


def test_bypass_cannot_cover_ceo_only_classes_without_ceo_authorization():
    with pytest.raises(ValueError, match="CEO approval required"):
        create_bypass(
            "W-1",
            "tool",
            "conductor",
            "missing source",
            "privacy blocking class",
        )


def test_expired_bypass_is_invalid():
    bypass_id = create_bypass("W-1", "tool", "conductor", "known false positive", "warning-only")
    _bypass_registry[bypass_id]["expires_at"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    assert check_bypass_valid(bypass_id) == (False, "expired")


def test_used_bypass_is_invalid():
    bypass_id = create_bypass("W-1", "tool", "conductor", "known false positive", "warning-only")
    _bypass_registry[bypass_id]["_used"] = True
    assert check_bypass_valid(bypass_id) == (False, "already_used")


def test_non_ceo_authorized_bypass_for_destructive_class_fails():
    with pytest.raises(ValueError, match="CEO approval required"):
        create_bypass(
            "W-1",
            "tool",
            "conductor",
            "missing source",
            "absence destructive class",
            admissible_missing_policy="destructive cleanup",
        )


def test_active_bypasses_omit_used_and_include_forbidden_scope():
    bypass_id = create_bypass("W-1", "tool", "conductor", "known false positive", "warning-only")
    active = get_active_bypasses()
    assert len(active) == 1
    assert active[0]["not_authorized_for"] == NOT_AUTHORIZED_FOR
    use_bypass(bypass_id)
    assert get_active_bypasses() == []
