from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from runtime.channels.telegram import adapter
from runtime.channels.telegram.config import TelegramConfig


class _FakeApplication:
    def __init__(self, events: list[object]) -> None:
        self.events = events
        self.handlers: list[object] = []

    def add_handler(self, handler: object) -> None:
        self.handlers.append(handler)

    def run_polling(self) -> None:
        self.events.append(("run_polling", None))


class _FakeBuilder:
    def __init__(self, application: _FakeApplication) -> None:
        self.application = application
        self.tokens: list[str] = []

    def token(self, token: str) -> _FakeBuilder:
        self.tokens.append(token)
        return self

    def build(self) -> _FakeApplication:
        return self.application


def _install_fake_telegram(
    monkeypatch: pytest.MonkeyPatch,
    application: _FakeApplication,
) -> _FakeBuilder:
    builder = _FakeBuilder(application)
    fake_ext = types.ModuleType("telegram.ext")
    fake_ext.ApplicationBuilder = lambda: builder
    fake_ext.CallbackQueryHandler = (
        lambda callback, pattern=None: ("callback", pattern, callback)
    )
    fake_ext.MessageHandler = lambda filter_value, callback: (
        "message",
        filter_value,
        callback,
    )
    fake_ext.filters = types.SimpleNamespace(ALL="ALL")

    fake_telegram = types.ModuleType("telegram")
    fake_telegram.ext = fake_ext

    monkeypatch.setitem(sys.modules, "telegram", fake_telegram)
    monkeypatch.setitem(sys.modules, "telegram.ext", fake_ext)
    return builder


def test_run_polling_bootstraps_event_loop_when_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[object] = []
    application = _FakeApplication(events)
    builder = _install_fake_telegram(monkeypatch, application)
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    new_loop = object()

    def _raise_no_loop() -> None:
        raise RuntimeError("There is no current event loop in thread 'MainThread'.")

    monkeypatch.setattr(adapter.asyncio, "get_event_loop", _raise_no_loop)
    monkeypatch.setattr(adapter.asyncio, "new_event_loop", lambda: new_loop)
    monkeypatch.setattr(
        adapter.asyncio,
        "set_event_loop",
        lambda loop: events.append(("set_event_loop", loop)),
    )

    adapter.run_polling(config, tmp_path)

    assert builder.tokens == ["token"]
    assert application.handlers[0][0:2] == ("message", "ALL")
    assert application.handlers[1][0:2] == ("callback", r"^(approve|reject):")
    assert events == [("set_event_loop", new_loop), ("run_polling", None)]


def test_run_polling_reuses_existing_event_loop(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    events: list[object] = []
    application = _FakeApplication(events)
    _install_fake_telegram(monkeypatch, application)
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")

    monkeypatch.setattr(adapter.asyncio, "get_event_loop", lambda: object())
    monkeypatch.setattr(
        adapter.asyncio,
        "new_event_loop",
        lambda: pytest.fail("new_event_loop should not be called when a loop exists"),
    )
    monkeypatch.setattr(
        adapter.asyncio,
        "set_event_loop",
        lambda loop: events.append(("set_event_loop", loop)),
    )

    adapter.run_polling(config, tmp_path)

    assert events == [("run_polling", None)]
