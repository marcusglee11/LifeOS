from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from runtime.orchestration.coo.service import (
    approve_operation,
    chat_message,
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
