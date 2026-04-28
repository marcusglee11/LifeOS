from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EventAction = Literal["created", "updated", "cancelled"]


@dataclass(frozen=True)
class CalendarPrivacyConfig:
    include_description: bool = False
    include_attendees: bool = False
    include_attendee_emails: bool = False


@dataclass(frozen=True)
class GoogleCalendarEvent:
    event_id: str
    status: str = "confirmed"
    summary: str | None = None
    html_link: str | None = None
    created: str | None = None
    updated: str | None = None
    start: dict[str, Any] = field(default_factory=dict)
    end: dict[str, Any] = field(default_factory=dict)
    organizer: dict[str, Any] = field(default_factory=dict)
    attendees: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    description: str | None = None

    @classmethod
    def from_api(cls, payload: dict[str, Any]) -> "GoogleCalendarEvent":
        raw_attendees = payload.get("attendees") or []
        attendees = tuple(item for item in raw_attendees if isinstance(item, dict))
        return cls(
            event_id=str(payload.get("id", "")).strip(),
            status=str(payload.get("status", "confirmed")).strip() or "confirmed",
            summary=payload.get("summary") if isinstance(payload.get("summary"), str) else None,
            html_link=payload.get("htmlLink") if isinstance(payload.get("htmlLink"), str) else None,
            created=payload.get("created") if isinstance(payload.get("created"), str) else None,
            updated=payload.get("updated") if isinstance(payload.get("updated"), str) else None,
            start=payload.get("start") if isinstance(payload.get("start"), dict) else {},
            end=payload.get("end") if isinstance(payload.get("end"), dict) else {},
            organizer=(
                payload.get("organizer") if isinstance(payload.get("organizer"), dict) else {}
            ),
            attendees=attendees,
            description=(
                payload.get("description") if isinstance(payload.get("description"), str) else None
            ),
        )


@dataclass(frozen=True)
class CalendarEventEnvelope:
    schema_version: str
    source: str
    calendar_id: str
    event_id: str
    action: EventAction
    time_window: dict[str, Any]
    organizer: dict[str, Any]
    attendees: dict[str, Any] | list[dict[str, Any]]
    link: str | None
    summary: str | None
    description: str | None
    privacy: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema_version": self.schema_version,
            "source": self.source,
            "calendar_id": self.calendar_id,
            "event_id": self.event_id,
            "action": self.action,
            "time_window": self.time_window,
            "organizer": self.organizer,
            "attendees": self.attendees,
            "link": self.link,
            "summary": self.summary,
            "privacy": self.privacy,
        }
        if self.description is not None:
            payload["description"] = self.description
        return payload


def _event_action(event: GoogleCalendarEvent, *, previous_sync_token: str | None) -> EventAction:
    if event.status == "cancelled":
        return "cancelled"
    if not previous_sync_token:
        return "created"
    if event.created and event.updated and event.created == event.updated:
        return "created"
    return "updated"


def _time_window(event: GoogleCalendarEvent) -> dict[str, Any]:
    return {
        "start": event.start.get("dateTime") or event.start.get("date"),
        "end": event.end.get("dateTime") or event.end.get("date"),
        "all_day": bool(event.start.get("date") and not event.start.get("dateTime")),
        "timezone": event.start.get("timeZone") or event.end.get("timeZone"),
    }


def _organizer(event: GoogleCalendarEvent) -> dict[str, Any]:
    return {
        "display_name": event.organizer.get("displayName"),
        "email": event.organizer.get("email"),
        "self": event.organizer.get("self"),
    }


def _attendees(
    attendees: tuple[dict[str, Any], ...], privacy: CalendarPrivacyConfig
) -> dict[str, Any] | list[dict[str, Any]]:
    if not privacy.include_attendees:
        return {"redacted": True, "count": len(attendees)}

    visible = []
    for attendee in attendees:
        item = {
            "display_name": attendee.get("displayName"),
            "response_status": attendee.get("responseStatus"),
            "optional": attendee.get("optional"),
        }
        if privacy.include_attendee_emails:
            item["email"] = attendee.get("email")
        visible.append(item)
    return visible


def build_event_envelope(
    *,
    calendar_id: str,
    event: GoogleCalendarEvent,
    previous_sync_token: str | None,
    privacy: CalendarPrivacyConfig | None = None,
) -> dict[str, Any]:
    if privacy is None:
        privacy = CalendarPrivacyConfig()
    envelope = CalendarEventEnvelope(
        schema_version="lifeos.calendar_event.v0",
        source="google_calendar",
        calendar_id=calendar_id,
        event_id=event.event_id,
        action=_event_action(event, previous_sync_token=previous_sync_token),
        time_window=_time_window(event),
        organizer=_organizer(event),
        attendees=_attendees(event.attendees, privacy),
        link=event.html_link,
        summary=event.summary,
        description=event.description if privacy.include_description else None,
        privacy={
            "description_included": privacy.include_description,
            "attendees_included": privacy.include_attendees,
            "attendee_emails_included": privacy.include_attendee_emails,
        },
    )
    return envelope.to_dict()
