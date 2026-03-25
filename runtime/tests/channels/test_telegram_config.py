from __future__ import annotations

import pytest

from runtime.channels.telegram.config import TelegramConfigError, load_config


def test_load_config_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIFEOS_COO_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("LIFEOS_COO_TELEGRAM_ALLOW_FROM", "123,456")
    monkeypatch.setenv("LIFEOS_COO_TELEGRAM_MODE", "polling")

    config = load_config()

    assert config.bot_token == "token"
    assert config.allow_from == frozenset({123, 456})
    assert config.mode == "polling"


def test_load_config_rejects_empty_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIFEOS_COO_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.delenv("LIFEOS_COO_TELEGRAM_ALLOW_FROM", raising=False)

    with pytest.raises(TelegramConfigError, match="ALLOW_FROM"):
        load_config()


def test_load_config_rejects_non_polling_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LIFEOS_COO_TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("LIFEOS_COO_TELEGRAM_ALLOW_FROM", "123")
    monkeypatch.setenv("LIFEOS_COO_TELEGRAM_MODE", "webhook")

    with pytest.raises(TelegramConfigError, match="polling"):
        load_config()
