"""
ExecutionOrder schema and validation.

The stable contract between the COO Agent (or any order source) and the Dispatch Engine.
Any source can produce an ExecutionOrder YAML file and place it in dispatch/inbox/.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

ORDER_SCHEMA_VERSION = "execution_order.v1"

_ORDER_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")


class OrderValidationError(ValueError):
    """Raised when an ExecutionOrder fails schema validation."""


@dataclass
class StepSpec:
    name: str
    role: str
    provider: str = "auto"
    mode: str = "blocking"
    lens_providers: Dict[str, str] = field(default_factory=dict)
    step_id: Optional[str] = None
    step_kind: Optional[str] = None
    mission_type: Optional[str] = None
    consumes: List[str] = field(default_factory=list)
    produces: Optional[str] = None
    mutation_class: Optional[str] = None


@dataclass
class ConstraintsSpec:
    governance_policy: Optional[str] = None
    worktree: bool = False
    max_duration_seconds: int = 3600
    scope_paths: List[str] = field(default_factory=list)


@dataclass
class ShadowSpec:
    enabled: bool = False
    provider: str = "codex"
    receives: str = "full_task_payload"


@dataclass
class SupervisionSpec:
    per_cycle_check: bool = False
    batch_id: Optional[str] = None
    cycle_number: Optional[int] = None


@dataclass
class ExecutionOrder:
    schema_version: str
    order_id: str
    task_ref: str
    created_at: str
    steps: List[StepSpec]
    workflow_id: Optional[str] = None
    workflow_version: Optional[str] = None
    review_policy_id: Optional[str] = None
    mutation_policy_id: Optional[str] = None
    task_context: Optional[Dict[str, Any]] = None
    constraints: ConstraintsSpec = field(default_factory=ConstraintsSpec)
    shadow: ShadowSpec = field(default_factory=ShadowSpec)
    supervision: SupervisionSpec = field(default_factory=SupervisionSpec)


def load_order(path: Path) -> ExecutionOrder:
    """Load and validate an ExecutionOrder from a YAML file."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        raise OrderValidationError(f"Invalid YAML in {path}: {exc}")

    if not isinstance(raw, dict):
        raise OrderValidationError(f"Order file must be a YAML mapping, got {type(raw).__name__}")

    return parse_order(raw)


def parse_order(raw: Dict[str, Any]) -> ExecutionOrder:
    """Parse and validate an ExecutionOrder from a dict."""
    schema_version = str(raw.get("schema_version", "")).strip()
    if schema_version != ORDER_SCHEMA_VERSION:
        raise OrderValidationError(
            f"Unsupported schema_version: {schema_version!r}. Expected {ORDER_SCHEMA_VERSION!r}"
        )

    order_id = str(raw.get("order_id", "")).strip()
    task_ref = str(raw.get("task_ref", "")).strip()
    created_at = str(raw.get("created_at", "")).strip()

    if not order_id:
        raise OrderValidationError("'order_id' is required")
    if not _ORDER_ID_RE.match(order_id):
        raise OrderValidationError(
            f"'order_id' must match [a-zA-Z0-9_\\-]{{1,128}}, got {order_id!r}"
        )
    if not task_ref:
        raise OrderValidationError("'task_ref' is required")
    if not created_at:
        raise OrderValidationError("'created_at' is required")

    raw_steps = raw.get("steps") or []
    if not raw_steps:
        raise OrderValidationError("'steps' must not be empty")

    steps: List[StepSpec] = []
    for i, s in enumerate(raw_steps):
        if not isinstance(s, dict):
            raise OrderValidationError(f"Step {i} must be a mapping")
        name = str(s.get("name", "")).strip()
        role = str(s.get("role", "")).strip()
        if not name:
            raise OrderValidationError(f"Step {i} missing 'name'")
        if not role:
            raise OrderValidationError(f"Step '{name}' missing 'role'")
        steps.append(
            StepSpec(
                name=name,
                role=role,
                provider=str(s.get("provider", "auto")),
                mode=str(s.get("mode", "blocking")),
                lens_providers=dict(s.get("lens_providers") or {}),
                step_id=str(s.get("step_id")).strip() if s.get("step_id") is not None else None,
                step_kind=str(s.get("step_kind")).strip()
                if s.get("step_kind") is not None
                else None,
                mission_type=str(s.get("mission_type")).strip()
                if s.get("mission_type") is not None
                else None,
                consumes=[str(item) for item in list(s.get("consumes") or [])],
                produces=str(s.get("produces")).strip() if s.get("produces") is not None else None,
                mutation_class=str(s.get("mutation_class")).strip()
                if s.get("mutation_class") is not None
                else None,
            )
        )

    raw_constraints = raw.get("constraints") or {}
    constraints = ConstraintsSpec(
        governance_policy=raw_constraints.get("governance_policy"),
        worktree=bool(raw_constraints.get("worktree", False)),
        max_duration_seconds=int(raw_constraints.get("max_duration_seconds", 3600)),
        scope_paths=list(raw_constraints.get("scope_paths") or []),
    )

    raw_shadow = raw.get("shadow") or {}
    shadow = ShadowSpec(
        enabled=bool(raw_shadow.get("enabled", False)),
        provider=str(raw_shadow.get("provider", "codex")),
        receives=str(raw_shadow.get("receives", "full_task_payload")),
    )

    raw_supervision = raw.get("supervision") or {}
    supervision = SupervisionSpec(
        per_cycle_check=bool(raw_supervision.get("per_cycle_check", False)),
        batch_id=raw_supervision.get("batch_id"),
        cycle_number=raw_supervision.get("cycle_number"),
    )

    return ExecutionOrder(
        schema_version=schema_version,
        order_id=order_id,
        task_ref=task_ref,
        created_at=created_at,
        steps=steps,
        workflow_id=str(raw.get("workflow_id")).strip()
        if raw.get("workflow_id") is not None
        else None,
        workflow_version=str(raw.get("workflow_version")).strip()
        if raw.get("workflow_version") is not None
        else None,
        review_policy_id=str(raw.get("review_policy_id")).strip()
        if raw.get("review_policy_id") is not None
        else None,
        mutation_policy_id=str(raw.get("mutation_policy_id")).strip()
        if raw.get("mutation_policy_id") is not None
        else None,
        task_context=dict(raw.get("task_context") or {}) or None,
        constraints=constraints,
        shadow=shadow,
        supervision=supervision,
    )
