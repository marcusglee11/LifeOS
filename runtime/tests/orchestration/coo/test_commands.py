"""Tests for COO CLI command handlers."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from runtime.orchestration.coo.backlog import BACKLOG_SCHEMA_VERSION
from runtime.orchestration.coo.commands import (
    cmd_coo_approve,
    cmd_coo_propose,
    cmd_coo_report,
    cmd_coo_status,
)
from runtime.orchestration.dispatch.order import parse_order


def _task(
    task_id: str,
    *,
    status: str = "pending",
    priority: str = "P1",
    task_type: str = "build",
    requires_approval: bool = True,
) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    return {
        "id": task_id,
        "title": f"Task {task_id}",
        "description": "desc",
        "dod": "done",
        "priority": priority,
        "risk": "low",
        "scope_paths": ["runtime/"],
        "status": status,
        "requires_approval": requires_approval,
        "owner": "codex",
        "evidence": "",
        "task_type": task_type,
        "tags": [],
        "objective_ref": "bootstrap",
        "created_at": now_iso,
        "completed_at": None,
    }


def _write_backlog(repo_root: Path, tasks: list[dict]) -> None:
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


def _write_delegation(repo_root: Path) -> None:
    delegation_path = repo_root / "config" / "governance" / "delegation_envelope.yaml"
    delegation_path.parent.mkdir(parents=True, exist_ok=True)
    delegation_path.write_text(
        yaml.dump({"schema_version": "delegation_envelope.v1", "trust_tier": "burn-in"}),
        encoding="utf-8",
    )


def _write_template(repo_root: Path, template_name: str = "build") -> None:
    template_dir = repo_root / "config" / "tasks" / "order_templates"
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / f"{template_name}.yaml").write_text(
        yaml.dump(
            {
                "schema_version": "order_template.v1",
                "template_name": template_name,
                "description": f"{template_name} template",
                "steps": [{"name": "build", "role": "builder"}],
                "constraints": {
                    "worktree": True,
                    "max_duration_seconds": 900,
                    "governance_policy": None,
                },
                "shadow": {
                    "enabled": False,
                    "provider": "codex",
                    "receives": "full_task_payload",
                },
                "supervision": {"per_cycle_check": False},
            },
            default_flow_style=False,
            sort_keys=False,
        ),
        encoding="utf-8",
    )


def test_coo_status_returns_zero(tmp_path: Path, capsys) -> None:
    _write_backlog(
        tmp_path,
        [
            _task("T-001", status="pending", priority="P0"),
            _task("T-002", status="in_progress", priority="P1"),
            _task("T-003", status="completed", priority="P2"),
            _task("T-004", status="blocked", priority="P3"),
        ],
    )

    rc = cmd_coo_status(argparse.Namespace(json=False), tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "backlog: 4 tasks" in out
    assert "pending:     1" in out
    assert "in_progress: 1" in out
    assert "completed:   1" in out
    assert "blocked:     1" in out
    assert "actionable (2):" in out


def test_coo_status_json_output(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-001", status="pending", priority="P2")])

    rc = cmd_coo_status(argparse.Namespace(json=True), tmp_path)

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["total_tasks"] == 1
    assert payload["by_status"]["pending"] == 1
    assert payload["actionable_count"] == 1


def test_coo_propose_prints_context(tmp_path: Path, capsys) -> None:
    _write_backlog(
        tmp_path,
        [
            _task("T-101", status="pending", priority="P1"),
            _task("T-102", status="completed", priority="P0"),
        ],
    )
    _write_delegation(tmp_path)

    rc = cmd_coo_propose(argparse.Namespace(json=True), tmp_path)

    assert rc == 0
    out = capsys.readouterr().out.strip().splitlines()
    assert out[-1] == "# COO invocation: not yet wired (Step 5)"
    payload = json.loads("\n".join(out[:-1]))
    assert payload["actionable_tasks"][0]["id"] == "T-101"
    assert payload["delegation_envelope"]["schema_version"] == "delegation_envelope.v1"


def test_coo_approve_writes_order_to_inbox(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-003", status="pending", task_type="build")])
    _write_template(tmp_path, "build")

    rc = cmd_coo_approve(argparse.Namespace(task_ids=["T-003"], json=False), tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "approved: T-003 -> ORD-T-003-" in out

    inbox_dir = tmp_path / "artifacts" / "dispatch" / "inbox"
    files = list(inbox_dir.glob("ORD-T-003-*.yaml"))
    assert len(files) == 1

    raw = yaml.safe_load(files[0].read_text(encoding="utf-8"))
    assert raw["task_ref"] == "T-003"
    assert parse_order(raw).order_id == raw["order_id"]


def test_coo_approve_unknown_task_returns_one(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-001", status="pending", task_type="build")])

    rc = cmd_coo_approve(argparse.Namespace(task_ids=["T-X"], json=False), tmp_path)

    assert rc == 1
    captured = capsys.readouterr()
    assert "task not found: T-X" in captured.err


def test_coo_approve_creates_inbox_dir_if_missing(tmp_path: Path) -> None:
    _write_backlog(tmp_path, [_task("T-005", status="pending", task_type="build")])
    _write_template(tmp_path, "build")

    inbox_dir = tmp_path / "artifacts" / "dispatch" / "inbox"
    assert not inbox_dir.exists()

    rc = cmd_coo_approve(argparse.Namespace(task_ids=["T-005"], json=False), tmp_path)

    assert rc == 0
    assert inbox_dir.exists()


def test_coo_report_returns_json(tmp_path: Path, capsys) -> None:
    _write_backlog(
        tmp_path,
        [
            _task("T-201", status="pending"),
            _task("T-202", status="completed"),
        ],
    )
    _write_delegation(tmp_path)

    rc = cmd_coo_report(argparse.Namespace(), tmp_path)

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["all_tasks"]) == 2
    assert payload["delegation_envelope"]["schema_version"] == "delegation_envelope.v1"
