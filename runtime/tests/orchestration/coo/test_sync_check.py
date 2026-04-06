"""Tests for COO sync-check drift detection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from runtime.orchestration.coo.commands import cmd_coo_sync_check
from runtime.orchestration.coo.sync_check import (
    check_lane_governance,
    check_task_status_gaps,
    run_sync_check,
)


def _write_yaml(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(payload, default_flow_style=False, sort_keys=False),
        encoding="utf-8",
    )


def _write_backlog(repo_root: Path, tasks: list[dict]) -> None:
    _write_yaml(
        repo_root / "config" / "tasks" / "backlog.yaml",
        {"schema_version": "backlog.v1", "tasks": tasks},
    )


def _write_lanes(repo_root: Path, lanes: list[dict]) -> None:
    _write_yaml(
        repo_root / "config" / "ops" / "lanes.yaml",
        {"schema_version": "ops_lanes.v1", "lanes": lanes},
    )


def _write_ruling(repo_root: Path, relative_path: str, decision: str = "RATIFIED") -> None:
    ruling_path = repo_root / relative_path
    ruling_path.parent.mkdir(parents=True, exist_ok=True)
    ruling_path.write_text(f"# Ruling\n\n**Decision**: {decision}\n", encoding="utf-8")


def test_check_task_status_gaps_detects_completed_at_with_pending_status() -> None:
    gaps = check_task_status_gaps(
        [{"id": "T-001", "status": "pending", "completed_at": "2026-04-01T00:00:00Z"}]
    )
    assert gaps == [
        {"task_id": "T-001", "issue": "completed_at is set but status is 'pending'"}
    ]


def test_check_task_status_gaps_detects_completed_status_without_completed_at() -> None:
    gaps = check_task_status_gaps([{"id": "T-001", "status": "completed", "completed_at": None}])
    assert gaps == [{"task_id": "T-001", "issue": "status is 'completed' but completed_at is null"}]


def test_check_lane_governance_detects_empty_approval_ref(tmp_path: Path) -> None:
    gaps = check_lane_governance(
        {"lanes": [{"lane_id": "workspace_mutation_v1", "status": "ratified", "approval_ref": ""}]},
        tmp_path,
    )
    assert gaps == [{"lane_id": "workspace_mutation_v1", "issue": "approval_ref is empty"}]


def test_check_lane_governance_detects_invalid_approval_marker(tmp_path: Path) -> None:
    approval_ref = "docs/01_governance/invalid.md"
    ruling_path = tmp_path / approval_ref
    ruling_path.parent.mkdir(parents=True, exist_ok=True)
    ruling_path.write_text("# Ruling\n\nNo marker here.\n", encoding="utf-8")

    gaps = check_lane_governance(
        {"lanes": [{"lane_id": "workspace_mutation_v1", "status": "ratified", "approval_ref": approval_ref}]},
        tmp_path,
    )
    assert len(gaps) == 1
    assert gaps[0]["lane_id"] == "workspace_mutation_v1"
    assert "structured approval marker" in gaps[0]["issue"]


def test_check_lane_governance_ignores_pending_lanes(tmp_path: Path) -> None:
    gaps = check_lane_governance(
        {
            "lanes": [
                {
                    "lane_id": "workspace_mutation_v1",
                    "status": "ratification_pending",
                    "approval_ref": "",
                }
            ]
        },
        tmp_path,
    )
    assert gaps == []


def test_run_sync_check_returns_no_drift_for_clean_repo(tmp_path: Path) -> None:
    _write_backlog(
        tmp_path,
        [
            {
                "id": "T-001",
                "title": "Task T-001",
                "description": "desc",
                "dod": "done",
                "priority": "P1",
                "risk": "low",
                "scope_paths": ["runtime/orchestration/coo/"],
                "status": "completed",
                "requires_approval": False,
                "owner": "codex",
                "evidence": "",
                "task_type": "build",
                "tags": [],
                "objective_ref": "bootstrap",
                "created_at": "2026-04-05T00:00:00Z",
                "completed_at": "2026-04-05T01:00:00Z",
            }
        ],
    )
    _write_ruling(tmp_path, "docs/01_governance/ratified.md")
    _write_lanes(
        tmp_path,
        [
            {
                "lane_id": "workspace_mutation_v1",
                "status": "ratified",
                "approval_ref": "docs/01_governance/ratified.md",
            }
        ],
    )

    result = run_sync_check(tmp_path)
    assert result == {
        "drift_found": False,
        "task_status_gaps": [],
        "lane_governance_drift": [],
    }


def test_cmd_coo_sync_check_json_output_reports_drift(tmp_path: Path, capsys) -> None:
    _write_backlog(
        tmp_path,
        [
            {
                "id": "T-001",
                "title": "Task T-001",
                "description": "desc",
                "dod": "done",
                "priority": "P1",
                "risk": "low",
                "scope_paths": ["runtime/orchestration/coo/"],
                "status": "pending",
                "requires_approval": False,
                "owner": "codex",
                "evidence": "",
                "task_type": "build",
                "tags": [],
                "objective_ref": "bootstrap",
                "created_at": "2026-04-05T00:00:00Z",
                "completed_at": "2026-04-05T01:00:00Z",
            }
        ],
    )

    rc = cmd_coo_sync_check(argparse.Namespace(json=True), tmp_path)

    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["drift_found"] is True
    assert payload["task_status_gaps"][0]["task_id"] == "T-001"


def test_approval_ref_validation_path_accepts_approved_marker(tmp_path: Path) -> None:
    _write_ruling(tmp_path, "docs/01_governance/approved.md", decision="APPROVED")

    gaps = check_lane_governance(
        {"lanes": [{"lane_id": "lane-v1", "status": "ratified", "approval_ref": "docs/01_governance/approved.md"}]},
        tmp_path,
    )
    assert gaps == []
