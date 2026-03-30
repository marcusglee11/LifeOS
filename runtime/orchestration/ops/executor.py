from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from runtime.orchestration.ops.queue import (
    load_operation_proposal,
    now_iso,
    save_order,
    save_receipt,
)
from runtime.orchestration.ops.registry import (
    OperationValidationError,
    validate_action,
)
from runtime.util.atomic_write import atomic_write_text


class OperationExecutionError(RuntimeError):
    pass


def _short_uuid() -> str:
    return uuid.uuid4().hex[:8]


def _render_note_markdown(*, title: str, timestamp: str, tags: list[str], content: str) -> str:
    frontmatter = {
        "title": title,
        "timestamp": timestamp,
        "tags": tags,
    }
    return (
        f"---\n{yaml.safe_dump(frontmatter, sort_keys=False).strip()}\n---\n\n{content.rstrip()}\n"
    )


def _execute_write(args: dict[str, Any]) -> dict[str, Any]:
    path = Path(args["resolved_path"])
    atomic_write_text(path, args["content"])
    return {"path": str(path), "bytes_written": len(args["content"].encode("utf-8"))}


def _execute_edit(args: dict[str, Any]) -> dict[str, Any]:
    path = Path(args["resolved_path"])
    if not path.exists():
        raise OperationExecutionError(f"Target file missing: {path}")
    current = path.read_text(encoding="utf-8")
    occurrences = current.count(args["old_text"])
    if occurrences == 0:
        raise OperationExecutionError("args.old_text not found in target file")
    if occurrences > 1:
        raise OperationExecutionError("args.old_text matched multiple locations in target file")
    updated = current.replace(args["old_text"], args["new_text"], 1)
    atomic_write_text(path, updated)
    return {
        "path": str(path),
        "bytes_written": len(updated.encode("utf-8")),
        "replacements": 1,
    }


def _execute_note(args: dict[str, Any]) -> dict[str, Any]:
    path = Path(args["resolved_path"])
    body = _render_note_markdown(
        title=args["title"],
        timestamp=args["timestamp"],
        tags=args["tags"],
        content=args["content"],
    )
    atomic_write_text(path, body)
    return {"path": str(path), "bytes_written": len(body.encode("utf-8"))}


_EXECUTORS = {
    "workspace.file.write": _execute_write,
    "workspace.file.edit": _execute_edit,
    "lifeos.note.record": _execute_note,
}


def execute_operation(
    proposal_id: str,
    repo_root: Path,
    actor: str,
) -> dict[str, Any]:
    proposal = load_operation_proposal(repo_root, proposal_id)
    action_id = str(proposal.get("action_id", "")).strip()
    try:
        normalized_args = validate_action(action_id, proposal.get("args") or {})
    except OperationValidationError as exc:
        raise OperationExecutionError(str(exc)) from exc

    order_id = f"OPR-{_short_uuid()}"
    order = {
        "schema_version": "operational_order.v1",
        "order_id": order_id,
        "proposal_id": proposal_id,
        "created_at": now_iso(),
        "approved_at": now_iso(),
        "approved_by": actor,
        "action_id": action_id,
        "operation_kind": proposal.get("operation_kind"),
        "args": normalized_args,
    }
    save_order(repo_root, order)

    executor = _EXECUTORS.get(action_id)
    if executor is None:
        raise OperationExecutionError(f"No executor registered for action_id {action_id}")

    status = "executed"
    details: dict[str, Any]
    error = None
    try:
        details = executor(normalized_args)
    except Exception as exc:
        status = "failed"
        details = {}
        error = str(exc)

    receipt_id = f"OPRCP-{_short_uuid()}"
    receipt = {
        "schema_version": "operational_receipt.v1",
        "receipt_id": receipt_id,
        "proposal_id": proposal_id,
        "order_id": order_id,
        "action_id": action_id,
        "status": status,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "details": details,
        "error": error,
        "reason": None,
        "actor": actor,
    }
    save_receipt(repo_root, receipt)
    return receipt


def execute_operation_proposal(
    repo_root: Path,
    proposal_id: str,
    approved_by: str = "CEO",
) -> dict[str, Any]:
    receipt = execute_operation(proposal_id, repo_root, approved_by)
    if receipt["status"] != "executed":
        raise OperationExecutionError(receipt["error"] or "operation execution failed")
    return receipt
