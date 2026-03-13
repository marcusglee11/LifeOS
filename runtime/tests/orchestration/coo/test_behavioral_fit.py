from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import patch

import yaml

from runtime.orchestration.coo.commands import cmd_coo_propose, cmd_coo_status
from runtime.orchestration.coo.context import (
    build_propose_context,
    build_report_context,
    build_status_context,
)
from runtime.orchestration.coo.execution_truth import build_execution_truth
from runtime.orchestration.coo.validation import validate_coo_response
from runtime.tests.orchestration.coo.test_commands import (
    _VALID_PROPOSAL_YAML,
    _write_backlog,
    _write_delegation,
    _task,
)


def _write_state(repo_root: Path) -> None:
    path = repo_root / "docs" / "11_admin" / "LIFEOS_STATE.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "# LifeOS State",
                "",
                "**Current Focus:** COO behavioral fit",
                "**Active WIP:** build/openclaw-coo-behavioral-fit",
                "**Last Updated:** 2026-03-12 (rev30)",
            ]
        ),
        encoding="utf-8",
    )


def _write_terminal_packet(
    repo_root: Path,
    *,
    run_id: str,
    outcome: str,
    reason: str,
    status: str = "CLEAN_FAIL",
) -> None:
    path = repo_root / "artifacts" / "terminal" / f"TP_{run_id}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            {
                "run_id": run_id,
                "timestamp": "2026-03-12T00:00:00+00:00",
                "outcome": outcome,
                "reason": reason,
                "status": status,
                "task_ref": "T-001",
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


def _write_manifest(repo_root: Path, entries: list[dict]) -> None:
    path = repo_root / "artifacts" / "manifests" / "run_log.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(entry, sort_keys=True) for entry in entries]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_execution_truth_distinguishes_empty_repo_from_read_errors(tmp_path: Path) -> None:
    payload = build_execution_truth(tmp_path)

    assert payload["truth_reader_ok"] is True
    assert payload["truth_data_present"] is False
    assert payload["truth_read_errors"] == []
    assert payload["dispatch_queue"]["pending_ids"] == []


def test_execution_truth_extracts_blockers_and_conflicts(tmp_path: Path) -> None:
    _write_manifest(
        tmp_path,
        [
            {
                "recorded_at": "2026-03-12T00:00:00+00:00",
                "run_id": "run_001",
                "order_id": "ORD-1",
                "outcome": "BLOCKED",
                "reason": "Missing approval",
            }
        ],
    )
    _write_terminal_packet(
        tmp_path,
        run_id="run_001",
        outcome="PASS",
        reason="done",
        status="SUCCESS",
    )
    lock_path = tmp_path / ".lifeos_run_lock"
    lock_path.write_text("run_001\n", encoding="utf-8")

    payload = build_execution_truth(tmp_path)

    assert payload["truth_data_present"] is True
    assert payload["run_in_flight"] is True
    assert payload["blockers"][0]["reason"] == "Missing approval"
    assert "lock_present_but_latest_terminal_passed" in payload["conflicts"]


def test_execution_truth_is_deterministic(tmp_path: Path) -> None:
    _write_terminal_packet(
        tmp_path,
        run_id="run_002",
        outcome="BLOCKED",
        reason="Missing dependency",
    )

    first = build_execution_truth(tmp_path)
    second = build_execution_truth(tmp_path)

    comparable_first = dict(first)
    comparable_second = dict(second)
    comparable_first.pop("truth_generated_at", None)
    comparable_second.pop("truth_generated_at", None)
    assert comparable_first == comparable_second


def test_contexts_include_canonical_state_and_execution_truth(tmp_path: Path) -> None:
    _write_backlog(tmp_path, [_task("T-001", status="pending")])
    _write_delegation(tmp_path)
    _write_state(tmp_path)
    _write_terminal_packet(
        tmp_path,
        run_id="run_003",
        outcome="BLOCKED",
        reason="Waiting for approval",
    )

    propose = build_propose_context(tmp_path)
    status = build_status_context(tmp_path)
    report = build_report_context(tmp_path)

    assert propose["canonical_state_present"] is True
    assert propose["execution_truth_present"] is True
    assert status["execution_truth"]["blockers"][0]["reason"] == "Waiting for approval"
    assert report["canonical_state"]["active_wip"] == "build/openclaw-coo-behavioral-fit"


def test_behavior_validation_flags_governed_query_deflection() -> None:
    result = validate_coo_response(
        "Where would you like me to look first?",
        mode="propose",
        context={"canonical_state_present": True, "execution_truth": {"blockers": []}},
    )

    assert result.is_valid is False
    assert {item.code for item in result.violations} == {"governed_query_deflection"}


def test_behavior_validation_flags_false_callback_and_ignored_blocker() -> None:
    result = validate_coo_response(
        "I'm on it. I'll report back after I check.",
        mode="direct",
        context={
            "canonical_state_present": False,
            "execution_truth": {
                "blockers": [{"run_id": "run_004", "reason": "Gateway down", "source": "tp"}]
            },
        },
    )

    assert result.is_valid is False
    assert {item.code for item in result.violations} == {
        "false_callback_promise",
        "ignored_blocker_truth",
    }


def test_coo_propose_fails_closed_on_behavioral_violation(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)
    _write_state(tmp_path)

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value="I'm on it. I'll report back.",
    ):
        rc = cmd_coo_propose(argparse.Namespace(json=False), tmp_path)

    assert rc == 1
    assert "behavioral validation failed" in capsys.readouterr().err


def test_coo_status_surfaces_authoritative_state(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-001", status="pending", priority="P0")])
    _write_state(tmp_path)
    _write_terminal_packet(
        tmp_path,
        run_id="run_005",
        outcome="BLOCKED",
        reason="Blocked on policy hash mismatch",
    )

    rc = cmd_coo_status(argparse.Namespace(json=False), tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "canonical current focus: COO behavioral fit" in out
    assert "execution truth:" in out


def test_coo_propose_accepts_grounded_output_when_blocker_is_mentioned(tmp_path: Path, capsys) -> None:
    _write_backlog(tmp_path, [_task("T-101", status="pending", priority="P1")])
    _write_delegation(tmp_path)
    _write_state(tmp_path)
    _write_terminal_packet(
        tmp_path,
        run_id="run_006",
        outcome="BLOCKED",
        reason="Dependency pending",
    )

    grounded_yaml = _VALID_PROPOSAL_YAML.replace(
        "Highest impact first",
        "Highest impact first",
    )
    grounded_yaml = grounded_yaml.replace(
        "P1 priority, highest actionable.",
        "Defer lower-confidence work while Dependency pending remains blocked.",
    )

    with patch(
        "runtime.orchestration.coo.commands.invoke_coo_reasoning",
        return_value=grounded_yaml,
    ):
        rc = cmd_coo_propose(argparse.Namespace(json=False), tmp_path)

    assert rc == 0
    assert "schema_version: task_proposal.v1" in capsys.readouterr().out
