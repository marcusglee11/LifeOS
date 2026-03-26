from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from runtime.channels.telegram.config import TelegramConfig
from runtime.channels.telegram.handlers import handle_callback, handle_message
from runtime.channels.telegram.status import write_status


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_event_loop() -> None:
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())


def run_polling(config: TelegramConfig, repo_root: Path) -> None:
    from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters

    write_status(repo_root, state="starting", mode=config.mode, started_at=_utc_now())

    application = ApplicationBuilder().token(config.bot_token).build()

    async def _message_handler(update, context) -> None:
        await handle_message(update, context, repo_root=repo_root, config=config)

    async def _callback_handler(update, context) -> None:
        await handle_callback(update, context, repo_root=repo_root, config=config)

    application.add_handler(
        MessageHandler(filters.ALL, _message_handler)
    )
    application.add_handler(
        CallbackQueryHandler(_callback_handler, pattern=r"^(approve|reject):")
    )
    _ensure_event_loop()
    write_status(repo_root, state="running")
    try:
        application.run_polling()
    except Exception as exc:
        write_status(repo_root, state="error", last_error=str(exc))
        raise
    write_status(repo_root, state="stopped")
