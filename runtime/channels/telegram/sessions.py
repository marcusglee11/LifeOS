"""Per-chat session state for the Telegram bot.

Separate from status.py (bot-level heartbeat). This module manages user-scoped
session state, keyed by chat_id. State is persisted to
artifacts/status/coo_telegram_sessions.json with atomic-write semantics and a
30-minute TTL.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from runtime.util.atomic_write import atomic_write_text

_SESSIONS_RELATIVE = Path("artifacts/status/coo_telegram_sessions.json")
_TTL_MINUTES = 30


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _load_all(repo_root: Path) -> dict[str, Any]:
    path = repo_root / _SESSIONS_RELATIVE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text()) or {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_all(repo_root: Path, data: dict[str, Any]) -> None:
    path = repo_root / _SESSIONS_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(path, json.dumps(data, indent=2))


def _is_expired(session: dict[str, Any]) -> bool:
    last_updated = session.get("last_updated", "")
    if not last_updated:
        return True
    try:
        ts = datetime.fromisoformat(last_updated)
    except (ValueError, TypeError):
        return True
    return (_utc_now() - ts) > timedelta(minutes=_TTL_MINUTES)


def _prune_expired(data: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in data.items() if not _is_expired(v)}


def get_or_create_session(
    repo_root: Path,
    chat_id: int | str,
    ttl_minutes: int = _TTL_MINUTES,  # noqa: ARG001 — kept for API compat
) -> str:
    """Return the session_id for chat_id, creating one if absent or expired."""
    data = _load_all(repo_root)
    key = str(chat_id)
    session = data.get(key)
    if session is None or _is_expired(session):
        session_id = str(uuid.uuid4())
        data[key] = {
            "session_id": session_id,
            "pending_escalation": None,
            "last_updated": _utc_now_iso(),
        }
        _save_all(repo_root, _prune_expired(data))
        return session_id
    return str(session.get("session_id", ""))


def clear_session(repo_root: Path, chat_id: int | str) -> None:
    """Clear all session state for chat_id."""
    data = _load_all(repo_root)
    key = str(chat_id)
    if key in data:
        del data[key]
        _save_all(repo_root, _prune_expired(data))


def get_pending_escalation(
    repo_root: Path, chat_id: int | str
) -> dict[str, Any] | None:
    """Return the pending escalation dict for chat_id, or None if absent/expired."""
    data = _load_all(repo_root)
    key = str(chat_id)
    session = data.get(key)
    if session is None or _is_expired(session):
        return None
    return session.get("pending_escalation") or None


def set_pending_escalation(
    repo_root: Path, chat_id: int | str, escalation: dict[str, Any]
) -> None:
    """Persist a pending escalation to session state for chat_id."""
    data = _prune_expired(_load_all(repo_root))
    key = str(chat_id)
    session = data.get(key) or {
        "session_id": str(uuid.uuid4()),
        "pending_escalation": None,
    }
    session["pending_escalation"] = escalation
    session["last_updated"] = _utc_now_iso()
    data[key] = session
    _save_all(repo_root, data)


def clear_pending_escalation(repo_root: Path, chat_id: int | str) -> None:
    """Remove pending_escalation from session state without clearing the session."""
    data = _load_all(repo_root)
    key = str(chat_id)
    session = data.get(key)
    if session is not None and not _is_expired(session):
        session["pending_escalation"] = None
        session["last_updated"] = _utc_now_iso()
        data[key] = session
        _save_all(repo_root, _prune_expired(data))
