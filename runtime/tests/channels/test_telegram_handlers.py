from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

import pytest

from runtime.channels.telegram import handlers
from runtime.channels.telegram.config import TelegramConfig
from runtime.orchestration.coo.parser import ParseError


@dataclass
class _FakeChat:
    type: str = "private"
    id: int = 1


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
async def test_handle_message_replies_with_buttons(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="write a note")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "chat_message",
        lambda text, repo_root, **_: {
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
async def test_handle_message_starts_and_cancels_typing_pulse(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="write a note")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))
    events: list[str] = []

    async def _fake_typing_pulse(update_arg, context_arg, interval_s: float = 4.0) -> None:
        assert update_arg is update
        assert interval_s == 4.0
        events.append("typing")
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            events.append("cancelled")
            raise

    monkeypatch.setattr(handlers, "_typing_pulse", _fake_typing_pulse)
    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "chat_message",
        lambda text, repo_root, **_: {
            "mode": "chat",
            "has_proposal": False,
            "proposal_id": None,
            "status": "conversation_only",
            "message": "All set.",
        },
    )

    await handlers.handle_message(
        update,
        SimpleNamespace(bot=object()),
        repo_root=tmp_path,
        config=config,
    )

    assert events == ["typing", "cancelled"]
    assert message.replies == [("All set.", None)]


@pytest.mark.asyncio
async def test_send_typing_action_uses_bot_chat_action() -> None:
    calls: list[tuple[int, str]] = []

    class _FakeBot:
        async def send_chat_action(self, *, chat_id: int, action: str) -> None:
            calls.append((chat_id, action))

    update = _FakeUpdate(
        effective_message=_FakeMessage(text="hello"),
        effective_user=_FakeUser(id=123),
    )

    sent = await handlers._send_typing_action(update, SimpleNamespace(bot=_FakeBot()))

    assert sent is True
    assert calls == [(1, "typing")]


@pytest.mark.asyncio
async def test_handle_message_ignores_unauthorized_user(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({999}), mode="polling")
    message = _FakeMessage(text="write a note")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert message.replies == []


@pytest.mark.asyncio
async def test_handle_message_replies_on_parse_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="write a note")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "chat_message",
        lambda text, repo_root, **_: (_ for _ in ()).throw(
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
async def test_handle_callback_approve_edits_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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


@pytest.mark.asyncio
async def test_handle_message_writes_activity_status(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """handle_message writes last_message_at, last_reply_at, last_latency_ms."""
    import json as _json

    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="write a note")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "chat_message",
        lambda text, repo_root, **_: {
            "mode": "chat",
            "has_proposal": False,
            "proposal_id": None,
            "status": "conversation_only",
            "message": "Done.",
        },
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    status_path = tmp_path / "artifacts" / "status" / "coo_telegram_runtime.json"
    assert status_path.exists()
    data = _json.loads(status_path.read_text())
    assert "last_message_at" in data
    assert "last_reply_at" in data
    assert "last_latency_ms" in data
    assert isinstance(data["last_latency_ms"], int)


@pytest.mark.asyncio
async def test_handle_callback_writes_last_callback_at(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """handle_callback writes last_callback_at after processing."""
    import json as _json

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

    status_path = tmp_path / "artifacts" / "status" / "coo_telegram_runtime.json"
    assert status_path.exists()
    data = _json.loads(status_path.read_text())
    assert "last_callback_at" in data


@pytest.mark.asyncio
async def test_handle_message_writes_last_error_on_exception(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """handle_message writes last_error to status when COO invocation fails."""
    import json as _json

    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="do something")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "chat_message",
        lambda text, repo_root, **_: (_ for _ in ()).throw(RuntimeError("gateway down")),
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert "COO is unavailable" in message.replies[0][0]
    assert "gateway down" in message.replies[0][0]
    status_path = tmp_path / "artifacts" / "status" / "coo_telegram_runtime.json"
    assert status_path.exists()
    data = _json.loads(status_path.read_text())
    assert data.get("last_error") == "gateway down"


# ---------------------------------------------------------------------------
# Slash command tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slash_help_replies_without_coo_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """/help replies immediately; chat_message is never called."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/help")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))
    coo_called = []

    monkeypatch.setattr(handlers.coo_service, "chat_message", lambda *a, **k: coo_called.append(1))

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    assert "/status" in message.replies[0][0]
    assert coo_called == []


@pytest.mark.asyncio
async def test_slash_unknown_replies_with_help(tmp_path: Path) -> None:
    """/unknown replies with help text (not an error crash)."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/unknowncmd")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    assert "Unknown command" in message.replies[0][0]
    assert "/status" in message.replies[0][0]


@pytest.mark.asyncio
async def test_slash_new_clears_session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """/new calls clear_session and sends acknowledgement."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/new")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))
    cleared = []

    monkeypatch.setattr(handlers, "clear_session", lambda r, c: cleared.append(c))

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert cleared == [1]  # chat_id=1 from _FakeChat default
    assert "cleared" in message.replies[0][0].lower()


@pytest.mark.asyncio
async def test_slash_reset_clears_session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """/reset also clears session."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/reset")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))
    cleared = []

    monkeypatch.setattr(handlers, "clear_session", lambda r, c: cleared.append(c))

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(cleared) == 1


@pytest.mark.asyncio
async def test_slash_status_replies_without_typing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """/status replies immediately without starting typing task."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/status")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))
    typing_started = []

    async def _no_typing(*args, **kwargs):
        typing_started.append(True)
        await asyncio.Future()

    monkeypatch.setattr(handlers, "_typing_pulse", _no_typing)
    monkeypatch.setattr(
        handlers.coo_service,
        "get_status_context",
        lambda r: {
            "total_tasks": 3,
            "actionable_count": 1,
            "by_status": {"pending": 2, "in_progress": 1, "completed": 0, "blocked": 0},
            "by_priority": {"P0": 1, "P1": 0, "P2": 0, "P3": 0},
            "dispatch": {
                "inbox": 0,
                "active": 0,
                "completed_total": 0,
                "escalations_pending": 0,
            },
            "generated_at": "2026-01-01T00:00:00+00:00",
        },
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    assert "Tasks: 3" in message.replies[0][0]
    assert typing_started == []  # typing task was NOT started for /status


@pytest.mark.asyncio
async def test_slash_propose_returns_summary_no_buttons(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """/propose sends summary text with no inline buttons."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/propose")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "propose_coo",
        lambda r: {
            "kind": "task_proposal",
            "payload": {
                "proposals": [
                    {
                        "task_id": "T-001",
                        "proposed_action": "dispatch",
                        "rationale": "Top priority.",
                    },
                ]
            },
            "raw_output": "",
            "run_id": "test",
            "parse_recovery_stage": "direct",
            "claim_violations": [],
        },
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    reply_text, markup = message.replies[0]
    assert "T-001" in reply_text
    assert "dispatch" in reply_text
    assert markup is None  # no inline keyboard


@pytest.mark.asyncio
async def test_slash_propose_ntp_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """/propose NTP path returns compact text."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/propose")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "propose_coo",
        lambda r: {
            "kind": "nothing_to_propose",
            "payload": {"reason": "All tasks blocked.", "recommended_follow_up": "Wait."},
            "raw_output": "",
            "run_id": "test",
            "parse_recovery_stage": "direct",
            "claim_violations": [],
        },
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    assert "Nothing to propose" in message.replies[0][0]
    assert "All tasks blocked" in message.replies[0][0]


@pytest.mark.asyncio
async def test_slash_direct_op_proposal_shows_buttons(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """/direct <intent> with op-proposal result shows inline buttons."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/direct write a workspace note")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))
    captured_source = []

    def _fake_direct(intent, repo_root, *, source, actor, agent="main"):
        captured_source.append(source)
        return {
            "kind": "operation_proposal",
            "payload": {
                "proposal_id": "OP-a1b2c3d4",
                "proposal": {
                    "title": "Write note",
                    "rationale": "User asked.",
                    "requires_approval": True,
                },
            },
            "raw_output": "",
            "run_id": "test",
            "parse_recovery_stage": "direct",
            "claim_violations": [],
        }

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(handlers.coo_service, "direct_coo", _fake_direct)
    monkeypatch.setattr(
        handlers, "_build_inline_markup", lambda proposal_id: {"proposal_id": proposal_id}
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert captured_source == ["telegram_direct"]
    assert len(message.replies) == 1
    reply_text, markup = message.replies[0]
    assert "Write note" in reply_text
    assert markup == {"proposal_id": "OP-a1b2c3d4"}


@pytest.mark.asyncio
async def test_slash_direct_escalation_no_buttons(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """/direct escalation path sends text summary, no inline buttons."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/direct touch protected path")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    def _fake_direct(intent, repo_root, *, source, actor, agent="main"):
        return {
            "kind": "escalation_packet",
            "payload": {
                "escalation_id": "ESC-001",
                "context": {"summary": "Protected path touch."},
            },
            "raw_output": "",
            "run_id": "test",
            "parse_recovery_stage": "direct",
            "claim_violations": [],
        }

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(handlers.coo_service, "direct_coo", _fake_direct)

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    reply_text, markup = message.replies[0]
    assert "ESC-001" in reply_text
    assert markup is None


@pytest.mark.asyncio
async def test_slash_approve_task_routes_to_task_approval(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """/approve T-... returns task_approval reply."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/approve T-001")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "approve_item",
        lambda identifier, repo_root, actor: {
            "kind": "task_approval",
            "task_id": "T-001",
            "order_id": "ORD-T-001-20260101000000",
        },
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    assert "T-001" in message.replies[0][0]
    assert "ORD-T-001-20260101000000" in message.replies[0][0]


@pytest.mark.asyncio
async def test_slash_approve_op_routes_to_operation_receipt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """/approve OP-... returns operation receipt reply."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/approve OP-a1b2c3d4")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "approve_item",
        lambda identifier, repo_root, actor: {
            "kind": "operation_receipt",
            "receipt": {
                "proposal_id": "OP-a1b2c3d4",
                "order_id": "OPR-abc",
                "status": "executed",
                "reason": None,
                "error": None,
            },
        },
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    assert "OP-a1b2c3d4" in message.replies[0][0]
    assert "executed" in message.replies[0][0] or "OPR-abc" in message.replies[0][0]


@pytest.mark.asyncio
async def test_slash_approve_actor_label_includes_user_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """/approve produces actor label telegram_approve:<user_id>."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({42}), mode="polling")
    message = _FakeMessage(text="/approve OP-a1b2c3d4")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=42))
    captured_actor = []

    def _fake_approve(identifier, repo_root, actor):
        captured_actor.append(actor)
        return {
            "kind": "operation_receipt",
            "receipt": {
                "proposal_id": "OP-a1b2c3d4",
                "order_id": "OPR-abc",
                "status": "executed",
                "reason": None,
                "error": None,
            },
        }

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(handlers.coo_service, "approve_item", _fake_approve)

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert captured_actor == ["telegram_approve:42"]


@pytest.mark.asyncio
async def test_slash_reject_op_success(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """/reject OP-... sends rejection receipt reply."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/reject OP-a1b2c3d4 not needed")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "reject_item",
        lambda identifier, repo_root, actor, reason: {
            "kind": "operation_receipt",
            "receipt": {
                "proposal_id": "OP-a1b2c3d4",
                "order_id": None,
                "status": "rejected",
                "reason": reason,
                "error": None,
            },
        },
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    assert "OP-a1b2c3d4" in message.replies[0][0]
    assert "rejected" in message.replies[0][0].lower()


@pytest.mark.asyncio
async def test_slash_reject_task_returns_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """/reject T-... returns validation error reply."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/reject T-001 wrong type")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "reject_item",
        lambda identifier, repo_root, actor, reason: {
            "kind": "error",
            "message": "cannot reject T-001: only OP-... proposals can be rejected",
        },
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    assert "Rejection failed" in message.replies[0][0] or "cannot reject" in message.replies[0][0]


@pytest.mark.asyncio
async def test_slash_dispatch_prevents_chat_message_call(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Slash commands do NOT fall through to chat_message()."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/help")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))
    chat_called = []

    monkeypatch.setattr(
        handlers.coo_service,
        "chat_message",
        lambda *a, **k: chat_called.append(True),
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert chat_called == []


@pytest.mark.asyncio
async def test_slash_prompt_status_replies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """/prompt_status replies with sync status."""
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/prompt_status")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(
        handlers.coo_service,
        "get_prompt_status",
        lambda r: {
            "in_sync": True,
            "canonical_sha256": "abc123def456",
            "live_sha256": "abc123def456",
            "canonical_exists": True,
            "live_exists": True,
        },
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    assert "IN SYNC" in message.replies[0][0]


# ---------------------------------------------------------------------------
# /model and /models command tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_model_command_shows_current_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/model")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers, "get_telegram_agent_primary", lambda: "openai-codex/gpt-5.4")

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    assert "openai-codex/gpt-5.4" in message.replies[0][0]


@pytest.mark.asyncio
async def test_model_command_sets_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/model openai-codex/gpt-5.3-codex")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    called_with: list[str] = []

    def _fake_set(repo_root, primary):
        called_with.append(primary)

    monkeypatch.setattr(handlers, "set_telegram_model", _fake_set)

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert called_with == ["openai-codex/gpt-5.3-codex"]
    assert "set to" in message.replies[0][0]


@pytest.mark.asyncio
async def test_model_command_unauthorized_user_ignored(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/model openai-codex/gpt-5.4")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=999))

    called = []
    monkeypatch.setattr(handlers, "set_telegram_model", lambda *a: called.append(a))

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert called == []
    assert message.replies == []


@pytest.mark.asyncio
async def test_models_command_shows_list(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/models")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(
        handlers, "list_allowed_models",
        lambda: ["openai-codex/gpt-5.4", "openai-codex/gpt-5.3-codex"],
    )
    monkeypatch.setattr(handlers, "get_telegram_agent_primary", lambda: "openai-codex/gpt-5.4")

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    reply = message.replies[0][0]
    assert "openai-codex/gpt-5.4" in reply
    assert "openai-codex/gpt-5.3-codex" in reply
    assert "Current:" in reply


# ---------------------------------------------------------------------------
# NLU model-switch tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_nlu_model_switch_calls_set_telegram_model(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="use openai-codex/gpt-5.4")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    called_with: list[str] = []
    monkeypatch.setattr(handlers, "set_telegram_model", lambda repo, primary: called_with.append(primary))

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert called_with == ["openai-codex/gpt-5.4"]
    assert "set to" in message.replies[0][0]


@pytest.mark.asyncio
async def test_nlu_model_switch_does_not_call_chat_message(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="switch to openai-codex/gpt-5.3-codex")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers, "set_telegram_model", lambda *a: None)
    chat_called = []
    monkeypatch.setattr(handlers.coo_service, "chat_message", lambda *a, **kw: chat_called.append(a))

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert chat_called == []


@pytest.mark.asyncio
async def test_nlu_model_switch_switch_to_variant(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="switch to openai-codex/gpt-5.4")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    called_with: list[str] = []
    monkeypatch.setattr(handlers, "set_telegram_model", lambda repo, primary: called_with.append(primary))

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert called_with == ["openai-codex/gpt-5.4"]


# ---------------------------------------------------------------------------
# Escalation follow-up reply tests
# ---------------------------------------------------------------------------

_SAMPLE_ESCALATION_PENDING = {
    "escalation_id": "ESC-0001",
    "options": [
        {"option_id": "A", "title": "Proceed", "action": "Do it", "resolution_action": "approve"},
        {"option_id": "B", "title": "Abort", "action": "Stop", "resolution_action": "reject"},
    ],
    "presented_at": "2026-04-07T00:00:00+00:00",
}


@pytest.mark.asyncio
async def test_pending_escalation_option_reply_approves(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime.channels.telegram.sessions import set_pending_escalation

    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    set_pending_escalation(tmp_path, 1, _SAMPLE_ESCALATION_PENDING)
    message = _FakeMessage(text="A")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "approve_escalation",
        lambda esc_id, repo, resolver, note="": {"kind": "escalation_approved", "escalation_id": esc_id},
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert len(message.replies) == 1
    assert "approved" in message.replies[0][0].lower()

    from runtime.channels.telegram.sessions import get_pending_escalation
    assert get_pending_escalation(tmp_path, 1) is None


@pytest.mark.asyncio
async def test_pending_escalation_option_reply_rejects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime.channels.telegram.sessions import set_pending_escalation

    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    set_pending_escalation(tmp_path, 1, _SAMPLE_ESCALATION_PENDING)
    message = _FakeMessage(text="option B")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    monkeypatch.setattr(
        handlers.coo_service,
        "reject_escalation",
        lambda esc_id, repo, resolver, reason="": {"kind": "escalation_rejected", "escalation_id": esc_id},
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert "rejected" in message.replies[0][0].lower()

    from runtime.channels.telegram.sessions import get_pending_escalation
    assert get_pending_escalation(tmp_path, 1) is None


@pytest.mark.asyncio
async def test_pending_escalation_no_resolution_action_prompts_explicit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime.channels.telegram.sessions import set_pending_escalation

    # Options without resolution_action
    pending = {
        "escalation_id": "ESC-0002",
        "options": [
            {"option_id": "A", "title": "Do something", "action": "Act"},
        ],
        "presented_at": "2026-04-07T00:00:00+00:00",
    }

    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    set_pending_escalation(tmp_path, 1, pending)
    message = _FakeMessage(text="A")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    chat_called = []
    monkeypatch.setattr(handlers.coo_service, "chat_message", lambda *a, **kw: chat_called.append(a))

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert chat_called == []
    assert "/approve" in message.replies[0][0] or "/reject" in message.replies[0][0]


@pytest.mark.asyncio
async def test_pending_escalation_unmatched_reply_blocks_chat(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from runtime.channels.telegram.sessions import set_pending_escalation

    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    set_pending_escalation(tmp_path, 1, _SAMPLE_ESCALATION_PENDING)
    message = _FakeMessage(text="hello random text")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    chat_called = []
    monkeypatch.setattr(handlers.coo_service, "chat_message", lambda *a, **kw: chat_called.append(a))

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert chat_called == []
    assert "Pending escalation" in message.replies[0][0]


# ---------------------------------------------------------------------------
# /approve ESC-... and /reject ESC-... tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_esc_id_calls_approve_escalation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/approve ESC-0001")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    called: list = []
    monkeypatch.setattr(
        handlers.coo_service,
        "approve_escalation",
        lambda esc_id, repo, resolver: called.append(esc_id) or {"kind": "escalation_approved", "escalation_id": esc_id},
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert called == ["ESC-0001"]
    assert "approved" in message.replies[0][0].lower()


@pytest.mark.asyncio
async def test_reject_esc_id_calls_reject_escalation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="/reject ESC-0001 not needed")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    called: list = []
    monkeypatch.setattr(
        handlers.coo_service,
        "reject_escalation",
        lambda esc_id, repo, resolver, reason="": called.append((esc_id, reason)) or {"kind": "escalation_rejected", "escalation_id": esc_id},
    )

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert called[0][0] == "ESC-0001"
    assert called[0][1] == "not needed"
    assert "rejected" in message.replies[0][0].lower()


# ---------------------------------------------------------------------------
# chat_message uses telegram agent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_message_uses_telegram_agent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = TelegramConfig(bot_token="token", allow_from=frozenset({123}), mode="polling")
    message = _FakeMessage(text="what is the backlog status?")
    update = _FakeUpdate(effective_message=message, effective_user=_FakeUser(id=123))

    monkeypatch.setattr(handlers.asyncio, "to_thread", _direct_to_thread)
    agent_used: list[str] = []

    def _fake_chat(text, repo_root, *, agent="main", **kwargs):
        agent_used.append(agent)
        return {"has_proposal": False, "message": "Here is the status."}

    monkeypatch.setattr(handlers.coo_service, "chat_message", _fake_chat)
    monkeypatch.setattr(handlers, "_typing_pulse", lambda *a, **kw: _noop_coro())

    async def _noop_coro():
        pass

    monkeypatch.setattr(handlers, "_typing_pulse", lambda *a, **kw: _noop_coro())

    await handlers.handle_message(update, None, repo_root=tmp_path, config=config)

    assert agent_used == ["telegram"]
