from __future__ import annotations

from pathlib import Path

import pytest

from runtime.orchestration.ops.executor import (
    OperationExecutionError,
    execute_operation_proposal,
)
from runtime.orchestration.ops.queue import (
    find_receipt_by_proposal_id,
    load_operation_proposal,
    persist_operation_proposal,
    save_receipt,
)
from runtime.orchestration.ops.registry import (
    OperationValidationError,
    normalize_workspace_path,
)


def _proposal(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "schema_version": "operation_proposal.v1",
        "proposal_id": "OP-a1b2c3d4",
        "title": "Write note",
        "rationale": "Safe workspace mutation.",
        "operation_kind": "mutation",
        "action_id": "workspace.file.write",
        "args": {
            "path": "/workspace/notes/test.md",
            "content": "hello",
        },
        "requires_approval": True,
        "suggested_owner": "lifeos",
    }
    base.update(overrides)
    return base


def test_normalize_workspace_path_accepts_workspace_alias(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path))
    resolved = normalize_workspace_path("/workspace/notes/test.md")
    assert resolved == (tmp_path / "notes" / "test.md").resolve()


def test_normalize_workspace_path_rejects_escape(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path))
    with pytest.raises(OperationValidationError, match="escapes workspace root"):
        normalize_workspace_path("../outside.txt")


def test_execute_operation_proposal_write_round_trip(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path / "workspace"))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(repo_root, _proposal())
    receipt = execute_operation_proposal(repo_root, "OP-a1b2c3d4")

    assert receipt["status"] == "executed"
    assert (tmp_path / "workspace" / "notes" / "test.md").read_text(encoding="utf-8") == "hello"


def test_execute_operation_proposal_edit_rejects_multiple_matches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "workspace"
    target = workspace / "notes" / "edit.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("same\nsame\n", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(
        repo_root,
        _proposal(
            proposal_id="OP-b1c2d3e4",
            title="Edit note",
            action_id="workspace.file.edit",
            args={
                "path": "/workspace/notes/edit.md",
                "old_text": "same",
                "new_text": "different",
            },
        ),
    )

    with pytest.raises(OperationExecutionError, match="multiple locations"):
        execute_operation_proposal(repo_root, "OP-b1c2d3e4")


def test_execute_operation_proposal_edit_rejects_zero_match(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "workspace"
    target = workspace / "notes" / "edit.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("unrelated content\n", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(
        repo_root,
        _proposal(
            proposal_id="OP-c1d2e3f4",
            title="Edit note",
            action_id="workspace.file.edit",
            args={
                "path": "/workspace/notes/edit.md",
                "old_text": "text that does not exist",
                "new_text": "replacement",
            },
        ),
    )

    with pytest.raises(OperationExecutionError, match="not found"):
        execute_operation_proposal(repo_root, "OP-c1d2e3f4")


def test_execute_operation_proposal_edit_rejects_missing_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(
        repo_root,
        _proposal(
            proposal_id="OP-d1e2f3a4",
            title="Edit missing file",
            action_id="workspace.file.edit",
            args={
                "path": "/workspace/notes/nonexistent.md",
                "old_text": "anything",
                "new_text": "replacement",
            },
        ),
    )

    with pytest.raises(OperationExecutionError, match="missing"):
        execute_operation_proposal(repo_root, "OP-d1e2f3a4")


def test_persist_operation_proposal_round_trip(tmp_path: Path) -> None:
    path = persist_operation_proposal(tmp_path, _proposal())
    loaded = load_operation_proposal(tmp_path, "OP-a1b2c3d4")
    assert path.exists()
    assert loaded["proposal_id"] == "OP-a1b2c3d4"


def test_find_receipt_by_proposal_id_returns_matching_receipt(tmp_path: Path) -> None:
    save_receipt(
        tmp_path,
        {
            "schema_version": "operational_receipt.v1",
            "receipt_id": "OPRCP-a1b2c3d4",
            "proposal_id": "OP-a1b2c3d4",
            "order_id": None,
            "action_id": "workspace.file.write",
            "status": "rejected",
            "executed_at": "2026-03-25T00:00:00Z",
            "details": {},
            "error": None,
            "reason": "No",
            "actor": "tester",
        },
    )

    receipt = find_receipt_by_proposal_id(tmp_path, "OP-a1b2c3d4")

    assert receipt is not None
    assert receipt["status"] == "rejected"
