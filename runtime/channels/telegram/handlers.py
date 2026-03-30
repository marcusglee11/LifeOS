from __future__ import annotations

import asyncio
import time
from contextlib import suppress
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.channels.telegram.config import TelegramConfig
from runtime.channels.telegram.sessions import clear_session
from runtime.channels.telegram.status import write_status
from runtime.orchestration.coo import service as coo_service
from runtime.orchestration.coo.parser import ParseError


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
        [
            [
                InlineKeyboardButton("Approve", callback_data=f"approve:{proposal_id}"),
                InlineKeyboardButton("Reject", callback_data=f"reject:{proposal_id}"),
            ]
        ]
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


_HELP_TEXT = (
    "Available commands:\n"
    "/status — backlog + dispatch state\n"
    "/propose — trigger COO propose sweep\n"
    "/direct <intent> — direct directive to COO\n"
    "/approve <id> — approve T-... or OP-...\n"
    "/reject <id> [reason] — reject OP-...\n"
    "/prompt_status — canonical vs live prompt hash\n"
    "/new or /reset — clear session state\n"
    "/help — show this message"
)


def _render_status(ctx: dict[str, Any]) -> str:
    by_status = ctx.get("by_status", {})
    dispatch = ctx.get("dispatch", {})
    lines = [
        f"Tasks: {ctx.get('total_tasks', 0)} total, {ctx.get('actionable_count', 0)} actionable",
        f"  pending={by_status.get('pending', 0)} in_progress={by_status.get('in_progress', 0)} "
        f"completed={by_status.get('completed', 0)} blocked={by_status.get('blocked', 0)}",
        f"Dispatch: inbox={dispatch.get('inbox', 0)} active={dispatch.get('active', 0)} "
        f"completed={dispatch.get('completed_total', 0)}",
        f"Escalations pending: {dispatch.get('escalations_pending', 0)}",
    ]
    return "\n".join(lines)


def _render_propose(result: dict[str, Any]) -> str:
    if result["kind"] == "nothing_to_propose":
        payload = result.get("payload") or {}
        reason = str(payload.get("reason", "")).strip()
        follow_up = str(payload.get("recommended_follow_up", "")).strip()
        msg = f"Nothing to propose. {reason}"
        if follow_up:
            msg += f" {follow_up}"
        return msg.strip()

    payload = result.get("payload") or {}
    proposals = payload.get("proposals") or []
    if not proposals:
        return "Propose sweep complete; no proposals in output."
    lines: list[str] = []
    for p in proposals:
        task_id = str(p.get("task_id", "")).strip()
        action = str(p.get("proposed_action", "")).strip()
        rationale = str(p.get("rationale", "")).strip()
        lines.append(f"{task_id} → {action}: {rationale}")
    return "\n".join(lines)


def _render_prompt_status(ps: dict[str, Any]) -> str:
    in_sync = ps.get("in_sync", False)
    canonical_hash = str(ps.get("canonical_sha256") or "missing")[:12]
    live_hash = str(ps.get("live_sha256") or "missing")[:12]
    sync_label = "IN SYNC" if in_sync else "OUT OF SYNC"
    return f"Prompt status: {sync_label}\n  canonical: {canonical_hash}\n  live:      {live_hash}"


async def _dispatch_slash_command(
    text: str,
    update: Any,
    context: Any,  # noqa: ARG001
    *,
    repo_root: Path,
) -> bool:
    """Dispatch slash commands.  Returns True if handled, False if not a slash command."""
    if not text.startswith("/"):
        return False

    message = getattr(update, "effective_message", None)
    chat = getattr(message, "chat", None)
    chat_id = getattr(chat, "id", None)

    parts = text.split(None, 1)
    command = parts[0].lower()
    rest = parts[1].strip() if len(parts) > 1 else ""

    if command in ("/help",):
        await message.reply_text(_HELP_TEXT)
        return True

    if command in ("/new", "/reset"):
        clear_session(repo_root, chat_id)
        await message.reply_text("Session cleared.")
        return True

    if command == "/status":
        ctx = coo_service.get_status_context(repo_root)
        await message.reply_text(_render_status(ctx))
        return True

    if command == "/prompt_status":
        ps = coo_service.get_prompt_status(repo_root)
        await message.reply_text(_render_prompt_status(ps))
        return True

    if command == "/propose":
        try:
            result = await asyncio.to_thread(coo_service.propose_coo, repo_root)
        except Exception as exc:
            await message.reply_text(f"Propose failed: {exc}")
            return True
        await message.reply_text(_render_propose(result))
        return True

    if command == "/direct":
        if not rest:
            await message.reply_text("Usage: /direct <intent>")
            return True
        actor = _actor_label(update, "telegram")
        try:
            result = await asyncio.to_thread(
                coo_service.direct_coo,
                rest,
                repo_root,
                source="telegram_direct",
                actor=actor,
            )
        except Exception as exc:
            await message.reply_text(f"Direct directive failed: {exc}")
            return True
        if result["kind"] == "operation_proposal":
            proposal_id = str(result["payload"].get("proposal_id", ""))
            proposal = result["payload"].get("proposal") or {}
            title = str(proposal.get("title", proposal_id)).strip()
            rationale = str(proposal.get("rationale", "")).strip()
            reply_text = f"Proposed: {title}\n{rationale}".strip()
            await message.reply_text(
                reply_text,
                reply_markup=_build_inline_markup(proposal_id),
            )
        else:
            packet = result.get("payload") or {}
            summary = str((packet.get("context") or {}).get("summary", "")).strip()
            escalation_id = str(packet.get("escalation_id", "")).strip()
            msg = f"Escalated to CEO (id={escalation_id})."
            if summary:
                msg = f"{summary}\n{msg}"
            await message.reply_text(msg)
        return True

    if command == "/approve":
        if not rest:
            await message.reply_text("Usage: /approve <id>")
            return True
        actor = _actor_label(update, "telegram_approve")
        result = await asyncio.to_thread(coo_service.approve_item, rest, repo_root, actor)
        kind = result.get("kind")
        if kind == "task_approval":
            await message.reply_text(
                f"Approved task {result['task_id']} — order {result['order_id']} queued."
            )
        elif kind == "operation_receipt":
            await message.reply_text(_render_terminal_text(result["receipt"]))
        else:
            await message.reply_text(f"Approval failed: {result.get('message', 'unknown error')}")
        return True

    if command == "/reject":
        parts2 = rest.split(None, 1) if rest else []
        if not parts2:
            await message.reply_text("Usage: /reject <id> [reason]")
            return True
        identifier = parts2[0]
        reason = parts2[1].strip() if len(parts2) > 1 else "Rejected from Telegram"
        actor = _actor_label(update, "telegram_reject")
        result = await asyncio.to_thread(
            coo_service.reject_item, identifier, repo_root, actor, reason
        )
        kind = result.get("kind")
        if kind == "operation_receipt":
            await message.reply_text(_render_terminal_text(result["receipt"]))
        else:
            await message.reply_text(f"Rejection failed: {result.get('message', 'unknown error')}")
        return True

    # Unknown slash command
    await message.reply_text(f"Unknown command: {command}\n\n{_HELP_TEXT}")
    return True


async def handle_message(
    update: Any, context: Any, *, repo_root: Path, config: TelegramConfig
) -> None:
    if not _is_private_chat(update) or not _is_allowed(update, config):
        return

    message = getattr(update, "effective_message", None)
    text = str(getattr(message, "text", "") or "").strip()
    if not text:
        return

    _msg_start = time.monotonic()
    write_status(repo_root, last_message_at=_utc_now())

    if await _dispatch_slash_command(text, update, context, repo_root=repo_root):
        return

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


async def handle_callback(
    update: Any, context: Any, *, repo_root: Path, config: TelegramConfig
) -> None:
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
