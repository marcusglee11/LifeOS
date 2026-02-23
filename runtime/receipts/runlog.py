"""
RunLog emitter for LifeOS build pipeline runs.

Emits structured run log events with deterministic ordering based on
PlanCore phase_order. Supports JSONL output and deterministic content
(with timestamps stripped for comparison).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .validator import assert_valid


@dataclass(frozen=True)
class RunLogEvent:
    """A single run log event."""
    phase: str
    step_id: str
    attempt_num: int
    seq: int
    timestamp: str
    event_type: str
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "phase": self.phase,
            "step_id": self.step_id,
            "attempt_num": self.attempt_num,
            "seq": self.seq,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
        }
        if self.data:
            d["data"] = self.data
        return d


class RunLogEmitter:
    """
    Emitter for run log events, ordered deterministically by PlanCore phase_order.

    Events are sorted by: (phase_order_index, step_id, attempt_num, seq)
    """

    def __init__(self, phase_order: list[str]) -> None:
        """
        Args:
            phase_order: Ordered list of phase names from PlanCore.
        """
        self._phase_order = phase_order
        self._phase_index = {phase: i for i, phase in enumerate(phase_order)}
        self._events: list[RunLogEvent] = []
        self._seq = 0

    def emit(
        self,
        phase: str,
        step_id: str,
        event_type: str,
        attempt_num: int = 0,
        data: dict | None = None,
    ) -> RunLogEvent:
        """
        Emit a new run log event.

        Args:
            phase: Phase name (should be in phase_order).
            step_id: Step identifier.
            event_type: Event type string.
            attempt_num: Attempt number (default 0).
            data: Optional event data dict.

        Returns:
            The created RunLogEvent.

        Raises:
            ReceiptValidationError: If the event fails schema validation.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        event = RunLogEvent(
            phase=phase,
            step_id=step_id,
            attempt_num=attempt_num,
            seq=self._seq,
            timestamp=timestamp,
            event_type=event_type,
            data=data or {},
        )
        assert_valid(event.to_dict(), "runlog_event")
        self._events.append(event)
        self._seq += 1
        return event

    def events(self) -> list[RunLogEvent]:
        """
        Return events sorted by (phase_order_index, step_id, attempt_num, seq).

        Phases not in phase_order get index len(phase_order) (appended at end).
        """
        max_idx = len(self._phase_order)

        def sort_key(e: RunLogEvent):
            phase_idx = self._phase_index.get(e.phase, max_idx)
            return (phase_idx, e.step_id, e.attempt_num, e.seq)

        return sorted(self._events, key=sort_key)

    def write_jsonl(self, path: Path | str) -> None:
        """
        Write events to a JSONL file (one JSON object per line).

        Args:
            path: Output file path.
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [json.dumps(e.to_dict(), sort_keys=True) for e in self.events()]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    def deterministic_content(self) -> list[dict]:
        """
        Return events as dicts with timestamps stripped.

        Used for determinism comparison between runs.

        Returns:
            List of event dicts without 'timestamp' keys.
        """
        result = []
        for event in self.events():
            d = event.to_dict()
            d.pop("timestamp", None)
            result.append(d)
        return result
