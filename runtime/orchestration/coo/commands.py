"""CLI command handlers for COO orchestration flows."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from runtime.orchestration.ceo_queue import CEOQueue, EscalationEntry, EscalationType
from runtime.orchestration.coo.backlog import load_backlog
from runtime.orchestration.coo.context import (
    build_propose_context,
    build_report_context,
    build_status_context,
)
from runtime.orchestration.coo.invoke import InvocationError, invoke_coo_reasoning
from runtime.orchestration.coo.parser import (
    ParseError,
    _extract_yaml_payload,  # shared within-package; not public API
    parse_proposal_response,
)
from runtime.orchestration.coo.templates import instantiate_order, load_template
from runtime.orchestration.dispatch.order import OrderValidationError, parse_order
from runtime.util.atomic_write import atomic_write_text


NTP_SCHEMA_VERSION = "nothing_to_propose.v1"
ESCALATION_SCHEMA_VERSION = "escalation_packet.v1"


_BACKLOG_RELATIVE_PATH = Path("config/tasks/backlog.yaml")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _print_error(message: str) -> None:
    print(message, file=sys.stderr)


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


def cmd_coo_propose(args: argparse.Namespace, repo_root: Path) -> int:
    """Invoke live COO and emit task proposal or NothingToPropose response."""
    try:
        context = build_propose_context(repo_root)
    except Exception as exc:
        _print_error(f"Error: {type(exc).__name__}: {exc}")
        return 1

    try:
        raw_output = invoke_coo_reasoning(context, mode="propose", repo_root=repo_root)
    except InvocationError as exc:
        _print_error(f"Error: COO invocation failed: {exc}")
        return 1

    # Try parsing as task_proposal.v1 first
    try:
        parse_proposal_response(raw_output)
        kind = "task_proposal"
        normalized = _extract_yaml_payload(raw_output)
        if getattr(args, "json", False):
            try:
                payload_dict = yaml.safe_load(normalized)
            except yaml.YAMLError:
                payload_dict = {"raw": raw_output}
            print(json.dumps({"kind": kind, "payload": payload_dict}, indent=2))
        else:
            print(normalized)
        return 0
    except ParseError:
        pass

    # Fall back to nothing_to_propose.v1
    try:
        ntp_dict = _parse_ntp(raw_output)
        kind = "nothing_to_propose"
        if getattr(args, "json", False):
            print(json.dumps({"kind": kind, "payload": ntp_dict}, indent=2))
        else:
            print(_extract_yaml_payload(raw_output))
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

    for task_id in args.task_ids:
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


def cmd_coo_direct(args: argparse.Namespace, repo_root: Path) -> int:
    """Invoke live COO with direct intent and queue resulting EscalationPacket."""
    context: dict[str, Any] = {
        "intent": args.intent,
        "source": "coo_direct",
    }

    try:
        raw_output = invoke_coo_reasoning(context, mode="direct", repo_root=repo_root)
    except InvocationError as exc:
        _print_error(f"Error: COO invocation failed: {exc}")
        return 1

    try:
        packet = _parse_escalation_packet(raw_output)
    except ParseError as exc:
        _print_error(f"Error: COO output failed validation: {exc}")
        return 1

    packet_type_str = str(packet.get("type", "")).strip()
    try:
        escalation_type = EscalationType(packet_type_str)
    except ValueError:
        _print_error(
            f"Error: Unknown escalation type {packet_type_str!r} from COO output"
        )
        return 1

    run_id = str(packet.get("run_id", f"coo-direct-{uuid.uuid4().hex[:8]}"))

    try:
        queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
        entry = EscalationEntry(
            type=escalation_type,
            context=packet.get("context", {"summary": args.intent, "source": "coo_direct"}),
            run_id=run_id,
        )
        escalation_id = queue.add_escalation(entry)
        print(f"queued: {escalation_id}")
        return 0
    except Exception as exc:
        _print_error(f"Error: {type(exc).__name__}: {exc}")
        return 1
