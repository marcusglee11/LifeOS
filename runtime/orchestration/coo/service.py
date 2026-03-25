"""Synchronous COO service helpers shared by CLI and chat adapters."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from runtime.orchestration.coo.context import build_chat_context
from runtime.orchestration.coo.invoke import invoke_coo_reasoning
from runtime.orchestration.coo.parser import (
    OPERATION_PROPOSAL_SCHEMA_VERSION,
    ParseError,
    _extract_yaml_payload,
    parse_operation_proposal,
)
from runtime.orchestration.ops.executor import OperationExecutionError, execute_operation
from runtime.orchestration.ops.queue import (
    find_receipt_by_proposal_id,
    load_proposal,
    now_iso,
    save_proposal,
    save_receipt,
)
from runtime.util.canonical import compute_sha256


def _strip_yaml_payload_from_text(raw_output: str, payload: str) -> str:
    text = raw_output.strip()
    fenced = f"```yaml\n{payload}\n```"
    if fenced in text:
        text = text.replace(fenced, "", 1)
    elif payload in text:
        text = text.replace(payload, "", 1)
    return text.strip()


def _terminal_receipt_for_proposal(
    proposal_id: str,
    repo_root: Path,
) -> dict[str, Any] | None:
    receipt = find_receipt_by_proposal_id(repo_root, proposal_id)
    if receipt is None:
        return None
    if str(receipt.get("status", "")).strip() in {"executed", "rejected", "failed"}:
        return receipt
    return None


def _existing_terminal_error(
    proposal_id: str,
    existing_receipt: dict[str, Any],
    *,
    requested_action: str,
) -> str:
    status = str(existing_receipt.get("status", "")).strip() or "unknown"
    if status == "rejected":
        return f"operation proposal {proposal_id} was already rejected"
    if status == "failed":
        error = str(existing_receipt.get("error", "") or "").strip()
        suffix = f": {error}" if error else ""
        return f"operation proposal {proposal_id} already failed{suffix}"
    if status == "executed":
        return f"operation proposal {proposal_id} was already executed; cannot {requested_action}"
    return f"operation proposal {proposal_id} already has terminal receipt status={status!r}"


def chat_message(
    message: str,
    repo_root: Path,
    *,
    auto_execute: bool = False,
    actor: str = "coo_chat",
) -> dict[str, Any]:
    context = build_chat_context(message, repo_root)
    run_id = compute_sha256({"context": context, "mode": "chat"})
    raw_output = invoke_coo_reasoning(
        context,
        mode="chat",
        repo_root=repo_root,
        run_id=run_id,
    )

    try:
        proposal = parse_operation_proposal(raw_output)
    except ParseError:
        if OPERATION_PROPOSAL_SCHEMA_VERSION in raw_output:
            raise
        return {
            "mode": "chat",
            "has_proposal": False,
            "proposal_id": None,
            "status": "conversation_only",
            "message": raw_output,
        }

    save_proposal(repo_root, proposal)
    payload = _extract_yaml_payload(raw_output)
    status = "pending"
    if auto_execute and not bool(proposal.get("requires_approval", True)):
        receipt = approve_operation(
            str(proposal["proposal_id"]),
            repo_root,
            approved_by=actor,
        )
        status = str(receipt.get("status", "executed"))

    return {
        "mode": "chat",
        "has_proposal": True,
        "proposal_id": proposal["proposal_id"],
        "status": status,
        "message": _strip_yaml_payload_from_text(raw_output, payload),
    }


def approve_operation(
    proposal_id: str,
    repo_root: Path,
    approved_by: str,
) -> dict[str, Any]:
    existing_receipt = _terminal_receipt_for_proposal(proposal_id, repo_root)
    if existing_receipt is not None:
        if str(existing_receipt.get("status", "")).strip() == "executed":
            return existing_receipt
        raise OperationExecutionError(
            _existing_terminal_error(
                proposal_id,
                existing_receipt,
                requested_action="approve",
            )
        )

    receipt = execute_operation(proposal_id, repo_root, approved_by)
    if receipt["status"] != "executed":
        raise OperationExecutionError(receipt["error"] or "operation execution failed")
    return receipt


def reject_operation(
    proposal_id: str,
    repo_root: Path,
    rejected_by: str,
    reason: str,
) -> dict[str, Any]:
    existing_receipt = _terminal_receipt_for_proposal(proposal_id, repo_root)
    if existing_receipt is not None:
        if str(existing_receipt.get("status", "")).strip() == "rejected":
            return existing_receipt
        raise OperationExecutionError(
            _existing_terminal_error(
                proposal_id,
                existing_receipt,
                requested_action="reject",
            )
        )

    proposal = load_proposal(repo_root, proposal_id)
    receipt = {
        "schema_version": "operational_receipt.v1",
        "receipt_id": f"OPRCP-{uuid.uuid4().hex[:8]}",
        "proposal_id": proposal_id,
        "order_id": None,
        "action_id": str(proposal.get("action_id", "")).strip(),
        "status": "rejected",
        "executed_at": now_iso(),
        "details": {},
        "error": None,
        "reason": reason,
        "actor": rejected_by,
    }
    save_receipt(repo_root, receipt)
    return receipt
