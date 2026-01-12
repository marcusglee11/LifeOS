"""
Backlog Parser v1.0
===================

Strict, fail-closed parser for YAML backlog format.
No inference, no unknown fields, deterministic ordering.

Per Mission Synthesis Engine MVP.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


# Schema constants
VALID_PRIORITIES = frozenset(["P0", "P1", "P2", "P3"])
VALID_STATUSES = frozenset(["TODO", "IN_PROGRESS", "DONE", "BLOCKED"])
ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
MAX_ID_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 2000
MAX_CONSTRAINTS = 20
MAX_CONSTRAINT_LENGTH = 500
MAX_CONTEXT_HINTS = 50

REQUIRED_FIELDS = frozenset(["id", "description", "priority"])
ALLOWED_FIELDS = frozenset([
    "id", "description", "priority", "constraints",
    "context_hints", "owner", "status", "due_date", "tags"
])


class BacklogParseError(Exception):
    """Raised when backlog parsing fails (fail-closed)."""
    pass


@dataclass(frozen=True)
class TaskSpec:
    """Parsed task specification. Immutable."""
    id: str
    description: str
    priority: str
    constraints: tuple[str, ...] = field(default_factory=tuple)
    context_hints: tuple[str, ...] = field(default_factory=tuple)
    owner: Optional[str] = None
    status: str = "TODO"
    due_date: Optional[str] = None
    tags: tuple[str, ...] = field(default_factory=tuple)


def _validate_task(task: Dict[str, Any], index: int) -> None:
    """Validate a single task dict. Raises BacklogParseError on failure."""
    
    # Check for unknown fields (fail-closed)
    unknown = set(task.keys()) - ALLOWED_FIELDS
    if unknown:
        raise BacklogParseError(
            f"Task[{index}]: Unknown fields: {sorted(unknown)}. "
            f"Allowed: {sorted(ALLOWED_FIELDS)}"
        )
    
    # Check required fields
    for field_name in REQUIRED_FIELDS:
        if field_name not in task:
            raise BacklogParseError(
                f"Task[{index}]: Missing required field '{field_name}'"
            )
    
    # Validate id
    task_id = task["id"]
    if not isinstance(task_id, str):
        raise BacklogParseError(
            f"Task[{index}]: 'id' must be string, got {type(task_id).__name__}"
        )
    if not ID_PATTERN.match(task_id):
        raise BacklogParseError(
            f"Task[{index}]: 'id' must match pattern [a-zA-Z0-9_-]+, got '{task_id}'"
        )
    if len(task_id) > MAX_ID_LENGTH:
        raise BacklogParseError(
            f"Task[{index}]: 'id' exceeds {MAX_ID_LENGTH} chars"
        )
    
    # Validate description
    desc = task["description"]
    if not isinstance(desc, str) or len(desc.strip()) == 0:
        raise BacklogParseError(
            f"Task[{index}]: 'description' must be non-empty string"
        )
    if len(desc) > MAX_DESCRIPTION_LENGTH:
        raise BacklogParseError(
            f"Task[{index}]: 'description' exceeds {MAX_DESCRIPTION_LENGTH} chars"
        )
    
    # Validate priority
    priority = task["priority"]
    if priority not in VALID_PRIORITIES:
        raise BacklogParseError(
            f"Task[{index}]: 'priority' must be one of {sorted(VALID_PRIORITIES)}, "
            f"got '{priority}'"
        )
    
    # Validate optional fields
    if "constraints" in task:
        constraints = task["constraints"]
        if not isinstance(constraints, list):
            raise BacklogParseError(
                f"Task[{index}]: 'constraints' must be list"
            )
        if len(constraints) > MAX_CONSTRAINTS:
            raise BacklogParseError(
                f"Task[{index}]: 'constraints' exceeds {MAX_CONSTRAINTS} items"
            )
        for i, c in enumerate(constraints):
            if not isinstance(c, str):
                raise BacklogParseError(
                    f"Task[{index}]: constraints[{i}] must be string"
                )
            if len(c) > MAX_CONSTRAINT_LENGTH:
                raise BacklogParseError(
                    f"Task[{index}]: constraints[{i}] exceeds {MAX_CONSTRAINT_LENGTH} chars"
                )
    
    if "context_hints" in task:
        hints = task["context_hints"]
        if not isinstance(hints, list):
            raise BacklogParseError(
                f"Task[{index}]: 'context_hints' must be list"
            )
        if len(hints) > MAX_CONTEXT_HINTS:
            raise BacklogParseError(
                f"Task[{index}]: 'context_hints' exceeds {MAX_CONTEXT_HINTS} items"
            )
        for i, h in enumerate(hints):
            if not isinstance(h, str):
                raise BacklogParseError(
                    f"Task[{index}]: context_hints[{i}] must be string"
                )
    
    if "status" in task:
        status = task["status"]
        if status not in VALID_STATUSES:
            raise BacklogParseError(
                f"Task[{index}]: 'status' must be one of {sorted(VALID_STATUSES)}, "
                f"got '{status}'"
            )
    
    if "tags" in task:
        tags = task["tags"]
        if not isinstance(tags, list):
            raise BacklogParseError(
                f"Task[{index}]: 'tags' must be list"
            )
        for i, t in enumerate(tags):
            if not isinstance(t, str):
                raise BacklogParseError(
                    f"Task[{index}]: tags[{i}] must be string"
                )


def _build_task_spec(task: Dict[str, Any]) -> TaskSpec:
    """Build TaskSpec from validated task dict."""
    return TaskSpec(
        id=task["id"],
        description=task["description"],
        priority=task["priority"],
        constraints=tuple(task.get("constraints", [])),
        context_hints=tuple(task.get("context_hints", [])),
        owner=task.get("owner"),
        status=task.get("status", "TODO"),
        due_date=task.get("due_date"),
        tags=tuple(task.get("tags", [])),
    )


def parse_backlog(backlog_path: Path) -> List[TaskSpec]:
    """
    Parse backlog YAML file into list of TaskSpec.
    
    Ordering: Preserves file order. No implicit sorting.
    Fail-closed: Any validation error raises BacklogParseError.
    
    Args:
        backlog_path: Path to backlog YAML file
        
    Returns:
        List of TaskSpec in file order
        
    Raises:
        BacklogParseError: On any validation failure
        FileNotFoundError: If file doesn't exist
    """
    if not backlog_path.exists():
        raise BacklogParseError(f"Backlog file not found: {backlog_path}")
    
    try:
        with open(backlog_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise BacklogParseError(f"YAML parse error: {e}")
    
    if not isinstance(data, dict):
        raise BacklogParseError("Backlog must be a YAML mapping")
    
    # Validate schema version
    schema_version = data.get("schema_version")
    if schema_version != "1.0":
        raise BacklogParseError(
            f"Unsupported schema_version: {schema_version}. Expected '1.0'"
        )
    
    # Get tasks
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        raise BacklogParseError("'tasks' must be a list")
    
    # Validate and build
    result: List[TaskSpec] = []
    for i, task in enumerate(tasks):
        if not isinstance(task, dict):
            raise BacklogParseError(f"Task[{i}] must be a mapping")
        _validate_task(task, i)
        result.append(_build_task_spec(task))
    
    return result


def get_task_by_id(tasks: List[TaskSpec], task_id: str) -> Optional[TaskSpec]:
    """Get task by ID. Returns None if not found."""
    for task in tasks:
        if task.id == task_id:
            return task
    return None


def sort_tasks_by_priority(tasks: List[TaskSpec]) -> List[TaskSpec]:
    """
    Sort tasks by (priority, id) for deterministic ordering.
    
    Priority order: P0 < P1 < P2 < P3 (P0 first)
    """
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    return sorted(tasks, key=lambda t: (priority_order[t.priority], t.id))
