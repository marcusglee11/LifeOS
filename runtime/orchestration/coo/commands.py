"""CLI command handlers for COO orchestration flows."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import yaml

from runtime.orchestration.ceo_queue import CEOQueue, EscalationEntry, EscalationType
from runtime.orchestration.coo.backlog import load_backlog
from runtime.orchestration.coo.context import (
    build_propose_context,
    build_report_context,
    build_status_context,
)
from runtime.orchestration.coo.templates import instantiate_order, load_template
from runtime.orchestration.dispatch.order import OrderValidationError, parse_order
from runtime.util.atomic_write import atomic_write_text


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


def cmd_coo_propose(args: argparse.Namespace, repo_root: Path) -> int:
    """Print proposal context payload for COO invocation."""
    try:
        context = build_propose_context(repo_root)
    except Exception as exc:
        _print_error(f"Error: {type(exc).__name__}: {exc}")
        return 1

    print(json.dumps(context, indent=2, sort_keys=True))
    print("# COO invocation: not yet wired (Step 5)")
    return 0


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
    """Queue a COO directive as a CEO escalation entry."""
    try:
        queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
        entry = EscalationEntry(
            type=EscalationType.AMBIGUOUS_TASK,
            context={"summary": args.intent, "source": "coo_direct"},
            run_id=f"coo-direct-{uuid.uuid4().hex[:8]}",
        )
        escalation_id = queue.add_escalation(entry)
        print(f"queued: {escalation_id}")
        return 0
    except Exception as exc:
        _print_error(f"Error: {type(exc).__name__}: {exc}")
        return 1
