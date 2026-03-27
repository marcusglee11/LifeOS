"""Synchronous COO service helpers shared by CLI and chat adapters."""
from __future__ import annotations

import uuid
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from runtime.orchestration.coo.claim_verifier import collect_evidence, verify_claims
from runtime.orchestration.coo.context import build_chat_context, build_direct_context, build_propose_context, build_status_context
from runtime.orchestration.coo.invoke import InvocationError, invoke_coo_reasoning
from runtime.orchestration.coo.parser import (
    OPERATION_PROPOSAL_SCHEMA_VERSION,
    ParseError,
    _extract_yaml_payload,
    _extract_yaml_payload_with_stage,
    parse_escalation_packet,
    parse_ntp,
    parse_operation_proposal,
    parse_proposal_response,
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


_PROMPT_CANONICAL_RELATIVE_PATH = Path("config") / "coo" / "prompt_canonical.md"
_BACKLOG_RELATIVE_PATH = Path("config/tasks/backlog.yaml")


def get_status_context(repo_root: Path) -> dict[str, Any]:
    """Return status context dict (no stdout, no exit code).

    Escalation count uses get_pending() — see context.py Fix 1.
    """
    return build_status_context(repo_root)


def get_prompt_status(repo_root: Path) -> dict[str, Any]:
    """Return prompt sync status dict (canonical vs live hash comparison).

    Callers format the dict for display; this function does not print.
    """
    from runtime.orchestration.ops.registry import resolve_openclaw_workspace_root
    from runtime.util.canonical import sha256_file

    canonical_path = repo_root / _PROMPT_CANONICAL_RELATIVE_PATH
    live_path = resolve_openclaw_workspace_root() / "AGENTS.md"
    canonical_exists = canonical_path.exists()
    live_exists = live_path.exists()
    canonical_hash = sha256_file(canonical_path) if canonical_exists else None
    live_hash = sha256_file(live_path) if live_exists else None
    return {
        "canonical_path": str(canonical_path),
        "live_path": str(live_path),
        "canonical_exists": canonical_exists,
        "live_exists": live_exists,
        "canonical_sha256": canonical_hash,
        "live_sha256": live_hash,
        "in_sync": bool(canonical_exists and live_exists and canonical_hash == live_hash),
    }


def propose_coo(repo_root: Path) -> dict[str, Any]:
    """Invoke COO in propose mode and return parsed result with dump metadata.

    Returns a dict with keys:
        kind: "task_proposal" | "nothing_to_propose"
        payload: dict (parsed YAML)
        raw_output: str
        run_id: str
        parse_recovery_stage: str
        claim_violations: list

    Raises InvocationError on subprocess failure.
    Raises ParseError if output matches neither task_proposal.v1 nor nothing_to_propose.v1.

    CLI wrappers: check claim_violations, call _auto_execute_proposals() for --execute,
    then call _maybe_capture_dump() with the returned metadata fields.
    Telegram: use kind/payload only; ignore raw_output and dump fields.
    """
    context = build_propose_context(repo_root)
    run_id = compute_sha256({"context": context, "mode": "propose"})
    raw_output = invoke_coo_reasoning(context, mode="propose", repo_root=repo_root, run_id=run_id)
    _, parse_recovery_stage = _extract_yaml_payload_with_stage(raw_output)

    try:
        parse_proposal_response(raw_output)
        kind = "task_proposal"
        evidence = collect_evidence(repo_root)
        violations = list(verify_claims(raw_output, evidence, repo_root=repo_root))
        normalized = _extract_yaml_payload(raw_output)
        try:
            payload = yaml.safe_load(normalized)
            if not isinstance(payload, dict):
                payload = {"raw": raw_output}
        except yaml.YAMLError:
            payload = {"raw": raw_output}
        return {
            "kind": kind,
            "payload": payload,
            "raw_output": raw_output,
            "run_id": run_id,
            "parse_recovery_stage": parse_recovery_stage,
            "claim_violations": violations,
        }
    except ParseError:
        pass

    ntp_dict = parse_ntp(raw_output)
    return {
        "kind": "nothing_to_propose",
        "payload": ntp_dict,
        "raw_output": raw_output,
        "run_id": run_id,
        "parse_recovery_stage": parse_recovery_stage,
        "claim_violations": [],
    }


def direct_coo(intent: str, repo_root: Path, *, source: str, actor: str) -> dict[str, Any]:
    """Invoke COO in direct mode and return parsed result with dump metadata.

    Returns a dict with keys:
        kind: "operation_proposal" | "escalation_packet"
        payload: dict
        raw_output: str
        run_id: str
        parse_recovery_stage: str
        claim_violations: list

    For operation_proposal: payload contains proposal_id and proposal dict.
    For escalation_packet: payload contains packet fields + escalation_id (queued to CEO).
    Escalation context includes source and actor for provenance.

    Raises InvocationError on subprocess failure.
    Raises ParseError if output matches neither schema.
    """
    from runtime.orchestration.ceo_queue import CEOQueue, EscalationEntry, EscalationType
    from runtime.orchestration.ops.queue import persist_operation_proposal

    context = build_direct_context(repo_root, intent, source=source)
    run_id = compute_sha256({"context": context, "mode": "direct"})
    raw_output = invoke_coo_reasoning(context, mode="direct", repo_root=repo_root, run_id=run_id)
    _, parse_recovery_stage = _extract_yaml_payload_with_stage(raw_output)

    evidence = collect_evidence(repo_root)
    violations = list(verify_claims(raw_output, evidence, repo_root=repo_root))

    try:
        proposal = parse_operation_proposal(raw_output)
        persist_operation_proposal(repo_root, proposal)
        return {
            "kind": "operation_proposal",
            "payload": {"proposal_id": str(proposal["proposal_id"]), "proposal": proposal},
            "raw_output": raw_output,
            "run_id": run_id,
            "parse_recovery_stage": parse_recovery_stage,
            "claim_violations": violations,
        }
    except ParseError:
        pass

    packet = parse_escalation_packet(raw_output)
    packet_type_str = str(packet.get("type", "")).strip()
    try:
        escalation_type = EscalationType(packet_type_str)
    except ValueError as exc:
        raise ParseError(f"Unknown escalation type {packet_type_str!r}") from exc

    escalation_run_id = str(packet.get("run_id") or compute_sha256(packet))
    queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")

    context_dict: dict[str, Any] = dict(packet.get("context") or {})
    context_dict["source"] = source
    context_dict["actor"] = actor
    if "summary" not in context_dict:
        context_dict["summary"] = intent

    entry = EscalationEntry(
        type=escalation_type,
        context=context_dict,
        run_id=escalation_run_id,
    )
    escalation_id = queue.add_escalation(entry)

    return {
        "kind": "escalation_packet",
        "payload": {**packet, "escalation_id": escalation_id},
        "raw_output": raw_output,
        "run_id": run_id,
        "parse_recovery_stage": parse_recovery_stage,
        "claim_violations": violations,
    }


def approve_item(identifier: str, repo_root: Path, actor: str) -> dict[str, Any]:
    """Approve a task (T-...) or execute an operation proposal (OP-...).

    Returns a discriminated result dict:
        {"kind": "task_approval", "task_id": str, "order_id": str}
        {"kind": "operation_receipt", "receipt": dict}
        {"kind": "error", "message": str}
    """
    if identifier.startswith("OP-"):
        try:
            receipt = approve_operation(identifier, repo_root, approved_by=actor)
            return {"kind": "operation_receipt", "receipt": receipt}
        except Exception as exc:
            return {"kind": "error", "message": str(exc)}

    if identifier.startswith("T-"):
        from runtime.orchestration.coo.backlog import load_backlog
        from runtime.orchestration.coo.templates import instantiate_order, load_template
        from runtime.orchestration.dispatch.order import OrderValidationError, parse_order
        from runtime.util.atomic_write import atomic_write_text

        inbox_dir = repo_root / "artifacts" / "dispatch" / "inbox"
        try:
            inbox_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return {"kind": "error", "message": f"failed to create dispatch inbox: {exc}"}

        backlog_path = repo_root / _BACKLOG_RELATIVE_PATH
        try:
            tasks = load_backlog(backlog_path)
        except Exception as exc:
            return {"kind": "error", "message": f"failed to load backlog: {exc}"}

        task = next((t for t in tasks if t.id == identifier), None)
        if task is None:
            return {"kind": "error", "message": f"task not found: {identifier}"}

        try:
            template = load_template(task.task_type, repo_root)
        except Exception as exc:
            return {"kind": "error", "message": f"failed to load template for {task.task_type!r}: {exc}"}

        created_at = datetime.now(timezone.utc).isoformat()
        order_dict = instantiate_order(template, task.id, task.scope_paths, created_at=created_at, task=task)

        try:
            parse_order(order_dict)
        except OrderValidationError as exc:
            return {"kind": "error", "message": f"invalid order for {identifier}: {exc}"}

        order_id = str(order_dict["order_id"])
        order_path = inbox_dir / f"{order_id}.yaml"
        try:
            payload_str = yaml.dump(order_dict, default_flow_style=False, allow_unicode=True, sort_keys=False)
            atomic_write_text(order_path, payload_str)
        except Exception as exc:
            return {"kind": "error", "message": f"failed writing order for {identifier}: {exc}"}

        return {"kind": "task_approval", "task_id": identifier, "order_id": order_id}

    return {"kind": "error", "message": f"unknown identifier format: {identifier!r}. Expected T-... or OP-..."}


def reject_item(identifier: str, repo_root: Path, actor: str, reason: str) -> dict[str, Any]:
    """Reject an operation proposal (OP-... only).

    Returns a discriminated result dict:
        {"kind": "operation_receipt", "receipt": dict}
        {"kind": "error", "message": str}
    """
    if not identifier.startswith("OP-"):
        return {"kind": "error", "message": f"cannot reject {identifier!r}: only OP-... proposals can be rejected"}
    try:
        receipt = reject_operation(identifier, repo_root, rejected_by=actor, reason=reason)
        return {"kind": "operation_receipt", "receipt": receipt}
    except Exception as exc:
        return {"kind": "error", "message": str(exc)}


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
