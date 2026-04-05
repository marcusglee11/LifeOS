"""Deterministic COO sync-check drift detection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

import yaml

_GOVERNANCE_ROOT = Path("docs") / "01_governance"


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return payload


def _load_approval_ref_validator() -> Callable[[str, Path], str | None] | None:
    try:
        from scripts import run_ops_certification
    except Exception:
        return None

    validator = getattr(run_ops_certification, "_validate_approval_ref", None)
    if not callable(validator):
        return None

    def _wrapped(approval_ref: str, repo_root: Path) -> str | None:
        return validator(approval_ref, repo_root=repo_root)

    return _wrapped


def _fallback_validate_approval_ref(approval_ref: str, repo_root: Path) -> str | None:
    """Mirror scripts/run_ops_certification.py when its private helper is unavailable."""
    ruling_path = (repo_root / approval_ref).resolve()
    gov_root = (repo_root / _GOVERNANCE_ROOT).resolve()
    if not ruling_path.is_relative_to(gov_root):
        return f"approval_ref {approval_ref!r} is outside docs/01_governance/"
    if not ruling_path.is_file():
        return f"approval_ref {approval_ref!r} does not exist"
    text = ruling_path.read_text(encoding="utf-8")
    if "**Decision**: RATIFIED" not in text and "**Decision**: APPROVED" not in text:
        return (
            f"approval_ref {approval_ref!r} does not contain a structured approval marker "
            "(**Decision**: RATIFIED or **Decision**: APPROVED)"
        )
    return None


def _approval_ref_error(approval_ref: str, repo_root: Path) -> str | None:
    validator = _load_approval_ref_validator()
    if validator is not None:
        return validator(approval_ref, repo_root)
    return _fallback_validate_approval_ref(approval_ref, repo_root)


def check_task_status_gaps(tasks: list[dict[str, Any]]) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    for task in tasks:
        task_id = str(task.get("id", "")).strip() or "<unknown>"
        status = str(task.get("status", "")).strip()
        completed_at = task.get("completed_at")
        if completed_at and status != "completed":
            gaps.append(
                {
                    "task_id": task_id,
                    "issue": f"completed_at is set but status is {status!r}",
                }
            )
        elif status == "completed" and not completed_at:
            gaps.append(
                {
                    "task_id": task_id,
                    "issue": "status is 'completed' but completed_at is null",
                }
            )
    return gaps


def check_lane_governance(lanes_payload: dict[str, Any], repo_root: Path) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    for lane in lanes_payload.get("lanes", []):
        if not isinstance(lane, dict):
            continue
        lane_id = str(lane.get("lane_id", "")).strip() or "<unknown>"
        if str(lane.get("status", "")).strip() != "ratified":
            continue
        approval_ref = str(lane.get("approval_ref") or "").strip()
        if not approval_ref:
            gaps.append({"lane_id": lane_id, "issue": "approval_ref is empty"})
            continue
        error = _approval_ref_error(approval_ref, repo_root)
        if error is not None:
            gaps.append({"lane_id": lane_id, "issue": error})
    return gaps


def run_sync_check(repo_root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "drift_found": False,
        "task_status_gaps": [],
        "lane_governance_drift": [],
    }

    backlog_path = repo_root / "config" / "tasks" / "backlog.yaml"
    if backlog_path.is_file():
        backlog_payload = _load_yaml(backlog_path)
        tasks = backlog_payload.get("tasks", [])
        if isinstance(tasks, list):
            result["task_status_gaps"] = check_task_status_gaps(tasks)

    lanes_path = repo_root / "config" / "ops" / "lanes.yaml"
    if lanes_path.is_file():
        lanes_payload = _load_yaml(lanes_path)
        result["lane_governance_drift"] = check_lane_governance(lanes_payload, repo_root)

    result["drift_found"] = bool(
        result["task_status_gaps"] or result["lane_governance_drift"]
    )
    return result


def render_sync_check(result: dict[str, Any], as_json: bool) -> str:
    if as_json:
        return json.dumps(result, indent=2, sort_keys=True)

    if not result["drift_found"]:
        return "sync_check: OK - no drift detected"

    lines = ["sync_check: DRIFT DETECTED"]
    for item in result["task_status_gaps"]:
        lines.append(f"  [task-gap] {item['task_id']}: {item['issue']}")
    for item in result["lane_governance_drift"]:
        lines.append(f"  [lane-gap] {item['lane_id']}: {item['issue']}")
    return "\n".join(lines)
