from __future__ import annotations

from typing import Any, Mapping


def for_openclaw(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Thin adapter preserving shared envelope while tagging OpenClaw consumer."""
    return {
        "kind": "lifeos.calendar_event.forward.v0",
        "target": "openclaw",
        "envelope": dict(envelope),
    }


def for_hermes(envelope: Mapping[str, Any]) -> dict[str, Any]:
    """Thin adapter preserving shared envelope while tagging Hermes consumer."""
    return {
        "kind": "lifeos.calendar_event.forward.v0",
        "target": "hermes",
        "envelope": dict(envelope),
    }
