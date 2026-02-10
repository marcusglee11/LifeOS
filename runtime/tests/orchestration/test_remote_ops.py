from __future__ import annotations

from datetime import datetime, timezone
import json
import subprocess
from pathlib import Path

from runtime.orchestration.remote_ops import load_queue, try_delete_remote_branch


def _fixed_now() -> datetime:
    return datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc)


def test_dns_failure_is_deferred_and_non_blocking(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "ws"
    workspace_root.mkdir(parents=True, exist_ok=True)

    def _fake_run(*args, **kwargs):
        _ = args
        _ = kwargs
        return subprocess.CompletedProcess(
            args=["git", "push", "origin", "--delete", "validator-suite-test"],
            returncode=128,
            stdout="",
            stderr="ssh: Could not resolve hostname github.com: Temporary failure in name resolution",
        )

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result = try_delete_remote_branch(
        "validator-suite-test",
        workspace_root=workspace_root,
        run_id="run-1",
        attempt_id="attempt-0001",
        now_fn=_fixed_now,
    )

    assert result.ok_non_blocking is True
    assert result.status == "DEFERRED"
    assert result.blocked_reason == "dns_or_name_resolution_failure"
    assert result.report_path.exists()

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["blocked_reason"] == "dns_or_name_resolution_failure"
    assert report["attempted_op"]["status"] == "DEFERRED"

    expected_next = datetime(2026, 2, 10, 12, 5, 0, tzinfo=timezone.utc).isoformat()
    assert report["attempted_op"]["next_attempt_at"] == expected_next


def test_non_dns_failures_become_terminal_after_fourth_attempt(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "ws"
    workspace_root.mkdir(parents=True, exist_ok=True)

    def _fake_run(*args, **kwargs):
        _ = args
        _ = kwargs
        return subprocess.CompletedProcess(
            args=["git", "push", "origin", "--delete", "validator-suite-test"],
            returncode=1,
            stdout="",
            stderr="remote rejected: policy failure",
        )

    monkeypatch.setattr(subprocess, "run", _fake_run)

    statuses = []
    escalations = []
    for _ in range(4):
        result = try_delete_remote_branch(
            "validator-suite-test",
            workspace_root=workspace_root,
            run_id="run-2",
            attempt_id="attempt-0001",
            now_fn=_fixed_now,
        )
        statuses.append(result.status)
        escalations.append(result.needs_escalation)
        assert result.ok_non_blocking is True

    assert statuses == ["DEFERRED", "DEFERRED", "DEFERRED", "TERMINAL"]
    assert escalations == [False, False, False, True]

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["needs_escalation"] is True
    assert report["attempted_op"]["attempts"] == 4


def test_success_marks_done_and_report_ops_are_sorted(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "ws"
    workspace_root.mkdir(parents=True, exist_ok=True)

    def _fake_run(*args, **kwargs):
        _ = args
        _ = kwargs
        return subprocess.CompletedProcess(
            args=["git", "push", "origin", "--delete", "validator-suite-branch"],
            returncode=0,
            stdout="deleted",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", _fake_run)

    result_b = try_delete_remote_branch(
        "validator-suite-b",
        workspace_root=workspace_root,
        run_id="run-3",
        attempt_id="attempt-0001",
        now_fn=_fixed_now,
    )
    result_a = try_delete_remote_branch(
        "validator-suite-a",
        workspace_root=workspace_root,
        run_id="run-3",
        attempt_id="attempt-0001",
        now_fn=_fixed_now,
    )

    assert result_b.status == "DONE"
    assert result_a.status == "DONE"

    report = json.loads(result_a.report_path.read_text(encoding="utf-8"))
    op_ids = [item["op_id"] for item in report["ops"]]
    assert op_ids == sorted(op_ids)


def test_dns_backoff_caps_at_twenty_four_hours(tmp_path: Path, monkeypatch) -> None:
    workspace_root = tmp_path / "ws"
    workspace_root.mkdir(parents=True, exist_ok=True)

    def _fake_run(*args, **kwargs):
        _ = args
        _ = kwargs
        return subprocess.CompletedProcess(
            args=["git", "push", "origin", "--delete", "validator-suite-backoff"],
            returncode=128,
            stdout="",
            stderr="name resolution failed",
        )

    monkeypatch.setattr(subprocess, "run", _fake_run)

    for _ in range(5):
        result = try_delete_remote_branch(
            "validator-suite-backoff",
            workspace_root=workspace_root,
            run_id="manual",
            attempt_id="manual",
            now_fn=_fixed_now,
        )

    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    attempted = report["attempted_op"]
    assert attempted["attempts"] == 5

    expected_next = datetime(2026, 2, 11, 12, 0, 0, tzinfo=timezone.utc).isoformat()
    assert attempted["next_attempt_at"] == expected_next

    queue_path = workspace_root / "artifacts" / "validation_runs" / "manual" / "manual" / "remote_ops_queue.jsonl"
    ops = load_queue(queue_path)
    assert len(ops) == 1
    assert ops[0].attempts == 5
