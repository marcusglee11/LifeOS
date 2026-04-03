from __future__ import annotations

from pathlib import Path

import pytest

from runtime.orchestration.ops.executor import (
    OperationExecutionError,
    execute_operation_proposal,
)
from runtime.orchestration.ops.queue import persist_operation_proposal
from runtime.orchestration.ops.registry import (
    OperationValidationError,
    get_action_spec,
    normalize_workspace_path,
)


def _proposal(
    *,
    proposal_id: str = "OP-q1r2s3t4",
    title: str = "Inspect workspace",
    rationale: str = "Safe workspace inspection.",
    action_id: str = "workspace.file.read",
    args: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "operation_proposal.v1",
        "proposal_id": proposal_id,
        "title": title,
        "rationale": rationale,
        "operation_kind": "query",
        "action_id": action_id,
        "args": args or {"path": "/workspace/notes/test.md"},
        "requires_approval": True,
        "suggested_owner": "lifeos",
    }


@pytest.mark.parametrize(
    ("action_id", "path_value"),
    [
        ("workspace.file.read", "/workspace/notes/readme.md"),
        ("workspace.file.list", "/workspace/notes"),
        ("workspace.status.inspect", "/workspace/notes/readme.md"),
    ],
)
def test_normalize_workspace_path_accepts_workspace_alias_for_inspection_actions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    action_id: str,
    path_value: str,
) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path))
    resolved = normalize_workspace_path(path_value)

    assert resolved == (tmp_path / path_value.removeprefix("/workspace/")).resolve()
    spec = get_action_spec(action_id)
    assert spec.operation_kind == "query"
    assert spec.requires_approval is True


@pytest.mark.parametrize("path_value", ["../outside.txt", "/workspace/../outside.txt"])
def test_normalize_workspace_path_rejects_escape_for_inspection_actions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    path_value: str,
) -> None:
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(tmp_path))
    with pytest.raises(OperationValidationError, match="escapes workspace root"):
        normalize_workspace_path(path_value)


def test_execute_operation_proposal_read_round_trip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    target = workspace / "notes" / "test.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("hello inspection\n", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(
        repo_root,
        _proposal(args={"path": "/workspace/notes/test.md"}),
    )
    receipt = execute_operation_proposal(repo_root, "OP-q1r2s3t4")

    assert receipt["status"] == "executed"
    assert receipt["details"]["content"] == "hello inspection\n"
    assert receipt["details"]["bytes_read"] == len("hello inspection\n".encode("utf-8"))


def test_execute_operation_proposal_list_round_trip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    notes_dir = workspace / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    (notes_dir / "b.md").write_text("b", encoding="utf-8")
    (notes_dir / "a.md").write_text("a", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(
        repo_root,
        _proposal(
            proposal_id="OP-l1s2t3r4",
            title="List notes",
            action_id="workspace.file.list",
            args={"path": "/workspace/notes"},
        ),
    )
    receipt = execute_operation_proposal(repo_root, "OP-l1s2t3r4")

    assert receipt["status"] == "executed"
    assert receipt["details"]["entries"] == ["a.md", "b.md"]
    assert receipt["details"]["count"] == 2


def test_execute_operation_proposal_inspect_round_trip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    target = workspace / "notes" / "inspect.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("inspect me", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(
        repo_root,
        _proposal(
            proposal_id="OP-i1n2s3p4",
            title="Inspect note",
            action_id="workspace.status.inspect",
            args={"path": "/workspace/notes/inspect.md"},
        ),
    )
    receipt = execute_operation_proposal(repo_root, "OP-i1n2s3p4")

    assert receipt["status"] == "executed"
    assert receipt["details"]["exists"] is True
    assert receipt["details"]["type"] == "file"
    assert receipt["details"]["size"] == len("inspect me".encode("utf-8"))
    assert receipt["details"]["mtime"].endswith("+00:00")


def test_execute_operation_proposal_read_rejects_missing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(
        repo_root,
        _proposal(args={"path": "/workspace/notes/missing.md"}),
    )

    with pytest.raises(OperationExecutionError, match="missing"):
        execute_operation_proposal(repo_root, "OP-q1r2s3t4")


def test_execute_operation_proposal_read_rejects_directory_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    target = workspace / "notes"
    target.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(
        repo_root,
        _proposal(args={"path": "/workspace/notes"}),
    )

    with pytest.raises(OperationExecutionError, match="directory"):
        execute_operation_proposal(repo_root, "OP-q1r2s3t4")


def test_execute_operation_proposal_read_rejects_non_utf8_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    target = workspace / "notes" / "binary.bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b"\xff\xfe\x00")
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(
        repo_root,
        _proposal(args={"path": "/workspace/notes/binary.bin"}),
    )

    with pytest.raises(OperationExecutionError, match="UTF-8"):
        execute_operation_proposal(repo_root, "OP-q1r2s3t4")


def test_execute_operation_proposal_list_rejects_missing_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(
        repo_root,
        _proposal(
            proposal_id="OP-l1s2t3r4",
            title="List notes",
            action_id="workspace.file.list",
            args={"path": "/workspace/notes"},
        ),
    )

    with pytest.raises(OperationExecutionError, match="missing"):
        execute_operation_proposal(repo_root, "OP-l1s2t3r4")


def test_execute_operation_proposal_list_rejects_file_target(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    target = workspace / "notes.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("not a directory", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(
        repo_root,
        _proposal(
            proposal_id="OP-l1s2t3r4",
            title="List notes",
            action_id="workspace.file.list",
            args={"path": "/workspace/notes.txt"},
        ),
    )

    with pytest.raises(OperationExecutionError, match="not a directory"):
        execute_operation_proposal(repo_root, "OP-l1s2t3r4")


def test_execute_operation_proposal_inspect_missing_path_returns_exists_false(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    persist_operation_proposal(
        repo_root,
        _proposal(
            proposal_id="OP-i1n2s3p4",
            title="Inspect missing note",
            action_id="workspace.status.inspect",
            args={"path": "/workspace/notes/missing.md"},
        ),
    )
    receipt = execute_operation_proposal(repo_root, "OP-i1n2s3p4")

    assert receipt["status"] == "executed"
    assert receipt["details"] == {
        "path": str((workspace / "notes" / "missing.md").resolve()),
        "exists": False,
    }
