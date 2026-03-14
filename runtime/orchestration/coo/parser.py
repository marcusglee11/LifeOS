"""
Parser utilities for COO proposal responses and execution-order generation.
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

import yaml

from runtime.orchestration.coo.backlog import TaskEntry

PROPOSAL_SCHEMA_VERSION = "task_proposal.v1"

_VALID_ACTIONS = {"dispatch", "defer", "escalate"}
_VALID_URGENCY = {"P0", "P1", "P2", "P3"}
_YAML_FENCE_RE = re.compile(r"```yaml\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_SCHEMA_BLOCK_RE = re.compile(
    r"^[ \t]*schema_version:",  # [ \t]* not \s* — avoids matching across blank lines
    re.MULTILINE,
)
_ORDER_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")


@dataclass
class TaskProposal:
    task_id: str
    rationale: str
    urgency_override: Optional[str]
    suggested_owner: str
    proposed_action: str


class ParseError(ValueError):
    pass


def _extract_yaml_payload(text: str) -> str:
    # 1. Markdown fence
    match = _YAML_FENCE_RE.search(text)
    if match:
        return match.group(1).strip()

    stripped = text.strip()

    # 2. Strip prose preamble before schema_version:
    #    Only apply when the full text doesn't already parse as a valid YAML mapping,
    #    preventing truncation of valid YAML where schema_version isn't the first key.
    schema_match = _SCHEMA_BLOCK_RE.search(stripped)
    if schema_match and schema_match.start() > 0:
        try:
            candidate = yaml.safe_load(stripped)
        except yaml.YAMLError:
            candidate = None
        if not isinstance(candidate, dict):
            return stripped[schema_match.start():].strip()

    # 3. Return as-is
    return stripped


def parse_proposal_response(text: str) -> list[TaskProposal]:
    payload = _extract_yaml_payload(text)
    try:
        raw = yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        raise ParseError(f"Failed to parse proposal YAML: {exc}") from exc

    if not isinstance(raw, dict):
        raise ParseError(
            f"Proposal payload must be a YAML mapping, got {type(raw).__name__}"
        )

    schema_version = str(raw.get("schema_version", "")).strip()
    if schema_version != PROPOSAL_SCHEMA_VERSION:
        raise ParseError(
            f"Unsupported schema_version: {schema_version!r}. "
            f"Expected {PROPOSAL_SCHEMA_VERSION!r}"
        )

    raw_proposals = raw.get("proposals")
    if not isinstance(raw_proposals, list):
        raise ParseError("'proposals' must be a list")
    if not raw_proposals:
        raise ParseError("No proposals found in response")

    proposals: list[TaskProposal] = []
    for idx, entry in enumerate(raw_proposals):
        if not isinstance(entry, dict):
            raise ParseError(f"Proposal[{idx}] must be a YAML mapping")

        task_id = str(entry.get("task_id", "")).strip()
        rationale = str(entry.get("rationale", "")).strip()
        proposed_action = str(entry.get("proposed_action", "")).strip()

        missing_fields = []
        if not task_id:
            missing_fields.append("task_id")
        if not rationale:
            missing_fields.append("rationale")
        if not proposed_action:
            missing_fields.append("proposed_action")
        if missing_fields:
            raise ParseError(
                f"Proposal[{idx}] missing required field(s): "
                f"{', '.join(missing_fields)}"
            )

        if proposed_action not in _VALID_ACTIONS:
            raise ParseError(
                f"Proposal[{idx}] invalid proposed_action {proposed_action!r}. "
                f"Must be one of {sorted(_VALID_ACTIONS)}"
            )

        raw_urgency = entry.get("urgency_override")
        urgency_override: Optional[str]
        if raw_urgency is None:
            urgency_override = None
        else:
            urgency_override = str(raw_urgency).strip()
            if urgency_override not in _VALID_URGENCY:
                raise ParseError(
                    f"Proposal[{idx}] invalid urgency_override {urgency_override!r}. "
                    "Must be one of [None, 'P0', 'P1', 'P2', 'P3']"
                )

        suggested_owner = str(entry.get("suggested_owner", "")).strip()

        proposals.append(
            TaskProposal(
                task_id=task_id,
                rationale=rationale,
                urgency_override=urgency_override,
                suggested_owner=suggested_owner,
                proposed_action=proposed_action,
            )
        )

    return proposals


def parse_execution_order(
    proposal: TaskProposal, task: TaskEntry, template_data: dict[str, Any]
) -> dict[str, Any]:
    if not isinstance(template_data, dict):
        raise ParseError("template_data must be a mapping")

    raw_steps = template_data.get("steps")
    if raw_steps is None:
        raise ParseError("template_data missing required field 'steps'")

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d%H%M%S")
    order_id = f"ORD-{proposal.task_id}-{timestamp}"
    if not _ORDER_ID_RE.match(order_id):
        raise ParseError(
            f"Generated order_id {order_id!r} is invalid — check task_id format"
        )

    raw_constraints = template_data.get("constraints") or {}
    if not isinstance(raw_constraints, dict):
        raise ParseError("template_data['constraints'] must be a mapping")

    raw_shadow = template_data.get("shadow")
    if raw_shadow is None:
        shadow = {
            "enabled": False,
            "provider": "codex",
            "receives": "full_task_payload",
        }
    else:
        if not isinstance(raw_shadow, dict):
            raise ParseError("template_data['shadow'] must be a mapping")
        shadow = copy.deepcopy(raw_shadow)

    raw_supervision = template_data.get("supervision")
    if raw_supervision is None:
        supervision = {
            "per_cycle_check": False,
            "batch_id": None,
            "cycle_number": None,
        }
    else:
        if not isinstance(raw_supervision, dict):
            raise ParseError("template_data['supervision'] must be a mapping")
        supervision = copy.deepcopy(raw_supervision)

    constraints: dict[str, Any] = {
        "scope_paths": list(task.scope_paths),
        "worktree": bool(raw_constraints.get("worktree", False)),
        "max_duration_seconds": int(raw_constraints.get("max_duration_seconds", 3600)),
    }
    governance_policy = raw_constraints.get("governance_policy")
    if governance_policy is not None:
        constraints["governance_policy"] = governance_policy

    return {
        "schema_version": "execution_order.v1",
        "order_id": order_id,
        "task_ref": proposal.task_id,
        "created_at": now.isoformat(),
        "steps": copy.deepcopy(raw_steps),
        "constraints": constraints,
        "shadow": shadow,
        "supervision": supervision,
    }
