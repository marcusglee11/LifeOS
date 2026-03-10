"""Template loading and instantiation for COO execution orders."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from runtime.orchestration.coo.backlog import TaskEntry
from runtime.orchestration.workflow_runtime import build_task_context, resolve_workflow_id_for_task_type

TEMPLATE_SCHEMA_VERSION = "order_template.v1"


class TemplateValidationError(ValueError):
    """Raised when an order template fails schema validation."""


def load_template(template_name: str, repo_root: Path) -> dict[str, Any]:
    """Load and validate an order template from config/tasks/order_templates/."""
    path = (
        repo_root
        / "config"
        / "tasks"
        / "order_templates"
        / f"{template_name}.yaml"
    )

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise TemplateValidationError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise TemplateValidationError(
            f"Template file must be a YAML mapping, got {type(raw).__name__}"
        )

    schema_version = str(raw.get("schema_version", "")).strip()
    if schema_version != TEMPLATE_SCHEMA_VERSION:
        raise TemplateValidationError(
            "Unsupported schema_version: "
            f"{schema_version!r}. Expected {TEMPLATE_SCHEMA_VERSION!r}"
        )

    declared_name = str(raw.get("template_name", "")).strip()
    if declared_name != template_name:
        raise TemplateValidationError(
            f"Template name mismatch: expected {template_name!r}, got {declared_name!r}"
        )

    steps = raw.get("steps")
    if not isinstance(steps, list) or not steps:
        raise TemplateValidationError("'steps' must be a non-empty list")

    return raw


def _parse_order_timestamp(created_at: str) -> str:
    try:
        parsed = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        parsed = datetime.now(timezone.utc)
    return parsed.strftime("%Y%m%d%H%M%S")


def instantiate_order(
    template: dict[str, Any],
    task_id: str,
    scope_paths: list[str],
    created_at: str,
    task: TaskEntry | None = None,
) -> dict[str, Any]:
    """Instantiate an execution-order-compatible dict from an order template."""
    timestamp = _parse_order_timestamp(created_at)

    constraints = template.get("constraints") or {}
    workflow_id = resolve_workflow_id_for_task_type(task.task_type) if task else None
    task_context = build_task_context(task) if task else None

    return {
        "schema_version": "execution_order.v1",
        "order_id": f"ORD-{task_id}-{timestamp}",
        "task_ref": task_id,
        "created_at": created_at,
        "workflow_id": workflow_id,
        "workflow_version": "workflow_runtime.v1" if workflow_id else None,
        "review_policy_id": "spec_review.v1" if workflow_id == "spec_creation.v1" else "legacy_build_review.v1",
        "mutation_policy_id": "mutation_authority.v1" if workflow_id else None,
        "task_context": task_context,
        "steps": deepcopy(template["steps"]),
        "constraints": {
            "governance_policy": constraints.get("governance_policy"),
            "worktree": constraints.get("worktree", False),
            "max_duration_seconds": constraints.get("max_duration_seconds", 3600),
            "scope_paths": list(scope_paths),
        },
        "shadow": deepcopy(
            template.get(
                "shadow",
                {
                    "enabled": False,
                    "provider": "codex",
                    "receives": "full_task_payload",
                },
            )
        ),
        "supervision": deepcopy(
            template.get("supervision", {"per_cycle_check": False})
        ),
    }
