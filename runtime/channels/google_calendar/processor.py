from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from runtime.channels.google_calendar.envelope import (
    CalendarPrivacyConfig,
    GoogleCalendarEvent,
    build_event_envelope,
)
from runtime.channels.google_calendar.state import CalendarChannelState, CalendarWebhookStateStore


@dataclass(frozen=True)
class GoogleCalendarNotification:
    channel_id: str
    resource_id: str
    resource_state: str
    message_number: int
    resource_uri: str | None = None
    channel_expiration: str | None = None

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> "GoogleCalendarNotification":
        normalized = {key.lower(): value for key, value in headers.items()}
        required_headers = (
            "x-goog-channel-id",
            "x-goog-resource-id",
            "x-goog-resource-state",
            "x-goog-message-number",
        )
        missing_headers = [header for header in required_headers if header not in normalized]
        if missing_headers:
            raise ValueError(f"missing_google_calendar_headers:{','.join(missing_headers)}")
        try:
            message_number = int(normalized["x-goog-message-number"])
        except ValueError as exc:
            raise ValueError("invalid_google_calendar_message_number") from exc
        return cls(
            channel_id=normalized["x-goog-channel-id"].strip(),
            resource_id=normalized["x-goog-resource-id"].strip(),
            resource_state=normalized["x-goog-resource-state"].strip(),
            message_number=message_number,
            resource_uri=normalized.get("x-goog-resource-uri"),
            channel_expiration=normalized.get("x-goog-channel-expiration"),
        )

    @property
    def dedupe_key(self) -> str:
        return f"{self.channel_id}:{self.resource_id}:{self.message_number}"


@dataclass(frozen=True)
class CalendarEventChangeBatch:
    events: tuple[dict[str, Any], ...]
    next_sync_token: str


class CalendarEventsClient(Protocol):
    def list_event_changes(
        self,
        *,
        calendar_id: str,
        sync_token: str | None,
    ) -> CalendarEventChangeBatch:
        """Return changed events and next sync token. Implementer owns Google API calls."""


@dataclass(frozen=True)
class WebhookProcessResult:
    status: str
    calendar_id: str | None = None
    envelopes: tuple[dict[str, Any], ...] = ()
    dedupe_key: str | None = None
    reason: str | None = None
    initial_sync_suppressed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "calendar_id": self.calendar_id,
            "envelopes": list(self.envelopes),
            "dedupe_key": self.dedupe_key,
            "reason": self.reason,
            "initial_sync_suppressed": self.initial_sync_suppressed,
        }


class CalendarWebhookProcessor:
    def __init__(
        self,
        *,
        state_store: CalendarWebhookStateStore,
        events_client: CalendarEventsClient,
        privacy: CalendarPrivacyConfig | None = None,
    ) -> None:
        self._state_store = state_store
        self._events_client = events_client
        self._privacy = privacy or CalendarPrivacyConfig()

    def register_channel(
        self,
        *,
        channel_id: str,
        resource_id: str,
        calendar_id: str = "primary",
        expiration_ms: int | None = None,
        sync_token: str | None = None,
    ) -> CalendarChannelState:
        state = self._state_store.load()
        channel = CalendarChannelState(
            channel_id=channel_id,
            resource_id=resource_id,
            calendar_id=calendar_id,
            expiration_ms=expiration_ms,
            sync_token=sync_token,
        )
        state.channels[channel_id] = channel
        self._state_store.save(state)
        return channel

    def process_notification(
        self,
        notification: GoogleCalendarNotification,
    ) -> WebhookProcessResult:
        state = self._state_store.load()
        channel = state.channels.get(notification.channel_id)
        if channel is None:
            return WebhookProcessResult(
                status="ignored",
                dedupe_key=notification.dedupe_key,
                reason="unknown_channel",
            )
        if channel.resource_id != notification.resource_id:
            return WebhookProcessResult(
                status="ignored",
                calendar_id=channel.calendar_id,
                dedupe_key=notification.dedupe_key,
                reason="resource_id_mismatch",
            )
        if state.has_processed(notification.dedupe_key):
            return WebhookProcessResult(
                status="duplicate",
                calendar_id=channel.calendar_id,
                dedupe_key=notification.dedupe_key,
                reason="already_processed",
            )

        previous_sync_token = channel.sync_token
        if notification.resource_state == "sync" and previous_sync_token is not None:
            channel.initial_sync_seen = True
            if notification.channel_expiration:
                channel.channel_expiration = notification.channel_expiration
            state.channels[notification.channel_id] = channel
            state.mark_processed(notification.dedupe_key)
            self._state_store.save(state)
            return WebhookProcessResult(
                status="initial_sync",
                calendar_id=channel.calendar_id,
                dedupe_key=notification.dedupe_key,
                reason="initial_sync_suppressed",
                initial_sync_suppressed=True,
            )

        batch = self._events_client.list_event_changes(
            calendar_id=channel.calendar_id,
            sync_token=previous_sync_token,
        )
        envelopes = ()
        if notification.resource_state != "sync" and previous_sync_token is not None:
            envelopes = tuple(
                build_event_envelope(
                    calendar_id=channel.calendar_id,
                    event=GoogleCalendarEvent.from_api(event_payload),
                    previous_sync_token=previous_sync_token,
                    privacy=self._privacy,
                )
                for event_payload in batch.events
            )

        channel.sync_token = batch.next_sync_token
        if notification.resource_state == "sync" or previous_sync_token is None:
            channel.initial_sync_seen = True
        if notification.channel_expiration:
            channel.channel_expiration = notification.channel_expiration
        state.channels[notification.channel_id] = channel
        state.mark_processed(notification.dedupe_key)
        self._state_store.save(state)

        if notification.resource_state == "sync" or previous_sync_token is None:
            return WebhookProcessResult(
                status="initial_sync",
                calendar_id=channel.calendar_id,
                dedupe_key=notification.dedupe_key,
                reason="initial_sync_suppressed",
                initial_sync_suppressed=True,
            )

        return WebhookProcessResult(
            status="processed",
            calendar_id=channel.calendar_id,
            envelopes=envelopes,
            dedupe_key=notification.dedupe_key,
        )

    def process_headers(self, headers: dict[str, str]) -> WebhookProcessResult:
        """Webhook endpoint entrypoint for raw Google Calendar push headers."""
        return self.process_notification(GoogleCalendarNotification.from_headers(headers))
