"""
Context builders for COO proposal/status/report flows.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from runtime.orchestration.coo.backlog import TaskEntry, filter_actionable, load_backlog


_BACKLOG_RELATIVE_PATH = Path("config/tasks/backlog.yaml")
_DELEGATION_RELATIVE_PATH = Path("config/governance/delegation_envelope.yaml")
_BRIEF_RELATIVE_PATH = Path("artifacts/coo/brief.md")
_REPO_MAP_RELATIVE_PATH = Path(".context/REPO_MAP.md")


def _load_repo_map(repo_root: Path) -> str:
    """Load REPO_MAP.md for LLM context injection (fail-soft)."""
    path = repo_root / _REPO_MAP_RELATIVE_PATH
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


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

_PROPOSE_FORMAT_INSTRUCTION = (
    "REQUIRED OUTPUT FORMAT.\n"
    "Your entire response MUST be ONLY valid YAML. No prose. No markdown fences. "
    "No explanation before or after the YAML block.\n\n"
    "Use exactly one of these two schemas:\n\n"
    "--- If tasks exist ---\n"
    + _PROPOSE_OUTPUT_SCHEMA_EXAMPLE
    + "\n--- If nothing to propose ---\n"
    + _NTP_OUTPUT_SCHEMA_EXAMPLE
    + "\nRules:\n"
    "- schema_version: exactly 'task_proposal.v1' or 'nothing_to_propose.v1'\n"
    "- proposed_action: dispatch | defer | escalate\n"
    "- urgency_override: null or P0|P1|P2|P3\n"
    "- Sub-keys of each proposals item MUST be indented 2 spaces under the '-' marker.\n"
    "- Do NOT add any text before or after the YAML.\n"
)


def build_propose_context(repo_root: Path) -> dict[str, Any]:
    backlog_path = repo_root / _BACKLOG_RELATIVE_PATH
    delegation_path = repo_root / _DELEGATION_RELATIVE_PATH
    brief_path = repo_root / _BRIEF_RELATIVE_PATH

    tasks = load_backlog(backlog_path)
    actionable = filter_actionable(tasks)
    delegation = _load_yaml_mapping(delegation_path)

    return {
        "actionable_tasks": [_task_to_dict(task) for task in actionable],
        "delegation_envelope": delegation,
        "backlog_path": str(backlog_path),
        "brief": _read_optional_brief(brief_path),
        "generated_at": _now_iso(),
        "output_format_instruction": _PROPOSE_FORMAT_INSTRUCTION,
        "repo_map": _load_repo_map(repo_root),
    }


def _collect_dispatch_state(repo_root: Path) -> dict[str, Any]:
    """Read dispatch dirs to build a summary of current order state."""
    import yaml as _yaml

    dispatch_base = repo_root / "artifacts" / "dispatch"
    inbox_dir = dispatch_base / "inbox"
    active_dir = dispatch_base / "active"
    completed_dir = dispatch_base / "completed"

    inbox_orders = [
        f.stem for f in inbox_dir.glob("*.yaml") if not f.name.endswith(".tmp")
    ] if inbox_dir.exists() else []

    active_orders = [
        f.stem for f in active_dir.glob("*.yaml") if not f.name.endswith(".tmp")
    ] if active_dir.exists() else []

    completed_success = 0
    completed_fail = 0
    if completed_dir.exists():
        for f in completed_dir.glob("*.yaml"):
            if f.name.endswith(".tmp"):
                continue
            try:
                raw = _yaml.safe_load(f.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    dr = raw.get("dispatch_result", {})
                    if isinstance(dr, dict):
                        outcome = dr.get("outcome", "")
                        if outcome == "SUCCESS":
                            completed_success += 1
                        elif outcome == "CLEAN_FAIL":
                            completed_fail += 1
            except Exception:
                pass

    escalation_count = 0
    try:
        from runtime.orchestration.ceo_queue import CEOQueue
        queue = CEOQueue(db_path=repo_root / "artifacts" / "queue" / "escalations.db")
        escalation_count = len(queue.list_pending())
    except Exception:
        pass

    return {
        "inbox": len(inbox_orders),
        "inbox_orders": inbox_orders,
        "active": len(active_orders),
        "active_orders": active_orders,
        "completed_total": completed_success + completed_fail,
        "completed_success": completed_success,
        "completed_fail": completed_fail,
        "escalations_pending": escalation_count,
    }


def build_status_context(repo_root: Path) -> dict[str, Any]:
    backlog_path = repo_root / _BACKLOG_RELATIVE_PATH
    tasks = load_backlog(backlog_path)
    actionable = filter_actionable(tasks)

    by_status = {"pending": 0, "in_progress": 0, "completed": 0, "blocked": 0}
    for task in tasks:
        by_status[task.status] = by_status.get(task.status, 0) + 1

    by_priority = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for task in actionable:
        by_priority[task.priority] = by_priority.get(task.priority, 0) + 1

    dispatch_state = _collect_dispatch_state(repo_root)

    return {
        "total_tasks": len(tasks),
        "by_status": by_status,
        "by_priority": by_priority,
        "actionable_count": len(actionable),
        "dispatch": dispatch_state,
        "generated_at": _now_iso(),
    }


def build_report_context(repo_root: Path) -> dict[str, Any]:
    backlog_path = repo_root / _BACKLOG_RELATIVE_PATH
    delegation_path = repo_root / _DELEGATION_RELATIVE_PATH

    tasks = load_backlog(backlog_path)
    delegation = _load_yaml_mapping(delegation_path)

    return {
        "all_tasks": [_task_to_dict(task) for task in tasks],
        "delegation_envelope": delegation,
        "generated_at": _now_iso(),
        "repo_map": _load_repo_map(repo_root),
    }
