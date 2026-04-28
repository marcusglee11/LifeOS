from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from runtime.util.atomic_write import atomic_write_json

DEFAULT_STATE_PATH = Path.home() / ".config" / "lifeos-google" / "calendar_webhooks" / "state.json"
DEFAULT_GWS_BIN = Path.home() / ".config" / "lifeos-google" / "bin" / "lifeos-gws"


@dataclass
class CalendarChannelState:
    channel_id: str
    resource_id: str
    calendar_id: str = "primary"
    sync_token: str | None = None
    expiration_ms: int | None = None
    channel_expiration: str | None = None
    renewal_requested_at: str | None = None
    initial_sync_seen: bool = False

    def renewal_due(self, *, now_ms: int, lead_ms: int = 86_400_000) -> bool:
        if self.expiration_ms is None:
            return False
        return self.expiration_ms <= now_ms + lead_ms

    def expired(self, *, now_ms: int) -> bool:
        return self.expiration_ms is not None and self.expiration_ms <= now_ms


@dataclass
class CalendarWebhookState:
    schema_version: str = "lifeos.google_calendar_webhook_state.v0"
    channels: dict[str, CalendarChannelState] = field(default_factory=dict)
    processed_notifications: list[str] = field(default_factory=list)
    max_processed_notifications: int = 1000

    def has_processed(self, dedupe_key: str) -> bool:
        return dedupe_key in set(self.processed_notifications)

    def mark_processed(self, dedupe_key: str) -> None:
        if dedupe_key in self.processed_notifications:
            return
        self.processed_notifications.append(dedupe_key)
        overflow = len(self.processed_notifications) - self.max_processed_notifications
        if overflow > 0:
            del self.processed_notifications[:overflow]

    def channels_due_for_renewal(self, *, now_ms: int, lead_ms: int = 86_400_000) -> list[str]:
        return sorted(
            channel_id
            for channel_id, channel in self.channels.items()
            if channel.renewal_due(now_ms=now_ms, lead_ms=lead_ms)
        )

    def expired_channels(self, *, now_ms: int) -> list[str]:
        return sorted(
            channel_id
            for channel_id, channel in self.channels.items()
            if channel.expired(now_ms=now_ms)
        )


class CalendarWebhookStateStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or DEFAULT_STATE_PATH

    def load(self) -> CalendarWebhookState:
        if not self.path.exists():
            return CalendarWebhookState()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        channels = {
            channel_id: CalendarChannelState(**channel_payload)
            for channel_id, channel_payload in (payload.get("channels") or {}).items()
        }
        return CalendarWebhookState(
            schema_version=payload.get(
                "schema_version",
                "lifeos.google_calendar_webhook_state.v0",
            ),
            channels=channels,
            processed_notifications=list(payload.get("processed_notifications") or []),
            max_processed_notifications=int(payload.get("max_processed_notifications", 1000)),
        )

    def save(self, state: CalendarWebhookState) -> None:
        payload = {
            "schema_version": state.schema_version,
            "channels": {
                channel_id: asdict(channel)
                for channel_id, channel in sorted(state.channels.items())
            },
            "processed_notifications": list(state.processed_notifications),
            "max_processed_notifications": state.max_processed_notifications,
            "shared_google_surface": {
                "default_gws_bin": str(DEFAULT_GWS_BIN),
                "default_credentials_dir": str(Path.home() / ".config" / "lifeos-google"),
                "notes": "Tests use injected clients; no real Google credentials required.",
            },
        }
        atomic_write_json(self.path, payload, indent=2, sort_keys=True)
