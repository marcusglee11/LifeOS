from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import yaml as _yaml

from runtime.orchestration.coo.backlog import BACKLOG_SCHEMA_VERSION
from runtime.orchestration.coo.service import (
    approve_item,
    approve_operation,
    chat_message,
    direct_coo,
    get_status_context,
    propose_coo,
    reject_item,
    reject_operation,
)


_VALID_OPERATION_YAML = """\
schema_version: operation_proposal.v1
proposal_id: OP-a1b2c3d4
title: "Write workspace note"
rationale: "The request fits the allowlisted ops lane."
operation_kind: mutation
action_id: workspace.file.write
args:
  path: /workspace/notes/example.md
  content: "Hello from COO."
requires_approval: true
suggested_owner: lifeos
"""

_LIVE_STYLE_OPERATION_YAML = """\
schema_version: operation_proposal.v1
proposal_id: OP-WORKSPACE-WRITE-TELEGRAM-002
title: "Write workspace note from Telegram"
rationale: "Persist a short note requested via chat: 'test from telegram'."
operation_kind: mutation
action_id: workspace.file.write
args:
  file_path: "/workspace/notes/telegram_test.md"
  content: "test from telegram"
  overwrite: true
requires_approval: true
suggested_owner: coo
"""


def test_chat_message_returns_conversation_only(tmp_path: Path) -> None:
    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning",
        return_value="Conversational response with no operation packet.",
    ):
        payload = chat_message("hello", tmp_path)

    assert payload["has_proposal"] is False
    assert payload["status"] == "conversation_only"


def test_chat_message_raises_on_malformed_operation_packet(tmp_path: Path) -> None:
    malformed = """\
schema_version: operation_proposal.v1
proposal_id: OP-a1b2c3d4
title: "Broken"
rationale: "broken"
operation_kind: mutation
action_id: workspace.file.write
args:
  path: /tmp/outside.md
  content: "Hello"
requires_approval: true
suggested_owner: lifeos
"""
    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning",
        return_value=malformed,
    ):
        with pytest.raises(Exception):
            chat_message("write a note", tmp_path)


def test_chat_message_persists_operation_proposal(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path / "workspace"))
    raw_output = "I can queue that.\n\n" + _VALID_OPERATION_YAML
    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning",
        return_value=raw_output,
    ):
        payload = chat_message("write a note", tmp_path)

    assert payload["has_proposal"] is True
    assert payload["proposal_id"] == "OP-a1b2c3d4"
    proposal_path = (
        tmp_path
        / "artifacts"
        / "coo"
        / "operations"
        / "proposals"
        / "OP-a1b2c3d4.yaml"
    )
    assert proposal_path.exists()


def test_chat_message_persists_live_style_operation_proposal(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path / "workspace"))
    raw_output = "Got it.\n\n" + _LIVE_STYLE_OPERATION_YAML
    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning",
        return_value=raw_output,
    ):
        payload = chat_message("write a workspace note saying test from telegram", tmp_path)

    assert payload["has_proposal"] is True
    assert payload["proposal_id"] == "OP-WORKSPACE-WRITE-TELEGRAM-002"
    proposal_path = (
        tmp_path
        / "artifacts"
        / "coo"
        / "operations"
        / "proposals"
        / "OP-WORKSPACE-WRITE-TELEGRAM-002.yaml"
    )
    assert proposal_path.exists()


def test_approve_operation_executes_and_writes_receipt(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path / "workspace"))
    proposal_dir = tmp_path / "artifacts" / "coo" / "operations" / "proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    (proposal_dir / "OP-a1b2c3d4.yaml").write_text(_VALID_OPERATION_YAML, encoding="utf-8")

    receipt = approve_operation("OP-a1b2c3d4", tmp_path, approved_by="tester")

    assert receipt["status"] == "executed"
    assert receipt["actor"] == "tester"
    assert (tmp_path / "workspace" / "notes" / "example.md").read_text(encoding="utf-8") == "Hello from COO."


def test_approve_operation_is_idempotent_after_execution(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path / "workspace"))
    proposal_dir = tmp_path / "artifacts" / "coo" / "operations" / "proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    (proposal_dir / "OP-a1b2c3d4.yaml").write_text(_VALID_OPERATION_YAML, encoding="utf-8")

    first = approve_operation("OP-a1b2c3d4", tmp_path, approved_by="tester")
    second = approve_operation("OP-a1b2c3d4", tmp_path, approved_by="tester")

    assert second == first
    receipt_dir = tmp_path / "artifacts" / "coo" / "operations" / "receipts"
    assert len(list(receipt_dir.glob("OPRCP-*.yaml"))) == 1


def test_reject_operation_writes_rejected_receipt(tmp_path: Path) -> None:
    proposal_dir = tmp_path / "artifacts" / "coo" / "operations" / "proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    (proposal_dir / "OP-a1b2c3d4.yaml").write_text(_VALID_OPERATION_YAML, encoding="utf-8")

    receipt = reject_operation(
        "OP-a1b2c3d4",
        tmp_path,
        rejected_by="tester",
        reason="No",
    )

    assert receipt["status"] == "rejected"
    assert receipt["reason"] == "No"
    assert receipt["actor"] == "tester"
    receipt_dir = tmp_path / "artifacts" / "coo" / "operations" / "receipts"
    receipts = list(receipt_dir.glob("OPRCP-*.yaml"))
    assert len(receipts) == 1
    raw = yaml.safe_load(receipts[0].read_text(encoding="utf-8"))
    assert raw["proposal_id"] == "OP-a1b2c3d4"


def test_reject_operation_blocks_after_execution(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path / "workspace"))
    proposal_dir = tmp_path / "artifacts" / "coo" / "operations" / "proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    (proposal_dir / "OP-a1b2c3d4.yaml").write_text(_VALID_OPERATION_YAML, encoding="utf-8")

    approve_operation("OP-a1b2c3d4", tmp_path, approved_by="tester")

    with pytest.raises(Exception, match="already executed"):
        reject_operation(
            "OP-a1b2c3d4",
            tmp_path,
            rejected_by="tester",
            reason="No",
        )


# ---------------------------------------------------------------------------
# Helper: write minimal backlog and delegation for propose_coo / get_status_context
# ---------------------------------------------------------------------------

_TASK_ENTRY = {
    "id": "T-001",
    "title": "Task T-001",
    "description": "desc",
    "dod": "done",
    "priority": "P1",
    "risk": "low",
    "scope_paths": ["runtime/"],
    "status": "pending",
    "requires_approval": False,
    "owner": "codex",
    "evidence": "",
    "task_type": "build",
    "tags": [],
    "objective_ref": "bootstrap",
    "created_at": "2026-01-01T00:00:00+00:00",
    "completed_at": None,
}

_VALID_PROPOSAL_YAML = """\
schema_version: task_proposal.v1
proposals:
  - task_id: T-001
    rationale: P1 priority.
    proposed_action: dispatch
    urgency_override: null
    suggested_owner: codex
"""

_VALID_NTP_YAML = """\
schema_version: nothing_to_propose.v1
reason: No pending actionable tasks.
recommended_follow_up: Wait for completions.
"""

_VALID_ESCALATION_YAML = """\
schema_version: escalation_packet.v1
run_id: test-001
type: governance_surface_touch
context:
  summary: Protected path modification requested.
analysis:
  issue: Path is protected.
options:
  - label: Escalate to CEO
    tradeoff: Governance-safe.
recommendation: Escalate to CEO.
"""


def _write_backlog(repo_root: Path, tasks: list | None = None) -> None:
    p = repo_root / "config" / "tasks" / "backlog.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        _yaml.dump(
            {"schema_version": BACKLOG_SCHEMA_VERSION, "tasks": tasks or [_TASK_ENTRY]},
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def _write_delegation(repo_root: Path) -> None:
    p = repo_root / "config" / "governance" / "delegation_envelope.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_yaml.dump({"schema_version": "delegation_envelope.v1"}), encoding="utf-8")


# ---------------------------------------------------------------------------
# propose_coo
# ---------------------------------------------------------------------------

def test_propose_coo_returns_task_proposal_kind(tmp_path: Path) -> None:
    _write_backlog(tmp_path)
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning",
        return_value=_VALID_PROPOSAL_YAML,
    ):
        result = propose_coo(tmp_path)

    assert result["kind"] == "task_proposal"
    assert "payload" in result
    assert "raw_output" in result
    assert "run_id" in result
    assert "parse_recovery_stage" in result
    assert "claim_violations" in result


def test_propose_coo_returns_nothing_to_propose_kind(tmp_path: Path) -> None:
    _write_backlog(tmp_path)
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning",
        return_value=_VALID_NTP_YAML,
    ):
        result = propose_coo(tmp_path)

    assert result["kind"] == "nothing_to_propose"
    assert result["payload"]["reason"] == "No pending actionable tasks."


def test_propose_coo_returns_dump_metadata(tmp_path: Path) -> None:
    _write_backlog(tmp_path)
    _write_delegation(tmp_path)

    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning",
        return_value=_VALID_PROPOSAL_YAML,
    ):
        result = propose_coo(tmp_path)

    assert isinstance(result["raw_output"], str)
    assert len(result["run_id"]) > 0
    assert isinstance(result["claim_violations"], list)
    assert isinstance(result["parse_recovery_stage"], str)


# ---------------------------------------------------------------------------
# direct_coo
# ---------------------------------------------------------------------------

def test_direct_coo_requires_source_and_actor(tmp_path: Path) -> None:
    """direct_coo() must accept source and actor kwargs."""
    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning",
        return_value=_VALID_OPERATION_YAML,
    ), patch(
        "runtime.orchestration.coo.service.verify_claims",
        return_value=[],
    ), patch(
        "runtime.orchestration.ops.queue.persist_operation_proposal",
    ):
        result = direct_coo(
            "write a note",
            tmp_path,
            source="telegram_direct",
            actor="telegram:123",
        )

    assert result["kind"] == "operation_proposal"
    assert "payload" in result
    assert "raw_output" in result


def test_direct_coo_escalation_includes_source_and_actor(tmp_path: Path) -> None:
    """For escalation results, source and actor are stored in EscalationEntry context."""
    from runtime.orchestration.ceo_queue import CEOQueue

    db_path = tmp_path / "artifacts" / "queue" / "escalations.db"

    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning",
        return_value=_VALID_ESCALATION_YAML,
    ), patch(
        "runtime.orchestration.coo.service.verify_claims",
        return_value=[],
    ):
        result = direct_coo(
            "touch a protected path",
            tmp_path,
            source="telegram_direct",
            actor="telegram:456",
        )

    assert result["kind"] == "escalation_packet"

    # Verify provenance was written to the DB
    db_path = tmp_path / "artifacts" / "queue" / "escalations.db"
    queue = CEOQueue(db_path=db_path)
    pending = queue.get_pending()
    assert len(pending) == 1
    assert pending[0].context.get("source") == "telegram_direct"
    assert pending[0].context.get("actor") == "telegram:456"


def test_direct_coo_cli_escalation_has_different_provenance(tmp_path: Path) -> None:
    """CLI-originated escalations use different source/actor from Telegram ones."""
    from runtime.orchestration.ceo_queue import CEOQueue

    with patch(
        "runtime.orchestration.coo.service.invoke_coo_reasoning",
        return_value=_VALID_ESCALATION_YAML,
    ), patch(
        "runtime.orchestration.coo.service.verify_claims",
        return_value=[],
    ):
        direct_coo(
            "touch a protected path",
            tmp_path,
            source="coo_direct",
            actor="cli:user",
        )

    db_path = tmp_path / "artifacts" / "queue" / "escalations.db"
    queue = CEOQueue(db_path=db_path)
    pending = queue.get_pending()
    assert pending[0].context.get("source") == "coo_direct"
    assert pending[0].context.get("actor") == "cli:user"


# ---------------------------------------------------------------------------
# approve_item — discriminated results
# ---------------------------------------------------------------------------

def test_approve_item_op_returns_operation_receipt(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path / "workspace"))
    proposal_dir = tmp_path / "artifacts" / "coo" / "operations" / "proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    (proposal_dir / "OP-a1b2c3d4.yaml").write_text(_VALID_OPERATION_YAML, encoding="utf-8")

    result = approve_item("OP-a1b2c3d4", tmp_path, actor="tester")

    assert result["kind"] == "operation_receipt"
    assert result["receipt"]["status"] == "executed"


def test_approve_item_task_returns_task_approval(tmp_path: Path) -> None:
    _write_backlog(tmp_path)

    # Write minimal template for "build" task type
    template_dir = tmp_path / "config" / "tasks" / "order_templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / "build.yaml").write_text(
        _yaml.dump({
            "schema_version": "order_template.v1",
            "template_name": "build",
            "steps": [{"name": "step1", "role": "codex"}],
            "constraints": {"max_duration_seconds": 60},
        }),
        encoding="utf-8",
    )

    result = approve_item("T-001", tmp_path, actor="tester")

    assert result["kind"] == "task_approval"
    assert result["task_id"] == "T-001"
    assert "order_id" in result


def test_approve_item_unknown_id_returns_error(tmp_path: Path) -> None:
    result = approve_item("UNKNOWN-123", tmp_path, actor="tester")

    assert result["kind"] == "error"
    assert "unknown identifier" in result["message"]


# ---------------------------------------------------------------------------
# reject_item
# ---------------------------------------------------------------------------

def test_reject_item_op_returns_operation_receipt(tmp_path: Path) -> None:
    proposal_dir = tmp_path / "artifacts" / "coo" / "operations" / "proposals"
    proposal_dir.mkdir(parents=True, exist_ok=True)
    (proposal_dir / "OP-a1b2c3d4.yaml").write_text(_VALID_OPERATION_YAML, encoding="utf-8")

    result = reject_item("OP-a1b2c3d4", tmp_path, actor="tester", reason="Not needed")

    assert result["kind"] == "operation_receipt"
    assert result["receipt"]["status"] == "rejected"


def test_reject_item_non_op_returns_error(tmp_path: Path) -> None:
    result = reject_item("T-001", tmp_path, actor="tester", reason="wrong type")

    assert result["kind"] == "error"
    assert "OP-" in result["message"]


# ---------------------------------------------------------------------------
# get_status_context — escalation count end-to-end via service wrapper
# ---------------------------------------------------------------------------

def test_get_status_context_escalation_count_via_service(tmp_path: Path) -> None:
    """get_status_context() reflects real pending escalations (Fix 1 end-to-end path)."""
    from runtime.orchestration.ceo_queue import CEOQueue, EscalationEntry, EscalationType

    _write_backlog(tmp_path)

    db_path = tmp_path / "artifacts" / "queue" / "escalations.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    queue = CEOQueue(db_path=db_path)
    queue.add_escalation(
        EscalationEntry(
            type=EscalationType.AMBIGUOUS_TASK,
            context={"summary": "e2e test escalation"},
            run_id="service-e2e-test",
        )
    )

    ctx = get_status_context(tmp_path)

    assert ctx["dispatch"]["escalations_pending"] == 1
