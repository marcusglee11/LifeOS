"""Tests for COO context builders."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from runtime.orchestration.coo.backlog import BACKLOG_SCHEMA_VERSION
from runtime.orchestration.coo.context import (
    build_propose_context,
    build_report_context,
    build_status_context,
)

import subprocess as _subprocess


def _find_repo_root() -> Path:
    result = _subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=False,
        cwd=str(Path(__file__).parent),
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return Path(__file__).resolve().parents[4]


REPO_ROOT = _find_repo_root()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _task(task_id: str, priority: str, status: str) -> dict:
    return {
        "id": task_id,
        "title": f"Task {task_id}",
        "description": "desc",
        "dod": "done",
        "priority": priority,
        "risk": "low",
        "scope_paths": ["runtime/"],
        "status": status,
        "requires_approval": False,
        "owner": "codex",
        "evidence": "",
        "task_type": "build",
        "tags": [],
        "objective_ref": "bootstrap",
        "created_at": _now_iso(),
        "completed_at": None,
    }


def _write_backlog(repo_root: Path, tasks: list[dict]) -> Path:
    backlog_path = repo_root / "config" / "tasks" / "backlog.yaml"
    backlog_path.parent.mkdir(parents=True, exist_ok=True)
    backlog_path.write_text(
        yaml.dump(
            {"schema_version": BACKLOG_SCHEMA_VERSION, "tasks": tasks},
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return backlog_path


def _write_delegation(repo_root: Path, payload: dict | None = None) -> Path:
    delegation_path = repo_root / "config" / "governance" / "delegation_envelope.yaml"
    delegation_path.parent.mkdir(parents=True, exist_ok=True)
    delegation_path.write_text(
        yaml.dump(payload or {"schema_version": "delegation_envelope.v1"}),
        encoding="utf-8",
    )
    return delegation_path


def test_build_propose_context_returns_actionable_tasks(tmp_path: Path) -> None:
    tasks = [
        _task("T-001", "P2", "pending"),
        _task("T-002", "P0", "in_progress"),
        _task("T-003", "P1", "completed"),
    ]
    backlog_path = _write_backlog(tmp_path, tasks)
    delegation = {"schema_version": "delegation_envelope.v1", "trust_tier": "burn-in"}
    _write_delegation(tmp_path, delegation)
    brief_path = tmp_path / "artifacts" / "coo" / "brief.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text("COO brief content", encoding="utf-8")

    context = build_propose_context(tmp_path)

    assert context["backlog_path"] == str(backlog_path)
    assert [task["id"] for task in context["actionable_tasks"]] == ["T-002", "T-001"]
    assert context["delegation_envelope"] == delegation
    assert context["brief"] == "COO brief content"
    assert context["audience"] == "runtime_machine"
    assert context["interaction_style"] == "machine_packet_only"
    datetime.fromisoformat(context["generated_at"])


def test_build_propose_context_missing_backlog_raises(tmp_path: Path) -> None:
    _write_delegation(tmp_path)

    with pytest.raises(FileNotFoundError):
        build_propose_context(tmp_path)


def test_build_propose_context_missing_delegation_raises(tmp_path: Path) -> None:
    _write_backlog(tmp_path, [_task("T-001", "P1", "pending")])

    with pytest.raises(FileNotFoundError):
        build_propose_context(tmp_path)


def test_build_propose_context_missing_brief_returns_empty_string(tmp_path: Path) -> None:
    _write_backlog(tmp_path, [_task("T-001", "P1", "pending")])
    _write_delegation(tmp_path)

    context = build_propose_context(tmp_path)

    assert context["brief"] == ""


def test_build_status_context_counts(tmp_path: Path) -> None:
    tasks = [
        _task("T-001", "P0", "pending"),
        _task("T-002", "P1", "completed"),
        _task("T-003", "P2", "in_progress"),
        _task("T-004", "P3", "blocked"),
    ]
    _write_backlog(tmp_path, tasks)

    context = build_status_context(tmp_path)

    assert context["total_tasks"] == 4
    assert context["by_status"] == {
        "pending": 1,
        "in_progress": 1,
        "completed": 1,
        "blocked": 1,
    }
    assert context["by_priority"] == {"P0": 1, "P1": 0, "P2": 1, "P3": 0}
    assert context["actionable_count"] == 2
    datetime.fromisoformat(context["generated_at"])


def test_build_report_context_returns_all_tasks(tmp_path: Path) -> None:
    tasks = [
        _task("T-001", "P0", "pending"),
        _task("T-002", "P1", "completed"),
    ]
    _write_backlog(tmp_path, tasks)
    delegation = {"schema_version": "delegation_envelope.v1", "active_levels": ["L0", "L3"]}
    _write_delegation(tmp_path, delegation)

    context = build_report_context(tmp_path)

    assert len(context["all_tasks"]) == 2
    assert {task["id"] for task in context["all_tasks"]} == {"T-001", "T-002"}
    assert context["delegation_envelope"] == delegation
    assert context["audience"] == "human_operator"
    assert context["interaction_style"] == "natural_language"
    datetime.fromisoformat(context["generated_at"])


# ---------------------------------------------------------------------------
# Repo map injection tests
# ---------------------------------------------------------------------------

def _write_repo_map(repo_root: Path, content: str) -> Path:
    map_path = repo_root / ".context" / "REPO_MAP.md"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(content, encoding="utf-8")
    return map_path


def test_propose_context_includes_repo_map(tmp_path: Path) -> None:
    _write_backlog(tmp_path, [_task("T-001", "P1", "pending")])
    _write_delegation(tmp_path)
    _write_repo_map(tmp_path, "# Repo Map\nmodule: runtime/")

    context = build_propose_context(tmp_path)

    assert "repo_map" in context
    assert "# Repo Map" in context["repo_map"]


def test_report_context_includes_repo_map(tmp_path: Path) -> None:
    _write_backlog(tmp_path, [_task("T-001", "P1", "pending")])
    _write_delegation(tmp_path)
    _write_repo_map(tmp_path, "# Repo Map\nmodule: runtime/")

    context = build_report_context(tmp_path)

    assert "repo_map" in context
    assert "# Repo Map" in context["repo_map"]


def test_propose_context_repo_map_missing_graceful(tmp_path: Path) -> None:
    _write_backlog(tmp_path, [_task("T-001", "P1", "pending")])
    _write_delegation(tmp_path)
    # No repo map written

    context = build_propose_context(tmp_path)

    assert "repo_map" in context
    assert context["repo_map"] == ""


def test_propose_context_output_format_instruction_key(tmp_path: Path) -> None:
    """output_format_instruction replaces output_schema in propose context."""
    _write_backlog(tmp_path, [_task("T-001", "P1", "pending")])
    _write_delegation(tmp_path)

    context = build_propose_context(tmp_path)

    assert "output_format_instruction" in context
    assert "output_schema" not in context
    assert context["audience"] == "runtime_machine"
    assert "REQUIRED OUTPUT FORMAT" in context["output_format_instruction"]
    assert "RUNTIME MACHINE-OUTPUT INVOCATION" in context["output_format_instruction"]


# ---------------------------------------------------------------------------
# Fix 1 regression: escalation count uses get_pending() (not list_pending)
# ---------------------------------------------------------------------------

def test_build_status_context_escalation_count_with_pending(tmp_path: Path) -> None:
    """Escalation count reflects real pending entries — tests the get_pending() fix at source."""
    from runtime.orchestration.ceo_queue import CEOQueue, EscalationEntry, EscalationType

    _write_backlog(tmp_path, [_task("T-001", "P1", "pending")])

    db_path = tmp_path / "artifacts" / "queue" / "escalations.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    queue = CEOQueue(db_path=db_path)
    queue.add_escalation(
        EscalationEntry(
            type=EscalationType.AMBIGUOUS_TASK,
            context={"summary": "test escalation"},
            run_id="fix1-regression-test",
        )
    )

    context = build_status_context(tmp_path)

    assert context["dispatch"]["escalations_pending"] == 1


def test_build_status_context_escalation_count_zero_when_empty(tmp_path: Path) -> None:
    """Escalation count is 0 when no pending entries exist."""
    _write_backlog(tmp_path, [_task("T-001", "P1", "pending")])

    context = build_status_context(tmp_path)

    assert context["dispatch"]["escalations_pending"] == 0
