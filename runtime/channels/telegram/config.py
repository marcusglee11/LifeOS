from __future__ import annotations

import os
from dataclasses import dataclass


class TelegramConfigError(ValueError):
    pass


@dataclass(frozen=True)
class TelegramConfig:
    bot_token: str
    allow_from: frozenset[int]
    mode: str


def _parse_allowlist(raw: str) -> frozenset[int]:
    values = [item.strip() for item in raw.split(",") if item.strip()]
    if not values:
        raise TelegramConfigError(
            "LIFEOS_COO_TELEGRAM_ALLOW_FROM must contain at least one Telegram user ID"
        )

    allow_from: set[int] = set()
    for value in values:
        try:
            allow_from.add(int(value))
        except ValueError as exc:
            raise TelegramConfigError(
                f"LIFEOS_COO_TELEGRAM_ALLOW_FROM contains a non-integer user ID: {value!r}"
            ) from exc
    return frozenset(allow_from)


def load_config() -> TelegramConfig:
    token = os.environ.get("LIFEOS_COO_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise TelegramConfigError("LIFEOS_COO_TELEGRAM_BOT_TOKEN is required")

    allow_from = _parse_allowlist(
        os.environ.get("LIFEOS_COO_TELEGRAM_ALLOW_FROM", "")
    )

    mode = os.environ.get("LIFEOS_COO_TELEGRAM_MODE", "polling").strip().lower()
    if mode != "polling":
        raise TelegramConfigError(
            "LIFEOS_COO_TELEGRAM_MODE must be exactly 'polling'"
        )

    return TelegramConfig(
        bot_token=token,
        allow_from=allow_from,
        mode=mode,
    )
