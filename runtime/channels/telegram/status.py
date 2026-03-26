"""Telegram bot runtime status — write/read the local state artifact."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_STATUS_RELATIVE = Path("artifacts/status/coo_telegram_runtime.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_path(repo_root: Path) -> Path:
    return repo_root / _STATUS_RELATIVE


def read_status(repo_root: Path) -> dict[str, Any] | None:
    """Read the status artifact.  Returns None if the file does not exist."""
    path = _status_path(repo_root)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception as exc:
        print(f"[telegram-status] read error: {exc}", file=sys.stderr)
        return None


def write_status(repo_root: Path, **fields: Any) -> None:
    """Merge *fields* into the status artifact and refresh updated_at.

    Fail-safe: any I/O error is printed to stderr and swallowed so callers
    never crash the bot due to a status write failure.
    """
    path = _status_path(repo_root)
    try:
        existing: dict[str, Any] = {}
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            pass
        existing.update(fields)
        existing["updated_at"] = _utc_now()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(existing, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"[telegram-status] write error: {exc}", file=sys.stderr)
