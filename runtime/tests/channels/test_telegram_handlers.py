from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from runtime.channels.telegram.config import TelegramConfig
from runtime.channels.telegram import handlers
from runtime.orchestration.coo.parser import ParseError


@dataclass
class _FakeChat:
    type: str = "private"


@dataclass
class _FakeMessage:
    text: str = ""
    chat: _FakeChat = field(default_factory=_FakeChat)
    replies: list[tuple[str, object | None]] = field(default_factory=list)

    async def reply_text(self, text: str, reply_markup: object | None = None) -> None:
        self.replies.append((text, reply_markup))


@dataclass
class _FakeQuery:
    data: str
    answered: bool = False
    edited_messages: list[str] = field(default_factory=list)

    async def answer(self) -> None:
        self.answered = True

    async def edit_message_text(self, text: str) -> None:
        self.edited_messages.append(text)


@dataclass
class _FakeUser:
    id: int


@dataclass
class _FakeUpdate:
    effective_message: _FakeMessage
    effective_user: _FakeUser
    callback_query: _FakeQuery | None = None


async def _direct_to_thread(func, *args, **kwargs):
    return func(*args, **kwargs)


@pytest.mark.asyncio
async def test_handle_message_replies_with_buttons(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="write a note")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "chat_message",
        lambda text, repo_root: {
            "mode": "chat",
            "has_proposal": True,
            "proposal_id": "OP-a1b2c3d4",
            "status": "pending",
            "message": "Queued for approval.",
        },
    )
    monkeypatch.setattr(
        handlers,
        "_build_inline_markup",
        lambda proposal_id: {"proposal_id": proposal_id},
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert message.replies == [("Queued for approval.", {"proposal_id": "OP-a1b2c3d4"})]


@pytest.mark.asyncio
async def test_handle_message_ignores_unauthorized_user(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({999}), mode="polling")
    message = _FakeMessage(text="write a note")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert message.replies == []


@pytest.mark.asyncio
async def test_handle_message_replies_on_parse_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="write a note")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "chat_message",
        lambda text, repo_root: (_ for _ in ()).throw(
            ParseError("Operation proposal has invalid proposal_id format")
        ),
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert message.replies == [
        (
            "COO returned an invalid operation packet and nothing was queued: "
            "Operation proposal has invalid proposal_id format",
            None,
        )
    ]


@pytest.mark.asyncio
async def test_handle_callback_approve_edits_message(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="write a note")
    query = _FakeQuery(data="approve:OP-a1b2c3d4")
    update = _FakeUpdate(
        effective_message=message,
        effective_user=_FakeUser(id=123),
        callback_query=query,
    )

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "approve_operation",
        lambda proposal_id, repo_root, approved_by: {
            "proposal_id": proposal_id,
            "order_id": "OPR-a1b2c3d4",
            "status": "executed",
            "reason": None,
            "error": None,
        },
    )

    await handlers.handle_callback(update, None, repo_root=tmp_path, config=config)

    assert query.answered is True
    assert query.edited_messages == ["Approved OP-a1b2c3d4 and executed OPR-a1b2c3d4."]
