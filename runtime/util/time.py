"""
Timestamp utilities for LifeOS determinism discipline.

Two distinct timestamp categories exist in LifeOS:

1. **AUDIT-ONLY** (`audit_timestamp`) — wall-clock UTC ISO timestamps for
   human-readable audit trails. These MUST NOT be used in deterministic
   computations (hashing, ID derivation, content-addressable keys).

2. **Deterministic** (`deterministic_timestamp`) — pinned timestamps that
   have been pre-validated for use inside the deterministic envelope.
   Callers must supply the pinned value; this function only validates it.

Usage pattern:
    from runtime.util.time import audit_timestamp
    ts = audit_timestamp()   # OK in receipts, logs, human-readable output
"""

from __future__ import annotations

from datetime import datetime, timezone


def audit_timestamp() -> str:
    """
    Return current UTC time as ISO 8601 string.

    AUDIT-ONLY: This is wall-clock time and MUST NOT be used in
    deterministic computations (hashing, ID derivation, content keys).
    Use only for: receipts, log metadata, human-readable timestamps.
    """
    return datetime.now(timezone.utc).isoformat()


def deterministic_timestamp(pinned: str) -> str:
    """
    Validate and return a pinned timestamp for deterministic contexts.

    Args:
        pinned: An ISO 8601 timestamp string that was pinned before the
                deterministic computation began (e.g., from a fixture or
                workflow start parameter).

    Returns:
        The validated pinned timestamp string.

    Raises:
        ValueError: If the pinned value is empty or not a valid ISO 8601 string.
    """
    if not pinned or not pinned.strip():
        raise ValueError("deterministic_timestamp: pinned timestamp must not be empty")
    try:
        datetime.fromisoformat(pinned.strip())
    except ValueError as exc:
        raise ValueError(f"deterministic_timestamp: invalid ISO 8601 value: {pinned!r}") from exc
    return pinned.strip()
