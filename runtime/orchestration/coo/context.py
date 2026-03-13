"""
Context builders for COO proposal/status/report flows.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any

import yaml

from runtime.orchestration.coo.backlog import TaskEntry, filter_actionable, load_backlog
from runtime.orchestration.coo.execution_truth import build_execution_truth


_BACKLOG_RELATIVE_PATH = Path("config/tasks/backlog.yaml")
_DELEGATION_RELATIVE_PATH = Path("config/governance/delegation_envelope.yaml")
_BRIEF_RELATIVE_PATH = Path("artifacts/coo/brief.md")
_CANONICAL_STATE_RELATIVE_PATH = Path("docs/11_admin/LIFEOS_STATE.md")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task_to_dict(task: TaskEntry) -> dict[str, Any]:
    return asdict(task)


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(path)

    with open(path, "r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)

    if not isinstance(raw, dict):
        raise ValueError(
            f"Expected YAML mapping in {path}, got {type(raw).__name__}"
        )
    return raw


def _read_optional_brief(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _extract_marker(content: str, label: str) -> str:
    pattern = re.compile(rf"^\*\*{re.escape(label)}:\*\*\s*(.+)$", re.MULTILINE)
    match = pattern.search(content)
    return match.group(1).strip() if match else ""


def _read_canonical_state(repo_root: Path) -> tuple[dict[str, Any], bool]:
    path = repo_root / _CANONICAL_STATE_RELATIVE_PATH
    if not path.exists():
        return (
            {
                "path": str(_CANONICAL_STATE_RELATIVE_PATH),
                "reason": "missing",
                "content": "",
            },
            False,
        )

    content = path.read_text(encoding="utf-8")
    return (
        {
            "path": str(_CANONICAL_STATE_RELATIVE_PATH),
            "content": content,
            "current_focus": _extract_marker(content, "Current Focus"),
            "active_wip": _extract_marker(content, "Active WIP"),
            "last_updated": _extract_marker(content, "Last Updated"),
        },
        True,
    )


_PROPOSE_OUTPUT_SCHEMA_EXAMPLE = """\
schema_version: task_proposal.v1
proposals:
  - task_id: T-001
    rationale: "Highest priority with all deps met."
    proposed_action: dispatch
    urgency_override: null
    suggested_owner: codex
  - task_id: T-002
    rationale: "Next priority; defer until T-001 complete."
    proposed_action: defer
    urgency_override: null
    suggested_owner: ""
"""

_NTP_OUTPUT_SCHEMA_EXAMPLE = """\
schema_version: nothing_to_propose.v1
reason: "No pending actionable tasks after policy checks."
recommended_follow_up: "Wait for blocked tasks to unblock."
"""

_PROPOSE_OUTPUT_SCHEMA = {
    "description": (
        "Required output format for propose mode. "
        "Output MUST be valid YAML with exactly this structure. "
        "Each item in 'proposals' MUST be indented by 2 spaces under the '-' marker. "
        "Do NOT use a 'task:' key. "
        "Do NOT use markdown code fences."
    ),
    "task_proposal_example": _PROPOSE_OUTPUT_SCHEMA_EXAMPLE,
    "nothing_to_propose_example": _NTP_OUTPUT_SCHEMA_EXAMPLE,
    "rules": {
        "schema_version": "must be exactly 'task_proposal.v1' or 'nothing_to_propose.v1'",
        "proposed_action": "must be one of: dispatch, defer, escalate",
        "urgency_override": "null or one of: P0, P1, P2, P3",
        "suggested_owner": "codex, claude_code, gemini, or empty string",
        "indentation": "sub-keys of each proposals list item must be indented 4 spaces (2 for '-' + 2 for content)",
    },
}


def build_propose_context(repo_root: Path) -> dict[str, Any]:
    backlog_path = repo_root / _BACKLOG_RELATIVE_PATH
    delegation_path = repo_root / _DELEGATION_RELATIVE_PATH
    brief_path = repo_root / _BRIEF_RELATIVE_PATH

    tasks = load_backlog(backlog_path)
    actionable = filter_actionable(tasks)
    delegation = _load_yaml_mapping(delegation_path)
    canonical_state, canonical_state_present = _read_canonical_state(repo_root)
    execution_truth = build_execution_truth(repo_root)

    return {
        "actionable_tasks": [_task_to_dict(task) for task in actionable],
        "delegation_envelope": delegation,
        "backlog_path": str(backlog_path),
        "brief": _read_optional_brief(brief_path),
        "canonical_state": canonical_state,
        "canonical_state_present": canonical_state_present,
        "execution_truth": execution_truth,
        "execution_truth_present": bool(execution_truth.get("truth_data_present")),
        "generated_at": _now_iso(),
        "output_schema": _PROPOSE_OUTPUT_SCHEMA,
    }


def build_status_context(repo_root: Path) -> dict[str, Any]:
    backlog_path = repo_root / _BACKLOG_RELATIVE_PATH
    tasks = load_backlog(backlog_path)
    actionable = filter_actionable(tasks)
    canonical_state, canonical_state_present = _read_canonical_state(repo_root)
    execution_truth = build_execution_truth(repo_root)

    by_status = {"pending": 0, "in_progress": 0, "completed": 0, "blocked": 0}
    for task in tasks:
        by_status[task.status] = by_status.get(task.status, 0) + 1

    by_priority = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for task in actionable:
        by_priority[task.priority] = by_priority.get(task.priority, 0) + 1

    return {
        "total_tasks": len(tasks),
        "by_status": by_status,
        "by_priority": by_priority,
        "actionable_count": len(actionable),
        "canonical_state": canonical_state,
        "canonical_state_present": canonical_state_present,
        "execution_truth": execution_truth,
        "execution_truth_present": bool(execution_truth.get("truth_data_present")),
        "generated_at": _now_iso(),
    }


def build_report_context(repo_root: Path) -> dict[str, Any]:
    backlog_path = repo_root / _BACKLOG_RELATIVE_PATH
    delegation_path = repo_root / _DELEGATION_RELATIVE_PATH

    tasks = load_backlog(backlog_path)
    delegation = _load_yaml_mapping(delegation_path)
    canonical_state, canonical_state_present = _read_canonical_state(repo_root)
    execution_truth = build_execution_truth(repo_root)

    return {
        "all_tasks": [_task_to_dict(task) for task in tasks],
        "delegation_envelope": delegation,
        "canonical_state": canonical_state,
        "canonical_state_present": canonical_state_present,
        "execution_truth": execution_truth,
        "execution_truth_present": bool(execution_truth.get("truth_data_present")),
        "generated_at": _now_iso(),
    }
