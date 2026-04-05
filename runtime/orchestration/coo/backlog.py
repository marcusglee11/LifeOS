"""
Structured backlog for the COO orchestration layer.

Canonical task registry for the COO agent. The COO reads and writes this file
to track task state across invocations. This is the single source of truth for
all active, pending, completed, and blocked tasks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from runtime.util.atomic_write import atomic_write_text

BACKLOG_SCHEMA_VERSION = "backlog.v1"

VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
VALID_RISKS = {"low", "med", "high"}
VALID_STATUSES = {"pending", "in_progress", "completed", "blocked"}
VALID_TASK_TYPES = {"build", "content", "hygiene"}

_TASK_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


class BacklogValidationError(ValueError):
    """Raised when a TaskEntry fails validation."""


@dataclass
class TaskEntry:
    id: str
    title: str
    description: str
    dod: str
    priority: str
    risk: str
    scope_paths: List[str]
    status: str
    requires_approval: bool
    owner: str
    evidence: str
    task_type: str
    tags: List[str]
    objective_ref: str
    created_at: str
    completed_at: Optional[str] = None
    decision_support_required: bool = False


def _validate_task(raw: Dict[str, Any], index: int) -> TaskEntry:
    """Parse and validate a single task entry from a dict."""

    def _req(key: str) -> Any:
        val = raw.get(key)
        if val is None:
            raise BacklogValidationError(f"Task[{index}] missing required field '{key}'")
        return val

    task_id = str(_req("id")).strip()
    if not _TASK_ID_RE.match(task_id):
        raise BacklogValidationError(
            f"Task[{index}] 'id' must match [A-Za-z0-9_-]{{1,64}}, got {task_id!r}"
        )

    priority = str(_req("priority")).strip()
    if priority not in VALID_PRIORITIES:
        raise BacklogValidationError(
            f"Task '{task_id}' invalid priority {priority!r}. "
            f"Must be one of {sorted(VALID_PRIORITIES)}"
        )

    risk = str(_req("risk")).strip()
    if risk not in VALID_RISKS:
        raise BacklogValidationError(
            f"Task '{task_id}' invalid risk {risk!r}. Must be one of {sorted(VALID_RISKS)}"
        )

    status = str(_req("status")).strip()
    if status not in VALID_STATUSES:
        raise BacklogValidationError(
            f"Task '{task_id}' invalid status {status!r}. Must be one of {sorted(VALID_STATUSES)}"
        )

    task_type = str(_req("task_type")).strip()
    if task_type not in VALID_TASK_TYPES:
        raise BacklogValidationError(
            f"Task '{task_id}' invalid task_type {task_type!r}. "
            f"Must be one of {sorted(VALID_TASK_TYPES)}"
        )

    scope_paths = raw.get("scope_paths") or []
    if not isinstance(scope_paths, list):
        raise BacklogValidationError(f"Task '{task_id}' 'scope_paths' must be a list")

    tags = raw.get("tags") or []
    if not isinstance(tags, list):
        raise BacklogValidationError(f"Task '{task_id}' 'tags' must be a list")

    return TaskEntry(
        id=task_id,
        title=str(_req("title")).strip(),
        description=str(raw.get("description", "")).strip(),
        dod=str(raw.get("dod", "")).strip(),
        priority=priority,
        risk=risk,
        scope_paths=[str(p) for p in scope_paths],
        status=status,
        requires_approval=bool(raw.get("requires_approval", False)),
        decision_support_required=bool(raw.get("decision_support_required", False)),
        owner=str(raw.get("owner", "")).strip(),
        evidence=str(raw.get("evidence", "")).strip(),
        task_type=task_type,
        tags=[str(t) for t in tags],
        objective_ref=str(_req("objective_ref")).strip(),
        created_at=str(_req("created_at")).strip(),
        completed_at=raw.get("completed_at"),
    )


def load_backlog(path: Path) -> list[TaskEntry]:
    """Load and validate all tasks from a YAML backlog file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise BacklogValidationError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise BacklogValidationError(
            f"Backlog file must be a YAML mapping, got {type(raw).__name__}"
        )

    schema_version = str(raw.get("schema_version", "")).strip()
    if schema_version != BACKLOG_SCHEMA_VERSION:
        raise BacklogValidationError(
            f"Unsupported schema_version: {schema_version!r}. Expected {BACKLOG_SCHEMA_VERSION!r}"
        )

    raw_tasks = raw.get("tasks") or []
    if not isinstance(raw_tasks, list):
        raise BacklogValidationError("'tasks' must be a list")

    return [_validate_task(t, i) for i, t in enumerate(raw_tasks)]


def _task_to_dict(task: TaskEntry) -> Dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "dod": task.dod,
        "priority": task.priority,
        "risk": task.risk,
        "scope_paths": task.scope_paths,
        "status": task.status,
        "requires_approval": task.requires_approval,
        "decision_support_required": task.decision_support_required,
        "owner": task.owner,
        "evidence": task.evidence,
        "task_type": task.task_type,
        "tags": task.tags,
        "objective_ref": task.objective_ref,
        "created_at": task.created_at,
        "completed_at": task.completed_at,
    }


def save_backlog(path: Path, tasks: list[TaskEntry]) -> None:
    """Atomically save tasks to a YAML backlog file."""
    data = {
        "schema_version": BACKLOG_SCHEMA_VERSION,
        "tasks": [_task_to_dict(t) for t in tasks],
    }
    content = yaml.dump(data, default_flow_style=False, allow_unicode=True, sort_keys=False)
    atomic_write_text(path, content)


_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def filter_actionable(tasks: list[TaskEntry]) -> list[TaskEntry]:
    """Return tasks with status 'pending' or 'in_progress', sorted P0 first."""
    active = [t for t in tasks if t.status in ("pending", "in_progress")]
    return sorted(active, key=lambda t: _PRIORITY_ORDER.get(t.priority, 99))


def mark_in_progress(tasks: list[TaskEntry], task_id: str, evidence: str = "") -> list[TaskEntry]:
    """Return a new list with the specified task marked in_progress.

    Raises BacklogValidationError if task_id is not found.
    """
    found = False
    result = []
    for task in tasks:
        if task.id == task_id:
            found = True
            updated = TaskEntry(
                id=task.id,
                title=task.title,
                description=task.description,
                dod=task.dod,
                priority=task.priority,
                risk=task.risk,
                scope_paths=task.scope_paths,
                status="in_progress",
                requires_approval=task.requires_approval,
                decision_support_required=task.decision_support_required,
                owner=task.owner,
                evidence=evidence or task.evidence,
                task_type=task.task_type,
                tags=task.tags,
                objective_ref=task.objective_ref,
                created_at=task.created_at,
                completed_at=task.completed_at,
            )
            result.append(updated)
        else:
            result.append(task)

    if not found:
        raise BacklogValidationError(f"Task '{task_id}' not found in backlog")
    return result


def mark_blocked(tasks: list[TaskEntry], task_id: str, evidence: str = "") -> list[TaskEntry]:
    """Return a new list with the specified task marked blocked.

    Raises BacklogValidationError if task_id is not found.
    """
    found = False
    result = []
    for task in tasks:
        if task.id == task_id:
            found = True
            updated = TaskEntry(
                id=task.id,
                title=task.title,
                description=task.description,
                dod=task.dod,
                priority=task.priority,
                risk=task.risk,
                scope_paths=task.scope_paths,
                status="blocked",
                requires_approval=task.requires_approval,
                decision_support_required=task.decision_support_required,
                owner=task.owner,
                evidence=evidence or task.evidence,
                task_type=task.task_type,
                tags=task.tags,
                objective_ref=task.objective_ref,
                created_at=task.created_at,
                completed_at=task.completed_at,
            )
            result.append(updated)
        else:
            result.append(task)

    if not found:
        raise BacklogValidationError(f"Task '{task_id}' not found in backlog")
    return result


def mark_completed(tasks: list[TaskEntry], task_id: str, evidence: str = "") -> list[TaskEntry]:
    """Return a new list with the specified task marked completed.

    Raises BacklogValidationError if task_id is not found.
    """
    from datetime import datetime, timezone

    found = False
    result = []
    for task in tasks:
        if task.id == task_id:
            found = True
            updated = TaskEntry(
                id=task.id,
                title=task.title,
                description=task.description,
                dod=task.dod,
                priority=task.priority,
                risk=task.risk,
                scope_paths=task.scope_paths,
                status="completed",
                requires_approval=task.requires_approval,
                decision_support_required=task.decision_support_required,
                owner=task.owner,
                evidence=evidence or task.evidence,
                task_type=task.task_type,
                tags=task.tags,
                objective_ref=task.objective_ref,
                created_at=task.created_at,
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
            result.append(updated)
        else:
            result.append(task)

    if not found:
        raise BacklogValidationError(f"Task '{task_id}' not found in backlog")
    return result
