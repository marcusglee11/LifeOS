"""CLI command handlers for COO orchestration flows."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from runtime.orchestration.ceo_queue import CEOQueue, EscalationEntry, EscalationType
from runtime.orchestration.coo.backlog import load_backlog
from runtime.orchestration.coo.context import (
    build_direct_context,
    build_propose_context,
    build_report_context,
    build_status_context,
)
from runtime.orchestration.coo import service as coo_service
from runtime.orchestration.coo.auto_dispatch import is_fully_auto_dispatchable
from runtime.orchestration.coo.claim_verifier import (
    collect_evidence,
    verify_claims,
    verify_progress_obligation,
)
from runtime.orchestration.coo.invoke import InvocationError, invoke_coo_reasoning
from runtime.orchestration.coo.parser import (
    ParseError,
    _extract_yaml_payload,  # shared within-package; not public API
    _extract_yaml_payload_with_stage,
    parse_operation_proposal,
    parse_proposal_response,
)
from runtime.orchestration.ops.executor import OperationExecutionError, execute_operation_proposal
from runtime.orchestration.ops.queue import persist_operation_proposal
from runtime.orchestration.ops.registry import resolve_openclaw_workspace_root
from runtime.orchestration.coo.templates import instantiate_order, load_template
from runtime.orchestration.dispatch.order import OrderValidationError, parse_order
from runtime.util.atomic_write import atomic_write_text
from runtime.util.canonical import compute_sha256, sha256_file


NTP_SCHEMA_VERSION = "nothing_to_propose.v1"
ESCALATION_SCHEMA_VERSION = "escalation_packet.v1"
OPERATION_SCHEMA_VERSION = "operation_proposal.v1"


_BACKLOG_RELATIVE_PATH = Path("config/tasks/backlog.yaml")
_PROMPT_CANONICAL_RELATIVE_PATH = Path("config") / "coo" / "prompt_canonical.md"


def _maybe_capture_dump(
    *,
    mode: str,
    raw_output: str,
    run_id: str,
    kind: str,
    parse_status: str,
    parse_recovery_stage: str,
    claim_violations: list,
) -> None:
    """Write a capture dump if LIFEOS_COO_CAPTURE_DIR is set."""
    capture_dir = os.environ.get("LIFEOS_COO_CAPTURE_DIR", "").strip()
    if not capture_dir:
        return

    label = os.environ.get("LIFEOS_COO_CAPTURE_LABEL", "unlabeled").strip() or "unlabeled"
    if not re.fullmatch(r"[A-Za-z0-9._-]+", label):
        raise ValueError(f"_maybe_capture_dump: LIFEOS_COO_CAPTURE_LABEL contains unsafe characters: {label!r}")
    capture_root = Path(capture_dir).resolve()
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dump = {
        "capture_ts": ts,
        "label": label,
        "mode": mode,
        "run_id": run_id,
        "kind": kind,
        "parse_status": parse_status,
        "parse_recovery_stage": parse_recovery_stage,
        "claim_violation_count": len(claim_violations),
        "raw_output_sha256": compute_sha256({"raw": raw_output}),
        "raw_output": raw_output,
    }
    capture_root.mkdir(parents=True, exist_ok=True)
    filename = f"{ts}_{mode}_{label}.json"
    out_path = (capture_root / filename).resolve()
    if not str(out_path).startswith(str(capture_root) + "/") and out_path != capture_root:
        raise ValueError(f"_maybe_capture_dump: resolved output path escapes capture_dir: {out_path}")
    atomic_write_text(out_path, json.dumps(dump, indent=2, sort_keys=True))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


def _coo_output_format(args: argparse.Namespace) -> str:
    if getattr(args, "json", False):
        return "json"
    if getattr(args, "yaml", False):
        return "yaml"

    explicit = getattr(args, "format", None)
    if explicit and explicit != "auto":
        return explicit

    env_value = os.environ.get("LIFEOS_COO_OUTPUT_FORMAT", "").strip().lower()
    if env_value in {"human", "yaml", "json"}:
        return env_value

    return "human" if sys.stdout.isatty() else "yaml"


def _task_title_map(repo_root: Path) -> dict[str, str]:
    backlog_path = repo_root / _BACKLOG_RELATIVE_PATH
    try:
        tasks = load_backlog(backlog_path)
    except Exception:
        return {}
    return {task.id: task.title for task in tasks}


def _render_task_proposal_human(payload: dict[str, Any], repo_root: Path) -> str:
    proposals = payload.get("proposals", [])
    title_map = _task_title_map(repo_root)

    lines = [
        f"COO proposal: {len(proposals)} item(s)",
        f"Objective: {payload.get('objective_ref', 'unknown')}",
    ]

    notes = str(payload.get("notes", "")).strip()
    if notes:
        lines.append(f"Notes: {notes}")

    for idx, proposal in enumerate(proposals, start=1):
        if not isinstance(proposal, dict):
            continue
        task_id = str(proposal.get("task_id", "")).strip() or "unknown-task"
        action = str(proposal.get("proposed_action", "")).strip() or "unspecified"
        urgency = proposal.get("urgency_override")
        owner = str(proposal.get("suggested_owner", "")).strip() or "unspecified"
        rationale = str(proposal.get("rationale", "")).strip() or "No rationale provided."
        title = title_map.get(task_id)

        header = f"{idx}. {task_id}"
        if title:
            header += f" - {title}"
        header += f" [{action}]"
        lines.append(header)
        if urgency:
            lines.append(f"   Priority override: {urgency}")
        lines.append(f"   Suggested owner: {owner}")
        lines.append(f"   Why: {rationale}")

    return "\n".join(lines)


def _render_ntp_human(payload: dict[str, Any]) -> str:
    reason = str(payload.get("reason", "")).strip() or "No reason provided."
    follow_up = str(payload.get("recommended_follow_up", "")).strip()
    lines = ["Nothing to propose", f"Reason: {reason}"]
    if follow_up:
        lines.append(f"Recommended follow-up: {follow_up}")
    return "\n".join(lines)


def cmd_coo_status(args: argparse.Namespace, repo_root: Path) -> int:
    """Print structured backlog status summary."""
    try:
        context = build_status_context(repo_root)
    except Exception as exc:
        _print_error(f"Error: {type(exc).__name__}: {exc}")
        return 1

    if getattr(args, "json", False):
        print(json.dumps(context, indent=2, sort_keys=True))
        return 0

    by_status = context.get("by_status", {})
    by_priority = context.get("by_priority", {})
    dispatch = context.get("dispatch", {})

    print(f"backlog: {context.get('total_tasks', 0)} tasks")
    print(f"  pending:     {by_status.get('pending', 0)}")
    print(f"  in_progress: {by_status.get('in_progress', 0)}")
    print(f"  completed:   {by_status.get('completed', 0)}")
    print(f"  blocked:     {by_status.get('blocked', 0)}")
    print()
    print(f"actionable ({context.get('actionable_count', 0)}):")
    print(
        "  "
        f"P0: {by_priority.get('P0', 0)}  "
        f"P1: {by_priority.get('P1', 0)}  "
        f"P2: {by_priority.get('P2', 0)}  "
        f"P3: {by_priority.get('P3', 0)}"
    )
    if dispatch:
        print()
        print("dispatch:")
        inbox_orders = dispatch.get("inbox_orders", [])
        inbox_label = f"  ({', '.join(inbox_orders[:3])})" if inbox_orders else ""
        print(f"  inbox:     {dispatch.get('inbox', 0)}{inbox_label}")
        active_orders = dispatch.get("active_orders", [])
        active_label = f"  ({', '.join(active_orders[:3])})" if active_orders else ""
        print(f"  active:    {dispatch.get('active', 0)}{active_label}")
        print(
            f"  completed: {dispatch.get('completed_total', 0)} "
            f"({dispatch.get('completed_success', 0)} SUCCESS, "
            f"{dispatch.get('completed_fail', 0)} CLEAN_FAIL)"
        )
        print()
        print(f"escalations: {dispatch.get('escalations_pending', 0)} pending")
    return 0


def _parse_ntp(raw_output: str) -> dict[str, Any]:
    """Parse a nothing_to_propose.v1 YAML block. Raises ParseError if invalid."""
    payload = _extract_yaml_payload(raw_output.strip())
    try:
        raw = yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        raise ParseError(f"NTP output is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ParseError("NTP output must be a YAML mapping")
    schema_version = str(raw.get("schema_version", "")).strip()
    if schema_version != NTP_SCHEMA_VERSION:
        raise ParseError(
            f"Unsupported schema_version: {schema_version!r}. "
            f"Expected {NTP_SCHEMA_VERSION!r}"
        )
    if not str(raw.get("reason", "")).strip():
        raise ParseError("NTP output missing required 'reason' field")
    return raw


def _parse_escalation_packet(raw_output: str) -> dict[str, Any]:
    """Parse an escalation_packet.v1 YAML block. Raises ParseError if invalid."""
    payload = _extract_yaml_payload(raw_output.strip())
    try:
        raw = yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        raise ParseError(f"Escalation packet is not valid YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ParseError("Escalation packet must be a YAML mapping")
    schema_version = str(raw.get("schema_version", "")).strip()
    if schema_version != ESCALATION_SCHEMA_VERSION:
        raise ParseError(
            f"Unsupported schema_version: {schema_version!r}. "
            f"Expected {ESCALATION_SCHEMA_VERSION!r}"
        )
    if not str(raw.get("type", "")).strip():
        raise ParseError("Escalation packet missing required 'type' field")
    if not isinstance(raw.get("options"), list) or not raw["options"]:
        raise ParseError("Escalation packet 'options' must be a non-empty list")
    return raw


def classify_coo_response(mode: str, raw_output: str) -> str:
    """Return the packet family string for a COO response without exposing parse internals.

    Returns one of: "operation_proposal", "escalation_packet", "task_proposal",
    "nothing_to_propose", "conversation_only".
    Raises ParseError if the output does not match any known schema for the given mode.
    """
    if mode == "direct":
        try:
            parse_operation_proposal(raw_output)
            return "operation_proposal"
        except Exception:
            _parse_escalation_packet(raw_output)
            return "escalation_packet"
    if mode == "chat":
        try:
            parse_operation_proposal(raw_output)
            return "operation_proposal"
        except Exception:
            return "conversation_only"
    try:
        parse_proposal_response(raw_output)
        return "task_proposal"
    except Exception:
        _parse_ntp(raw_output)
        return "nothing_to_propose"


def _persist_prompt_sync_receipt(repo_root: Path, payload: dict[str, Any]) -> Path:
    receipt_dir = repo_root / "artifacts" / "coo" / "operations" / "receipts"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt_name = f"prompt_sync_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    path = receipt_dir / receipt_name
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True))
    return path


def _build_prompt_status(repo_root: Path) -> dict[str, Any]:
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


def _strip_yaml_payload_from_text(raw_output: str, payload: str) -> str:
    text = raw_output.strip()
    fenced = f"```yaml\n{payload}\n```"
    if fenced in text:
        text = text.replace(fenced, "", 1)
    elif payload in text:
        text = text.replace(payload, "", 1)
    return text.strip()


def _queue_or_execute_operation(
    raw_output: str,
    repo_root: Path,
    *,
    auto_execute: bool = False,
) -> tuple[dict[str, Any], str, dict[str, Any] | None]:
    proposal = parse_operation_proposal(raw_output)
    persist_operation_proposal(repo_root, proposal)
    if auto_execute and not bool(proposal.get("requires_approval", True)):
        receipt = execute_operation_proposal(repo_root, str(proposal["proposal_id"]))
        return proposal, "executed", receipt
    return proposal, "pending", None


def cmd_coo_propose(args: argparse.Namespace, repo_root: Path) -> int:
    """Invoke live COO and emit task proposal or NothingToPropose response."""
    try:
        context = build_propose_context(repo_root)
    except Exception as exc:
        _print_error(f"Error: {type(exc).__name__}: {exc}")
        return 1

    run_id = compute_sha256({"context": context, "mode": "propose"})

    try:
        raw_output = invoke_coo_reasoning(context, mode="propose", repo_root=repo_root, run_id=run_id)
    except InvocationError as exc:
        _print_error(f"Error: COO invocation failed: {exc}")
        return 1
    _, _capture_stage = _extract_yaml_payload_with_stage(raw_output)

    output_format = _coo_output_format(args)

    # Try parsing as task_proposal.v1 first
    try:
        parse_proposal_response(raw_output)
        kind = "task_proposal"
        # Verify no unsupported execution claims
        evidence = collect_evidence(repo_root)
        violations = verify_claims(raw_output, evidence, repo_root=repo_root)
        if violations:
            _print_error(
                f"CLAIM_VIOLATION: COO output contains {len(violations)} unsupported claim(s)"
            )
            for v in violations:
                _print_error(
                    f"  - {v.claim_type}: {v.claim_text!r} "
                    f"(need: {v.required_evidence}, found: {v.found_evidence})"
                )
            return 1
        normalized = _extract_yaml_payload(raw_output)

        # --execute: auto-dispatch eligible proposals
        if getattr(args, "execute", False):
            try:
                proposal_dict = yaml.safe_load(normalized)
            except yaml.YAMLError:
                proposal_dict = {}

            dispatch_results = _auto_execute_proposals(
                proposal_dict, repo_root, args
            )
            if dispatch_results["any_dispatched"]:
                # Dispatch summary includes pending_proposals in JSON mode;
                # non-JSON pending proposals are printed per-task during eligibility check.
                _print_dispatch_summary(dispatch_results, args)
            else:
                # Nothing was dispatched — print full proposal YAML so CEO can review.
                if output_format == "json":
                    try:
                        payload_dict = yaml.safe_load(normalized)
                    except yaml.YAMLError:
                        payload_dict = {"raw": raw_output}
                    print(json.dumps({"kind": kind, "payload": payload_dict}, indent=2))
                elif output_format == "human":
                    try:
                        payload_dict = yaml.safe_load(normalized)
                    except yaml.YAMLError:
                        payload_dict = {"proposals": []}
                    print(_render_task_proposal_human(payload_dict, repo_root))
                else:
                    print(normalized)
            _maybe_capture_dump(
                mode="propose",
                raw_output=raw_output,
                run_id=run_id,
                kind=kind,
                parse_status="pass",
                parse_recovery_stage=_capture_stage,
                claim_violations=violations,
            )
            return 0 if not dispatch_results["failed_dispatches"] else 1

        if output_format == "json":
            try:
                payload_dict = yaml.safe_load(normalized)
            except yaml.YAMLError:
                payload_dict = {"raw": raw_output}
            print(json.dumps({"kind": kind, "payload": payload_dict}, indent=2))
        elif output_format == "human":
            try:
                payload_dict = yaml.safe_load(normalized)
            except yaml.YAMLError:
                payload_dict = {"proposals": []}
            print(_render_task_proposal_human(payload_dict, repo_root))
        else:
            print(normalized)
        _maybe_capture_dump(
            mode="propose",
            raw_output=raw_output,
            run_id=run_id,
            kind=kind,
            parse_status="pass",
            parse_recovery_stage=_capture_stage,
            claim_violations=violations,
        )
        return 0
    except ParseError:
        pass

    # Fall back to nothing_to_propose.v1
    try:
        ntp_dict = _parse_ntp(raw_output)
        kind = "nothing_to_propose"
        # Check progress obligation: NTP must cite a specific blocker
        ntp_evidence = collect_evidence(repo_root)
        obligation_violation = verify_progress_obligation(raw_output, ntp_evidence)
        if obligation_violation:
            _print_error(f"Warning: {obligation_violation}")
        if output_format == "json":
            print(json.dumps({"kind": kind, "payload": ntp_dict}, indent=2))
        elif output_format == "human":
            print(_render_ntp_human(ntp_dict))
        else:
            print(_extract_yaml_payload(raw_output))
        _maybe_capture_dump(
            mode="propose",
            raw_output=raw_output,
            run_id=run_id,
            kind=kind,
            parse_status="pass",
            parse_recovery_stage=_capture_stage,
            claim_violations=[],
        )
        return 0
    except ParseError as exc:
        _print_error(f"Error: COO output failed validation: {exc}")
        return 1


def cmd_coo_approve(args: argparse.Namespace, repo_root: Path) -> int:
    """Approve tasks and write validated ExecutionOrder files into dispatch inbox."""
    inbox_dir = repo_root / "artifacts" / "dispatch" / "inbox"
    try:
        inbox_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _print_error(f"Error: failed to create dispatch inbox at {inbox_dir}: {exc}")
        return 1

    approved: list[str] = []
    failed: list[dict[str, str]] = []

    backlog_path = repo_root / _BACKLOG_RELATIVE_PATH

    task_ids = list(getattr(args, "task_ids", None) or getattr(args, "ids", None) or [])

    for task_id in task_ids:
        if task_id.startswith("OP-"):
            try:
                receipt = coo_service.approve_operation(
                    task_id,
                    repo_root,
                    approved_by="CEO",
                )
            except Exception as exc:
                message = f"failed to execute operation proposal {task_id}: {exc}"
                _print_error(f"Error: {message}")
                failed.append({"task_id": task_id, "error": message})
                continue

            approved.append(str(receipt.get("order_id")))
            if not getattr(args, "json", False):
                print(f"approved: {task_id} -> {receipt.get('order_id')}")
            continue

        try:
            tasks = load_backlog(backlog_path)
        except Exception as exc:
            message = f"failed to load backlog ({backlog_path}): {exc}"
            _print_error(f"Error: {message}")
            failed.append({"task_id": task_id, "error": message})
            continue

        task = next((entry for entry in tasks if entry.id == task_id), None)
        if task is None:
            message = f"task not found: {task_id}"
            _print_error(f"Error: {message}")
            failed.append({"task_id": task_id, "error": message})
            continue

        if not task.requires_approval:
            _print_error(f"Warning: task {task_id} does not require approval; proceeding")

        try:
            template = load_template(task.task_type, repo_root)
        except FileNotFoundError:
            message = f"no template for task_type '{task.task_type}' (task {task_id})"
            _print_error(message)
            failed.append({"task_id": task_id, "error": message})
            continue
        except Exception as exc:
            message = f"failed to load template for task_type '{task.task_type}' (task {task_id}): {exc}"
            _print_error(f"Error: {message}")
            failed.append({"task_id": task_id, "error": message})
            continue

        order_dict = instantiate_order(
            template,
            task.id,
            task.scope_paths,
            created_at=_now_iso(),
            task=task,
        )

        try:
            parse_order(order_dict)
        except OrderValidationError as exc:
            message = f"invalid order for task {task_id}: {exc}"
            _print_error(f"Error: {message}")
            failed.append({"task_id": task_id, "error": message})
            continue

        order_id = str(order_dict["order_id"])
        order_path = inbox_dir / f"{order_id}.yaml"
        try:
            payload = yaml.dump(
                order_dict,
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
            atomic_write_text(order_path, payload)
        except Exception as exc:
            message = f"failed writing order for task {task_id}: {exc}"
            _print_error(f"Error: {message}")
            failed.append({"task_id": task_id, "error": message})
            continue

        approved.append(order_id)
        if not getattr(args, "json", False):
            print(f"approved: {task_id} -> {order_id}")

    if getattr(args, "json", False):
        print(json.dumps({"approved": approved, "failed": failed}, indent=2, sort_keys=True))

    return 0 if not failed else 1


def cmd_coo_report(args: argparse.Namespace, repo_root: Path) -> int:
    """Print report context as JSON."""
    try:
        context = build_report_context(repo_root)
    except Exception as exc:
        _print_error(f"Error: {type(exc).__name__}: {exc}")
        return 1

    print(json.dumps(context, indent=2, sort_keys=True))
    return 0


def cmd_coo_prompt_status(args: argparse.Namespace, repo_root: Path) -> int:
    payload = _build_prompt_status(repo_root)
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if payload["in_sync"] else 1

    status = "in_sync" if payload["in_sync"] else "drift"
    print(f"status: {status}")
    print(f"canonical: {payload['canonical_path']}")
    print(f"live: {payload['live_path']}")
    print(f"canonical_sha256: {payload['canonical_sha256'] or 'missing'}")
    print(f"live_sha256: {payload['live_sha256'] or 'missing'}")
    return 0 if payload["in_sync"] else 1


def cmd_coo_direct(args: argparse.Namespace, repo_root: Path) -> int:
    """Invoke live COO with direct intent and route escalation or operation output."""
    context = build_direct_context(repo_root, args.intent, source="coo_direct")

    direct_run_id = compute_sha256({"context": context, "mode": "direct"})

    try:
        raw_output = invoke_coo_reasoning(context, mode="direct", repo_root=repo_root, run_id=direct_run_id)
    except InvocationError as exc:
        _print_error(f"Error: COO invocation failed: {exc}")
        return 1
    _, _capture_stage = _extract_yaml_payload_with_stage(raw_output)

    try:
        kind = classify_coo_response("direct", raw_output)
    except ParseError as exc:
        _print_error(f"Error: COO output failed validation: {exc}")
        return 1

    evidence = collect_evidence(repo_root)
    violations = verify_claims(raw_output, evidence, repo_root=repo_root)
    if violations:
        _print_error(
            f"CLAIM_VIOLATION: COO output contains {len(violations)} unsupported claim(s)"
        )
        for v in violations:
            _print_error(
                f"  - {v.claim_type}: {v.claim_text!r} "
                f"(need: {v.required_evidence}, found: {v.found_evidence})"
            )
        return 1

    try:
        if kind == "operation_proposal":
            proposal, status, receipt = _queue_or_execute_operation(
                raw_output,
                repo_root,
                auto_execute=getattr(args, "execute", False),
            )
            if status == "executed" and receipt is not None:
                print(f"executed: {proposal['proposal_id']} -> {receipt['order_id']}")
            else:
                print(f"queued: {proposal['proposal_id']}")
        else:
            packet = _parse_escalation_packet(raw_output)
            packet_type_str = str(packet.get("type", "")).strip()
            try:
                escalation_type = EscalationType(packet_type_str)
            except ValueError:
                _print_error(
                    f"Error: Unknown escalation type {packet_type_str!r} from COO output"
                )
                return 1

            run_id = str(packet.get("run_id") or compute_sha256(packet))
            queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
            entry = EscalationEntry(
                type=escalation_type,
                context=packet.get("context", {"summary": args.intent, "source": "coo_direct"}),
                run_id=run_id,
            )
            escalation_id = queue.add_escalation(entry)
            print(f"queued: {escalation_id}")

        _maybe_capture_dump(
            mode="direct",
            raw_output=raw_output,
            run_id=direct_run_id,
            kind=kind,
            parse_status="pass",
            parse_recovery_stage=_capture_stage,
            claim_violations=violations,
        )
        return 0
    except Exception as exc:
        _print_error(f"Error: {type(exc).__name__}: {exc}")
        return 1


def cmd_coo_chat(args: argparse.Namespace, repo_root: Path) -> int:
    try:
        envelope = coo_service.chat_message(
            args.message,
            repo_root,
            auto_execute=getattr(args, "execute", False),
        )
    except InvocationError as exc:
        _print_error(f"Error: COO invocation failed: {exc}")
        return 1
    except (OperationExecutionError, ParseError, ValueError) as exc:
        _print_error(f"Error: COO chat failed: {exc}")
        return 1

    print(json.dumps(envelope, indent=2, sort_keys=True))
    return 0


def cmd_coo_reject(args: argparse.Namespace, repo_root: Path) -> int:
    proposal_id = str(args.proposal_id).strip()
    if not proposal_id.startswith("OP-"):
        _print_error("Error: coo reject only supports OP-... proposal IDs")
        return 1

    reason = str(getattr(args, "reason", "") or "").strip() or "Rejected by operator"
    try:
        receipt = coo_service.reject_operation(
            proposal_id,
            repo_root,
            rejected_by="CEO",
            reason=reason,
        )
    except Exception as exc:
        _print_error(f"Error: failed to reject {proposal_id}: {exc}")
        return 1

    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


def cmd_coo_telegram_run(args: argparse.Namespace, repo_root: Path) -> int:
    try:
        from runtime.channels.telegram.adapter import run_polling
        from runtime.channels.telegram.config import load_config

        config = load_config()
        run_polling(config, repo_root)
    except Exception as exc:
        _print_error(f"Error: telegram adapter failed: {exc}")
        return 1
    return 0


def _auto_execute_proposals(
    proposal_dict: dict[str, Any],
    repo_root: Path,
    args: argparse.Namespace,
) -> dict[str, Any]:
    """Execute eligible proposals from a task_proposal.v1 dict.

    Returns a summary dict with dispatch results.
    """
    from runtime.orchestration.coo.backlog import load_backlog
    from runtime.orchestration.dispatch.engine import DispatchEngine
    from runtime.orchestration.coo.templates import instantiate_order, load_template
    from runtime.orchestration.dispatch.order import parse_order

    results: dict[str, Any] = {
        "any_dispatched": False,
        "dispatched": [],
        "pending_proposals": [],
        "failed_dispatches": [],
    }

    proposals = proposal_dict.get("proposals", [])
    if not proposals:
        return results

    backlog_path = repo_root / _BACKLOG_RELATIVE_PATH
    try:
        all_tasks = load_backlog(backlog_path)
    except Exception as exc:
        _print_error(f"Error: failed to load backlog for auto-dispatch: {exc}")
        return results

    delegation_path = repo_root / "config" / "governance" / "delegation_envelope.yaml"
    try:
        import yaml as _yaml
        with open(delegation_path, "r", encoding="utf-8") as fh:
            envelope = _yaml.safe_load(fh)
    except Exception as exc:
        _print_error(f"Error: failed to load delegation envelope: {exc}")
        return results

    engine = DispatchEngine(repo_root=repo_root)

    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        if proposal.get("proposed_action") != "dispatch":
            results["pending_proposals"].append(proposal)
            continue

        task_id = str(proposal.get("task_id", "")).strip()
        task = next((t for t in all_tasks if t.id == task_id), None)
        if task is None:
            _print_error(f"Warning: task {task_id} not found in backlog; skipping auto-dispatch")
            results["pending_proposals"].append(proposal)
            continue

        eligible, reason = is_fully_auto_dispatchable(task, all_tasks, envelope)
        if not eligible:
            if not getattr(args, "json", False):
                print(f"pending approval: {task_id} — {reason}")
            results["pending_proposals"].append(proposal)
            continue

        # Eligible — create order and dispatch
        try:
            template = load_template(task.task_type, repo_root)
            order_dict = instantiate_order(
                template,
                task.id,
                task.scope_paths,
                created_at=_now_iso(),
                task=task,
            )
            order = parse_order(order_dict)
        except Exception as exc:
            _print_error(f"Error: failed to create order for {task_id}: {exc}")
            results["failed_dispatches"].append({"task_id": task_id, "error": str(exc)})
            continue

        try:
            dispatch_result = engine.execute(order)
        except Exception as exc:
            _print_error(f"Error: dispatch failed for {task_id}: {exc}")
            results["failed_dispatches"].append({"task_id": task_id, "error": str(exc)})
            continue

        results["any_dispatched"] = True
        if dispatch_result.outcome != "SUCCESS":
            results["failed_dispatches"].append({
                "task_id": task_id,
                "error": f"CLEAN_FAIL: {dispatch_result.reason}",
            })
        else:
            results["dispatched"].append({
                "task_id": task_id,
                "order_id": dispatch_result.order_id,
                "outcome": dispatch_result.outcome,
            })

    return results


def _print_dispatch_summary(
    dispatch_results: dict[str, Any],
    args: argparse.Namespace,
) -> None:
    """Print dispatch summary to stdout."""
    if getattr(args, "json", False):
        print(json.dumps({
            "auto_dispatch_results": dispatch_results
        }, indent=2))
        return

    for d in dispatch_results.get("dispatched", []):
        print(f"auto-dispatched: {d['task_id']} -> {d['order_id']} ({d['outcome']})")
    for f in dispatch_results.get("failed_dispatches", []):
        _print_error(f"dispatch failed: {f['task_id']}: {f['error']}")
