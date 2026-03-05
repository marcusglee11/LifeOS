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

    return {
        "total_tasks": len(tasks),
        "by_status": by_status,
        "by_priority": by_priority,
        "actionable_count": len(actionable),
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
    }
