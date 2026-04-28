from __future__ import annotations

from pathlib import Path
from typing import Any

from runtime.channels.google_calendar import (
    CalendarEventChangeBatch,
    CalendarPrivacyConfig,
    CalendarWebhookProcessor,
    CalendarWebhookStateStore,
    GoogleCalendarNotification,
    for_hermes,
    for_openclaw,
)
from runtime.channels.google_calendar.state import CalendarChannelState, CalendarWebhookState


class FakeCalendarClient:
    def __init__(self, batches: list[CalendarEventChangeBatch]) -> None:
        self.batches = batches
        self.calls: list[dict[str, Any]] = []

    def list_event_changes(
        self,
        *,
        calendar_id: str,
        sync_token: str | None,
    ) -> CalendarEventChangeBatch:
        self.calls.append({"calendar_id": calendar_id, "sync_token": sync_token})
        return self.batches.pop(0)


def _store(tmp_path: Path) -> CalendarWebhookStateStore:
    return CalendarWebhookStateStore(tmp_path / "calendar_state.json")


def _notification(
    message_number: int = 1,
    resource_state: str = "exists",
) -> GoogleCalendarNotification:
    return GoogleCalendarNotification(
        channel_id="chan-1",
        resource_id="res-1",
        resource_state=resource_state,
        message_number=message_number,
    )


def test_state_persists_channels_tokens_and_dedupe(tmp_path: Path) -> None:
    store = _store(tmp_path)
    state = CalendarWebhookState()
    state.channels["chan-1"] = CalendarChannelState(
        channel_id="chan-1",
        resource_id="res-1",
        calendar_id="primary",
        sync_token="sync-a",
        expiration_ms=123456,
    )
    state.mark_processed("chan-1:res-1:1")

    store.save(state)
    loaded = store.load()

    assert loaded.channels["chan-1"].sync_token == "sync-a"
    assert loaded.channels["chan-1"].expiration_ms == 123456
    assert loaded.has_processed("chan-1:res-1:1")
    assert ".config/lifeos-google" in store.path.read_text(encoding="utf-8")


def test_processor_dedupes_notifications_and_updates_sync_token(tmp_path: Path) -> None:
    store = _store(tmp_path)
    processor = CalendarWebhookProcessor(
        state_store=store,
        events_client=FakeCalendarClient(
            [
                CalendarEventChangeBatch(
                    events=(
                        {
                            "id": "evt-1",
                            "summary": "Review",
                            "created": "2026-04-28T00:00:00Z",
                            "updated": "2026-04-28T01:00:00Z",
                        },
                    ),
                    next_sync_token="sync-b",
                )
            ]
        ),
    )
    processor.register_channel(
        channel_id="chan-1",
        resource_id="res-1",
        sync_token="sync-a",
    )

    first = processor.process_notification(_notification())
    second = processor.process_notification(_notification())

    assert first.status == "processed"
    assert len(first.envelopes) == 1
    assert second.status == "duplicate"
    assert store.load().channels["chan-1"].sync_token == "sync-b"


def test_initial_sync_noise_suppressed_but_sync_token_persisted(tmp_path: Path) -> None:
    client = FakeCalendarClient(
        [CalendarEventChangeBatch(events=({"id": "evt-ignored"},), next_sync_token="sync-initial")]
    )
    store = _store(tmp_path)
    processor = CalendarWebhookProcessor(state_store=store, events_client=client)
    processor.register_channel(channel_id="chan-1", resource_id="res-1")

    result = processor.process_notification(_notification(resource_state="sync"))

    assert result.status == "initial_sync"
    assert result.initial_sync_suppressed is True
    assert result.envelopes == ()
    assert store.load().channels["chan-1"].sync_token == "sync-initial"
    assert store.load().channels["chan-1"].initial_sync_seen is True
    assert client.calls == [{"calendar_id": "primary", "sync_token": None}]


def test_sync_notification_with_existing_token_does_not_fetch_or_drop_changes(
    tmp_path: Path,
) -> None:
    client = FakeCalendarClient([])
    store = _store(tmp_path)
    processor = CalendarWebhookProcessor(state_store=store, events_client=client)
    processor.register_channel(channel_id="chan-1", resource_id="res-1", sync_token="sync-a")

    result = processor.process_notification(_notification(resource_state="sync"))

    assert result.status == "initial_sync"
    assert result.initial_sync_suppressed is True
    assert client.calls == []
    loaded_channel = store.load().channels["chan-1"]
    assert loaded_channel.sync_token == "sync-a"
    assert loaded_channel.initial_sync_seen is True


def test_invalid_event_does_not_advance_sync_token_or_dedupe(tmp_path: Path) -> None:
    store = _store(tmp_path)
    processor = CalendarWebhookProcessor(
        state_store=store,
        events_client=FakeCalendarClient(
            [
                CalendarEventChangeBatch(
                    events=({"summary": "missing id"},), next_sync_token="sync-b"
                )
            ]
        ),
    )
    processor.register_channel(channel_id="chan-1", resource_id="res-1", sync_token="sync-a")

    try:
        processor.process_notification(_notification())
    except ValueError as exc:
        assert str(exc) == "google_calendar_event_missing_id"
    else:
        raise AssertionError("expected missing event id to fail")

    loaded_state = store.load()
    assert loaded_state.channels["chan-1"].sync_token == "sync-a"
    assert not loaded_state.has_processed("chan-1:res-1:1")


def test_envelope_privacy_minimizes_attendees_and_description(tmp_path: Path) -> None:
    processor = CalendarWebhookProcessor(
        state_store=_store(tmp_path),
        events_client=FakeCalendarClient(
            [
                CalendarEventChangeBatch(
                    events=(
                        {
                            "id": "evt-2",
                            "summary": "Private meeting",
                            "description": "sensitive notes",
                            "htmlLink": "https://calendar.google.com/event?eid=evt-2",
                            "created": "2026-04-27T00:00:00Z",
                            "updated": "2026-04-28T00:00:00Z",
                            "start": {"dateTime": "2026-04-28T09:00:00+10:00"},
                            "end": {"dateTime": "2026-04-28T09:30:00+10:00"},
                            "organizer": {"email": "owner@example.com"},
                            "attendees": [
                                {"email": "a@example.com", "responseStatus": "accepted"},
                                {"email": "b@example.com", "responseStatus": "needsAction"},
                            ],
                        },
                    ),
                    next_sync_token="sync-next",
                )
            ]
        ),
    )
    processor.register_channel(channel_id="chan-1", resource_id="res-1", sync_token="sync-a")

    envelope = processor.process_notification(_notification()).envelopes[0]

    assert envelope["action"] == "updated"
    assert envelope["attendees"] == {"redacted": True, "count": 2}
    assert "description" not in envelope
    assert envelope["privacy"] == {
        "description_included": False,
        "attendees_included": False,
        "attendee_emails_included": False,
    }


def test_privacy_can_include_attendees_without_emails(tmp_path: Path) -> None:
    processor = CalendarWebhookProcessor(
        state_store=_store(tmp_path),
        events_client=FakeCalendarClient(
            [
                CalendarEventChangeBatch(
                    events=(
                        {
                            "id": "evt-3",
                            "attendees": [{"email": "a@example.com", "displayName": "Alex"}],
                        },
                    ),
                    next_sync_token="sync-next",
                )
            ]
        ),
        privacy=CalendarPrivacyConfig(include_attendees=True),
    )
    processor.register_channel(channel_id="chan-1", resource_id="res-1", sync_token="sync-a")

    envelope = processor.process_notification(_notification()).envelopes[0]

    assert envelope["attendees"] == [
        {"display_name": "Alex", "response_status": None, "optional": None}
    ]


def test_channel_renewal_and_expiry_detection(tmp_path: Path) -> None:
    state = CalendarWebhookState()
    state.channels["soon"] = CalendarChannelState(
        channel_id="soon",
        resource_id="res-soon",
        expiration_ms=1_100,
    )
    state.channels["later"] = CalendarChannelState(
        channel_id="later",
        resource_id="res-later",
        expiration_ms=10_000,
    )

    assert state.channels_due_for_renewal(now_ms=1_000, lead_ms=200) == ["soon"]
    assert state.expired_channels(now_ms=1_101) == ["soon"]


def test_shared_envelope_has_thin_hermes_and_openclaw_adapters() -> None:
    envelope = {"schema_version": "lifeos.calendar_event.v0", "event_id": "evt-1"}

    assert for_openclaw(envelope)["envelope"] == envelope
    assert for_hermes(envelope)["envelope"] == envelope


def test_processor_accepts_raw_google_webhook_headers(tmp_path: Path) -> None:
    processor = CalendarWebhookProcessor(
        state_store=_store(tmp_path),
        events_client=FakeCalendarClient(
            [CalendarEventChangeBatch(events=({"id": "evt-4"},), next_sync_token="sync-next")]
        ),
    )
    processor.register_channel(channel_id="chan-1", resource_id="res-1", sync_token="sync-a")

    result = processor.process_headers(
        {
            "X-Goog-Channel-ID": "chan-1",
            "X-Goog-Resource-ID": "res-1",
            "X-Goog-Resource-State": "exists",
            "X-Goog-Message-Number": "4",
        }
    )

    assert result.status == "processed"
    assert result.dedupe_key == "chan-1:res-1:4"


def test_processor_rejects_incomplete_raw_google_webhook_headers(tmp_path: Path) -> None:
    processor = CalendarWebhookProcessor(
        state_store=_store(tmp_path),
        events_client=FakeCalendarClient([]),
    )

    try:
        processor.process_headers({"X-Goog-Channel-ID": "chan-1"})
    except ValueError as exc:
        assert str(exc) == (
            "missing_google_calendar_headers:"
            "x-goog-resource-id,x-goog-resource-state,x-goog-message-number"
        )
    else:
        raise AssertionError("expected missing headers to fail")
