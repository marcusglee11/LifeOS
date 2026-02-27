"""
Bypass Monitor - Trusted Builder bypass utilization monitoring.

Reads the attempt ledger and tracks bypass events in a rolling window.
Emits structured warnings when bypass utilization exceeds configured thresholds.

Thresholds (rolling window of last N entries):
- ok:    bypass rate < 0.3
- warn:  bypass rate >= 0.3 and < 0.5
- alert: bypass rate >= 0.5

Fail-closed: malformed ledger data or I/O errors return alert-level status
with reason indicating the failure mode.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Default rolling window size
DEFAULT_WINDOW_SIZE = 10

# Thresholds
WARN_THRESHOLD = 0.3
ALERT_THRESHOLD = 0.5


@dataclass(frozen=True)
class BypassStatus:
    """Structured bypass utilization status."""

    level: str  # "ok" | "warn" | "alert"
    bypass_count: int
    total_count: int
    rate: float
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        if self.level not in ("ok", "warn", "alert"):
            raise ValueError(f"Invalid level: {self.level!r}")
        if self.bypass_count < 0:
            raise ValueError(f"bypass_count must be non-negative, got {self.bypass_count}")
        if self.total_count < 0:
            raise ValueError(f"total_count must be non-negative, got {self.total_count}")
        if not (0.0 <= self.rate <= 1.0):
            raise ValueError(f"rate must be between 0.0 and 1.0, got {self.rate}")


def _classify_level(rate: float) -> str:
    """Classify bypass rate into level."""
    if rate >= ALERT_THRESHOLD:
        return "alert"
    elif rate >= WARN_THRESHOLD:
        return "warn"
    return "ok"


def check_bypass_utilization(
    ledger_path: Path,
    window_size: int = DEFAULT_WINDOW_SIZE,
) -> BypassStatus:
    """
    Check bypass utilization from the attempt ledger.

    Reads the JSONL ledger file, extracts the last `window_size` attempt
    records, and computes the bypass rate based on the presence of
    `plan_bypass_info` in each record.

    Args:
        ledger_path: Path to the attempt ledger JSONL file.
        window_size: Number of most recent entries to consider.

    Returns:
        BypassStatus with level, counts, and rate.

    Fail-closed behavior:
        - Missing file: returns alert with reason="ledger_missing"
        - Malformed JSON: returns alert with reason="ledger_corrupt"
        - I/O error: returns alert with reason="io_error"
    """
    if window_size <= 0:
        raise ValueError(f"window_size must be positive, got {window_size}")

    try:
        if not ledger_path.exists():
            return BypassStatus(
                level="alert",
                bypass_count=0,
                total_count=0,
                rate=0.0,
                reason="ledger_missing",
            )

        with open(ledger_path, "r") as f:
            lines = f.readlines()
    except OSError as e:
        return BypassStatus(
            level="alert",
            bypass_count=0,
            total_count=0,
            rate=0.0,
            reason=f"io_error: {e}",
        )

    # Parse records (skip header line and empty lines)
    records = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            return BypassStatus(
                level="alert",
                bypass_count=0,
                total_count=0,
                rate=0.0,
                reason="ledger_corrupt",
            )
        if not isinstance(entry, dict):
            return BypassStatus(
                level="alert",
                bypass_count=0,
                total_count=0,
                rate=0.0,
                reason="ledger_corrupt",
            )
        # Skip header entries (they have "type": "header")
        if entry.get("type") == "header":
            continue
        records.append(entry)

    if not records:
        return BypassStatus(
            level="ok",
            bypass_count=0,
            total_count=0,
            rate=0.0,
        )

    # Take the last `window_size` records
    window = records[-window_size:]
    total = len(window)
    bypasses = sum(
        1 for r in window
        if r.get("plan_bypass_info") is not None
    )

    rate = bypasses / total if total > 0 else 0.0
    level = _classify_level(rate)

    return BypassStatus(
        level=level,
        bypass_count=bypasses,
        total_count=total,
        rate=round(rate, 4),
    )
