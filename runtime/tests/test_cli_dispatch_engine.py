"""CLI tests for 'lifeos dispatch submit' and 'lifeos dispatch status' commands."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from runtime.cli import cmd_dispatch_status, cmd_dispatch_submit
from runtime.orchestration.dispatch.engine import DispatchResult
from runtime.orchestration.dispatch.order import ORDER_SCHEMA_VERSION


MINIMAL_ORDER = {
    "schema_version": ORDER_SCHEMA_VERSION,
    "order_id": "cli_test_001",
    "task_ref": "CLI-test-ref",
    "created_at": "2026-02-26T10:00:00Z",
    "steps": [{"name": "build", "role": "builder"}],
}

PASS_RESULT = DispatchResult(
    order_id="cli_test_001",
    run_id="run_cli_001",
    outcome="SUCCESS",
    reason="chain_complete",
    terminal_packet_path="artifacts/terminal/TP_run_cli_001.yaml",
    repo_clean_verified=True,
    orphan_check_passed=True,
    completed_at="2026-02-26T10:01:00Z",
)

FAIL_RESULT = DispatchResult(
    order_id="cli_test_001",
    run_id=None,
    outcome="CLEAN_FAIL",
    reason="spine_failed",
    terminal_packet_path=None,
    repo_clean_verified=False,
    orphan_check_passed=True,
    completed_at="2026-02-26T10:01:00Z",
)


@pytest.fixture
def order_file(tmp_path: Path) -> Path:
    f = tmp_path / "cli_test_001.yaml"
    f.write_text(yaml.dump(MINIMAL_ORDER, sort_keys=True), encoding="utf-8")
    return f


def _submit_args(order_file: Path, as_json: bool = False) -> argparse.Namespace:
    return argparse.Namespace(order_file=str(order_file), json=as_json)


def _status_args(as_json: bool = False) -> argparse.Namespace:
    return argparse.Namespace(json=as_json)


# ── dispatch submit ───────────────────────────────────────────────────────────


def test_dispatch_submit_pass_returns_0(tmp_path, order_file, capsys):
    with patch("runtime.cli.DispatchEngine") as mock_cls:
        mock_engine = MagicMock()
        mock_engine.execute_from_path.return_value = PASS_RESULT
        mock_cls.return_value = mock_engine

        rc = cmd_dispatch_submit(_submit_args(order_file), tmp_path)

    assert rc == 0
    out = capsys.readouterr().out
    assert "SUCCESS" in out
    assert "cli_test_001" in out


def test_dispatch_submit_fail_returns_1(tmp_path, order_file):
    with patch("runtime.cli.DispatchEngine") as mock_cls:
        mock_engine = MagicMock()
        mock_engine.execute_from_path.return_value = FAIL_RESULT
        mock_cls.return_value = mock_engine

        rc = cmd_dispatch_submit(_submit_args(order_file), tmp_path)

    assert rc == 1


def test_dispatch_submit_json_output(tmp_path, order_file, capsys):
    with patch("runtime.cli.DispatchEngine") as mock_cls:
        mock_engine = MagicMock()
        mock_engine.execute_from_path.return_value = PASS_RESULT
        mock_cls.return_value = mock_engine

        rc = cmd_dispatch_submit(_submit_args(order_file, as_json=True), tmp_path)

    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["order_id"] == "cli_test_001"
    assert parsed["outcome"] == "SUCCESS"
    assert rc == 0


def test_dispatch_submit_missing_file_returns_1(tmp_path, capsys):
    args = _submit_args(tmp_path / "does_not_exist.yaml")
    rc = cmd_dispatch_submit(args, tmp_path)
    assert rc == 1
    err = capsys.readouterr().err
    assert "not found" in err


def test_dispatch_submit_invalid_order_returns_1(tmp_path, capsys):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        "schema_version: wrong_version\norder_id: x\ntask_ref: y\ncreated_at: z\nsteps: []\n",
        encoding="utf-8",
    )
    rc = cmd_dispatch_submit(_submit_args(bad), tmp_path)
    assert rc == 1
    err = capsys.readouterr().err
    assert "Invalid order" in err


# ── dispatch status ───────────────────────────────────────────────────────────


def test_dispatch_status_returns_0(tmp_path, capsys):
    rc = cmd_dispatch_status(_status_args(), tmp_path)
    assert rc == 0
    out = capsys.readouterr().out
    assert "pending" in out
    assert "active" in out
    assert "completed" in out


def test_dispatch_status_json_output(tmp_path, capsys):
    rc = cmd_dispatch_status(_status_args(as_json=True), tmp_path)
    assert rc == 0
    parsed = json.loads(capsys.readouterr().out)
    assert "pending_orders" in parsed
    assert "active_orders" in parsed
    assert "completed_orders" in parsed
