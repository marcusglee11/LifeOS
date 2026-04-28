"""Shared Google Calendar webhook surface for LifeOS agents."""

from runtime.channels.google_calendar.adapters import for_hermes, for_openclaw
from runtime.channels.google_calendar.envelope import (
    CalendarEventEnvelope,
    CalendarPrivacyConfig,
    GoogleCalendarEvent,
    build_event_envelope,
)
from runtime.channels.google_calendar.processor import (
    CalendarEventChangeBatch,
    CalendarEventsClient,
    CalendarWebhookProcessor,
    GoogleCalendarNotification,
    WebhookProcessResult,
)
from runtime.channels.google_calendar.state import CalendarChannelState, CalendarWebhookStateStore

__all__ = [
    "CalendarChannelState",
    "CalendarEventChangeBatch",
    "CalendarEventEnvelope",
    "CalendarEventsClient",
    "CalendarPrivacyConfig",
    "CalendarWebhookProcessor",
    "CalendarWebhookStateStore",
    "GoogleCalendarEvent",
    "GoogleCalendarNotification",
    "WebhookProcessResult",
    "build_event_envelope",
    "for_hermes",
    "for_openclaw",
]
