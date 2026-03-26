from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.channels.telegram.config import TelegramConfig
from runtime.channels.telegram.status import write_status
from runtime.orchestration.coo.parser import ParseError
from runtime.orchestration.coo import service as coo_service


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_private_chat(update: Any) -> bool:
    chat = getattr(getattr(update, "effective_message", None), "chat", None)
    return bool(chat is not None and getattr(chat, "type", "") == "private")


def _user_id(update: Any) -> int | None:
    user = getattr(update, "effective_user", None)
    raw = getattr(user, "id", None)
    return raw if isinstance(raw, int) else None


def _is_allowed(update: Any, config: TelegramConfig) -> bool:
    user_id = _user_id(update)
    return bool(user_id is not None and user_id in config.allow_from)


def _actor_label(update: Any, prefix: str) -> str:
    user_id = _user_id(update)
    return f"{prefix}:{user_id}" if user_id is not None else prefix


def _build_inline_markup(proposal_id: str) -> Any:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("Approve", callback_data=f"approve:{proposal_id}"),
            InlineKeyboardButton("Reject", callback_data=f"reject:{proposal_id}"),
        ]]
    )


def _render_terminal_text(receipt: dict[str, Any]) -> str:
    proposal_id = str(receipt.get("proposal_id", "")).strip()
    order_id = receipt.get("order_id")
    status = str(receipt.get("status", "")).strip() or "unknown"
    reason = str(receipt.get("reason", "") or "").strip()
    error = str(receipt.get("error", "") or "").strip()

    if status == "executed":
        return f"Approved {proposal_id} and executed {order_id}."
    if status == "rejected":
        suffix = f" Reason: {reason}" if reason else ""
        return f"Rejected {proposal_id}.{suffix}".strip()
    if error:
        return f"{proposal_id} failed: {error}"
    return f"{proposal_id} status: {status}"


async def _send_typing_action(update: Any, context: Any) -> bool:
    bot = getattr(context, "bot", None)
    chat = getattr(getattr(update, "effective_message", None), "chat", None)
    chat_id = getattr(chat, "id", None)
    if bot is None or not isinstance(chat_id, int):
        return False

    try:
        from telegram.constants import ChatAction
        action = ChatAction.TYPING
    except ModuleNotFoundError:
        action = "typing"

    await bot.send_chat_action(chat_id=chat_id, action=action)
    return True


async def _typing_pulse(update: Any, context: Any, interval_s: float = 4.0) -> None:
    if not await _send_typing_action(update, context):
        return

    while True:
        await asyncio.sleep(interval_s)
        await _send_typing_action(update, context)


async def handle_message(update: Any, context: Any, *, repo_root: Path, config: TelegramConfig) -> None:
    if not _is_private_chat(update) or not _is_allowed(update, config):
        return

    message = getattr(update, "effective_message", None)
    text = str(getattr(message, "text", "") or "").strip()
    if not text:
        return

    _msg_start = time.monotonic()
    write_status(repo_root, last_message_at=_utc_now())

    typing_task = asyncio.create_task(_typing_pulse(update, context))
    await asyncio.sleep(0)
    try:
        result = await asyncio.to_thread(coo_service.chat_message, text, repo_root)
    except ParseError as exc:
        await message.reply_text(
            f"COO returned an invalid operation packet and nothing was queued: {exc}"
        )
        write_status(repo_root, last_error=f"parse error: {exc}")
        return
    except Exception as exc:
        await message.reply_text(f"COO chat failed: {exc}")
        write_status(repo_root, last_error=str(exc))
        return
    finally:
        typing_task.cancel()
        with suppress(asyncio.CancelledError):
            await typing_task
    reply_text = str(result.get("message", "")).strip() or "Queued."
    if result.get("has_proposal"):
        await message.reply_text(
            reply_text,
            reply_markup=_build_inline_markup(str(result["proposal_id"])),
        )
        write_status(
            repo_root,
            last_reply_at=_utc_now(),
            last_latency_ms=int((time.monotonic() - _msg_start) * 1000),
        )
        return

    await message.reply_text(reply_text)
    write_status(
        repo_root,
        last_reply_at=_utc_now(),
        last_latency_ms=int((time.monotonic() - _msg_start) * 1000),
    )


async def handle_callback(update: Any, context: Any, *, repo_root: Path, config: TelegramConfig) -> None:
    del context
    if not _is_private_chat(update) or not _is_allowed(update, config):
        return

    query = getattr(update, "callback_query", None)
    if query is None:
        return

    data = str(getattr(query, "data", "") or "").strip()
    if not data:
        return

    action, _, proposal_id = data.partition(":")
    if action == "approve" and proposal_id:
        receipt = await asyncio.to_thread(
            coo_service.approve_operation,
            proposal_id,
            repo_root,
            _actor_label(update, "telegram_approve"),
        )
    elif action == "reject" and proposal_id:
        receipt = await asyncio.to_thread(
            coo_service.reject_operation,
            proposal_id,
            repo_root,
            _actor_label(update, "telegram_reject"),
            "Rejected from Telegram",
        )
    else:
        return

    await query.answer()
    await query.edit_message_text(_render_terminal_text(receipt))
    write_status(repo_root, last_callback_at=_utc_now())
