"""Tests for runtime/channels/telegram/sessions.py."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from runtime.channels.telegram import sessions as sess_mod
from runtime.channels.telegram.sessions import (
    clear_pending_escalation,
    clear_session,
    get_or_create_session,
    get_pending_escalation,
    set_pending_escalation,
)

_SESSIONS_PATH = Path("artifacts/status/coo_telegram_sessions.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sessions_file(tmp_path: Path) -> Path:
    return tmp_path / _SESSIONS_PATH


def _write_raw(tmp_path: Path, data: dict) -> None:
    path = _sessions_file(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def _read_raw(tmp_path: Path) -> dict:
    path = _sessions_file(tmp_path)
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _fresh_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stale_iso() -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=61)).isoformat()


# ---------------------------------------------------------------------------
# get_or_create_session
# ---------------------------------------------------------------------------


def test_get_or_create_creates_new_session(tmp_path: Path) -> None:
    sid = get_or_create_session(tmp_path, 42)
    assert sid != ""
    data = _read_raw(tmp_path)
    assert "42" in data
    assert data["42"]["session_id"] == sid


def test_get_or_create_returns_existing_session(tmp_path: Path) -> None:
    sid1 = get_or_create_session(tmp_path, 42)
    sid2 = get_or_create_session(tmp_path, 42)
    assert sid1 == sid2


def test_get_or_create_different_chat_ids_independent(tmp_path: Path) -> None:
    sid_a = get_or_create_session(tmp_path, 1)
    sid_b = get_or_create_session(tmp_path, 2)
    assert sid_a != sid_b


def test_get_or_create_expired_session_replaced(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_raw(tmp_path, {
        "99": {
            "session_id": "old-id",
            "pending_escalation": None,
            "last_updated": _stale_iso(),
        }
    })
    new_sid = get_or_create_session(tmp_path, 99)
    assert new_sid != "old-id"


def test_sessions_file_created_on_first_write(tmp_path: Path) -> None:
    path = _sessions_file(tmp_path)
    assert not path.exists()
    get_or_create_session(tmp_path, 7)
    assert path.exists()


# ---------------------------------------------------------------------------
# clear_session
# ---------------------------------------------------------------------------


def test_clear_session_removes_entry(tmp_path: Path) -> None:
    get_or_create_session(tmp_path, 10)
    clear_session(tmp_path, 10)
    data = _read_raw(tmp_path)
    assert "10" not in data


def test_clear_session_noop_if_absent(tmp_path: Path) -> None:
    clear_session(tmp_path, 999)  # should not raise


# ---------------------------------------------------------------------------
# get_pending_escalation / set_pending_escalation / clear_pending_escalation
# ---------------------------------------------------------------------------

_SAMPLE_ESCALATION = {
    "escalation_id": "ESC-0001",
    "options": [
        {"option_id": "A", "title": "Approve", "action": "Do it", "resolution_action": "approve"},
        {"option_id": "B", "title": "Reject", "action": "Abort", "resolution_action": "reject"},
    ],
    "presented_at": _fresh_iso(),
}


def test_set_and_get_pending_escalation(tmp_path: Path) -> None:
    set_pending_escalation(tmp_path, 5, _SAMPLE_ESCALATION)
    result = get_pending_escalation(tmp_path, 5)
    assert result is not None
    assert result["escalation_id"] == "ESC-0001"
    assert len(result["options"]) == 2


def test_get_pending_escalation_returns_none_when_absent(tmp_path: Path) -> None:
    assert get_pending_escalation(tmp_path, 5) is None


def test_clear_pending_escalation_nulls_field(tmp_path: Path) -> None:
    set_pending_escalation(tmp_path, 5, _SAMPLE_ESCALATION)
    clear_pending_escalation(tmp_path, 5)
    assert get_pending_escalation(tmp_path, 5) is None
    # Session itself still exists
    data = _read_raw(tmp_path)
    assert "5" in data
    assert data["5"]["pending_escalation"] is None


def test_clear_pending_escalation_noop_if_no_session(tmp_path: Path) -> None:
    clear_pending_escalation(tmp_path, 404)  # should not raise


def test_expired_session_treated_as_absent(tmp_path: Path) -> None:
    _write_raw(tmp_path, {
        "77": {
            "session_id": "x",
            "pending_escalation": _SAMPLE_ESCALATION,
            "last_updated": _stale_iso(),
        }
    })
    assert get_pending_escalation(tmp_path, 77) is None


def test_set_pending_escalation_overwrites_previous(tmp_path: Path) -> None:
    set_pending_escalation(tmp_path, 5, _SAMPLE_ESCALATION)
    new_esc = {**_SAMPLE_ESCALATION, "escalation_id": "ESC-0002"}
    set_pending_escalation(tmp_path, 5, new_esc)
    result = get_pending_escalation(tmp_path, 5)
    assert result["escalation_id"] == "ESC-0002"


def test_corrupt_sessions_file_returns_empty(tmp_path: Path) -> None:
    path = _sessions_file(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not valid json")
    assert get_pending_escalation(tmp_path, 1) is None
    sid = get_or_create_session(tmp_path, 1)
    assert sid != ""
