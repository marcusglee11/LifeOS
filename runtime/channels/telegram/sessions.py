"""Per-chat session state for the Telegram bot.

Separate from status.py (bot-level heartbeat). This module manages user-scoped
session state, keyed by chat_id. v1 stubs only — wires in future session_id storage.
"""
from __future__ import annotations

from pathlib import Path

_SESSIONS_RELATIVE = Path("artifacts/status/coo_telegram_sessions.json")


def clear_session(repo_root: Path, chat_id: int | str) -> None:  # noqa: ARG001
    """Clear session state for the given chat_id. v1 stub — no-op."""
    return


def get_or_create_session(
    repo_root: Path,  # noqa: ARG001
    chat_id: int | str,  # noqa: ARG001
    ttl_minutes: int = 30,  # noqa: ARG001
) -> str:
    """Return the session_id for the given chat_id, creating one if absent.

    v1 stub — returns empty string.
    """
    return ""
