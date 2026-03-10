"""Tests for DispatchEngine — Phase 1 lifecycle and gates."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from runtime.orchestration.dispatch.engine import DispatchEngine, DispatchResult
from runtime.orchestration.dispatch.manifest import MANIFEST_RELATIVE_PATH
from runtime.orchestration.dispatch.order import ORDER_SCHEMA_VERSION, ExecutionOrder, parse_order

# ── Helpers ───────────────────────────────────────────────────────────────────

MINIMAL_ORDER_RAW = {
    "schema_version": ORDER_SCHEMA_VERSION,
    "order_id": "exec_engine_test_001",
    "task_ref": "TEST-task-ref",
    "created_at": "2026-02-26T10:00:00Z",
    "steps": [
        {"name": "build", "role": "builder"},
    ],
}

PASS_SPINE_RESULT: Dict[str, Any] = {
    "run_id": "run_20260226_test001",
    "outcome": "PASS",
    "reason": "chain_complete",
    "state": "DONE",
    "terminal_packet_path": "artifacts/terminal/TP_run_20260226_test001.yaml",
}

FAIL_SPINE_RESULT: Dict[str, Any] = {
    "run_id": "run_20260226_test002",
    "outcome": "BLOCKED",
    "reason": "kill_switch_active",
    "state": "BLOCKED",
    "terminal_packet_path": "artifacts/terminal/TP_run_20260226_test002.yaml",
}


def _make_engine(tmp_path: Path) -> DispatchEngine:
    return DispatchEngine(repo_root=tmp_path)


def _make_order_file(tmp_path: Path, raw: dict = None) -> Path:
    raw = raw or MINIMAL_ORDER_RAW
    order_file = tmp_path / "test_order.yaml"
    order_file.write_text(
        yaml.dump(raw, sort_keys=True, default_flow_style=False), encoding="utf-8"
    )
    return order_file


# ── Directory setup ───────────────────────────────────────────────────────────


def test_engine_creates_dispatch_dirs(tmp_path):
    engine = _make_engine(tmp_path)
    assert engine.inbox.exists()
    assert engine.active.exists()
    assert engine.completed.exists()


# ── submit_to_inbox ───────────────────────────────────────────────────────────


def test_submit_to_inbox_copies_file(tmp_path):
    engine = _make_engine(tmp_path)
    order_file = _make_order_file(tmp_path)
    dest = engine.submit_to_inbox(order_file)
    assert dest.exists()
    assert dest.parent == engine.inbox
    assert dest.name == "exec_engine_test_001.yaml"


def test_submit_to_inbox_validates_order(tmp_path):
    from runtime.orchestration.dispatch.order import OrderValidationError

    engine = _make_engine(tmp_path)
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("schema_version: bad_version\norder_id: x\ntask_ref: y\ncreated_at: z\nsteps: []\n", encoding="utf-8")
    with pytest.raises(OrderValidationError):
        engine.submit_to_inbox(bad_file)


# ── poll_inbox ────────────────────────────────────────────────────────────────


def test_poll_inbox_empty(tmp_path):
    engine = _make_engine(tmp_path)
    assert engine.poll_inbox() == []


def test_poll_inbox_finds_orders(tmp_path):
    engine = _make_engine(tmp_path)
    order_file = _make_order_file(tmp_path)
    engine.submit_to_inbox(order_file)
    pending = engine.poll_inbox()
    assert len(pending) == 1
    assert pending[0].name == "exec_engine_test_001.yaml"


# ── execute lifecycle ─────────────────────────────────────────────────────────


def test_execute_inbox_to_completed_on_pass(tmp_path):
    """Full lifecycle: inbox → active → completed when spine returns PASS."""
    engine = _make_engine(tmp_path)
    order_file = _make_order_file(tmp_path)
    engine.submit_to_inbox(order_file)

    with patch("runtime.orchestration.loop.spine.LoopSpine") as mock_spine_cls:
        mock_spine = MagicMock()
        mock_spine.run.return_value = PASS_SPINE_RESULT
        mock_spine_cls.return_value = mock_spine

        order = parse_order(MINIMAL_ORDER_RAW)
        result = engine.execute(order)

    assert result.outcome == "SUCCESS"
    # Order should be in completed, not inbox or active
    assert not list(engine.inbox.glob("exec_engine_test_001.yaml"))
    assert not (engine.active / "exec_engine_test_001.yaml").exists()
    assert (engine.completed / "exec_engine_test_001.yaml").exists()


def test_execute_completed_file_has_result_record(tmp_path):
    engine = _make_engine(tmp_path)

    with patch("runtime.orchestration.loop.spine.LoopSpine") as mock_spine_cls:
        mock_spine = MagicMock()
        mock_spine.run.return_value = PASS_SPINE_RESULT
        mock_spine_cls.return_value = mock_spine

        order = parse_order(MINIMAL_ORDER_RAW)
        engine.execute(order)

    completed_file = engine.completed / "exec_engine_test_001.yaml"
    content = completed_file.read_text(encoding="utf-8")
    assert "dispatch_result" in content
    assert "SUCCESS" in content


def test_execute_appends_to_manifest(tmp_path):
    engine = _make_engine(tmp_path)

    with patch("runtime.orchestration.loop.spine.LoopSpine") as mock_spine_cls:
        mock_spine = MagicMock()
        mock_spine.run.return_value = PASS_SPINE_RESULT
        mock_spine_cls.return_value = mock_spine

        order = parse_order(MINIMAL_ORDER_RAW)
        engine.execute(order)

    entries = engine.manifest.read_all()
    assert len(entries) == 1
    assert entries[0]["order_id"] == "exec_engine_test_001"
    assert entries[0]["outcome"] == "SUCCESS"


def test_execute_records_run_id(tmp_path):
    engine = _make_engine(tmp_path)

    with patch("runtime.orchestration.loop.spine.LoopSpine") as mock_spine_cls:
        mock_spine = MagicMock()
        mock_spine.run.return_value = PASS_SPINE_RESULT
        mock_spine_cls.return_value = mock_spine

        order = parse_order(MINIMAL_ORDER_RAW)
        result = engine.execute(order)

    assert result.run_id == "run_20260226_test001"


def test_execute_records_terminal_packet_path(tmp_path):
    engine = _make_engine(tmp_path)

    with patch("runtime.orchestration.loop.spine.LoopSpine") as mock_spine_cls:
        mock_spine = MagicMock()
        mock_spine.run.return_value = PASS_SPINE_RESULT
        mock_spine_cls.return_value = mock_spine

        order = parse_order(MINIMAL_ORDER_RAW)
        result = engine.execute(order)

    assert result.terminal_packet_path == PASS_SPINE_RESULT["terminal_packet_path"]


def test_execute_passes_worktree_constraint_to_spine(tmp_path):
    engine = _make_engine(tmp_path)
    raw = dict(MINIMAL_ORDER_RAW)
    raw["constraints"] = {"worktree": True}

    with patch("runtime.orchestration.loop.spine.LoopSpine") as mock_spine_cls:
        mock_spine = MagicMock()
        mock_spine.run.return_value = PASS_SPINE_RESULT
        mock_spine_cls.return_value = mock_spine

        order = parse_order(raw)
        engine.execute(order)

    assert mock_spine_cls.call_args.kwargs.get("use_worktree") is True


def test_execute_auto_remediates_isolation_required_once(tmp_path):
    engine = _make_engine(tmp_path)
    raw = dict(MINIMAL_ORDER_RAW)
    raw["constraints"] = {"worktree": False}

    first = {
        "run_id": "run_iso_1",
        "outcome": "BLOCKED",
        "reason": "ISOLATION_REQUIRED: primary worktree on build/foo",
        "state": "BLOCKED",
        "terminal_packet_path": "artifacts/terminal/TP_run_iso_1.yaml",
    }
    second = {
        "run_id": "run_iso_2",
        "outcome": "PASS",
        "reason": "chain_complete",
        "state": "DONE",
        "terminal_packet_path": "artifacts/terminal/TP_run_iso_2.yaml",
    }

    with patch("runtime.orchestration.loop.spine.LoopSpine") as mock_spine_cls:
        mock_one = MagicMock()
        mock_one.run.return_value = first
        mock_two = MagicMock()
        mock_two.run.return_value = second
        mock_spine_cls.side_effect = [mock_one, mock_two]

        order = parse_order(raw)
        result = engine.execute(order)

    assert result.outcome == "SUCCESS"
    assert "auto-remediated:isolation" in result.reason
    assert mock_spine_cls.call_count == 2
    first_kwargs = mock_spine_cls.call_args_list[0].kwargs
    second_kwargs = mock_spine_cls.call_args_list[1].kwargs
    assert first_kwargs.get("use_worktree") is False
    assert second_kwargs.get("use_worktree") is True


def test_execute_preemptively_flips_to_worktree_on_isolation_required(tmp_path):
    engine = _make_engine(tmp_path)
    raw = dict(MINIMAL_ORDER_RAW)
    raw["constraints"] = {"worktree": False}

    with patch("runtime.orchestration.loop.spine.LoopSpine") as mock_spine_cls, patch(
        "runtime.orchestration.dispatch.engine._isolation_required", return_value=True
    ):
        mock_spine = MagicMock()
        mock_spine.run.return_value = PASS_SPINE_RESULT
        mock_spine_cls.return_value = mock_spine

        order = parse_order(raw)
        result = engine.execute(order)

    assert result.outcome == "SUCCESS"
    assert "auto-remediated:isolation" in result.reason
    assert mock_spine_cls.call_count == 1
    assert mock_spine_cls.call_args.kwargs.get("use_worktree") is True


# ── Non-bypassable gates ──────────────────────────────────────────────────────


def test_repo_clean_gate_always_runs_on_pass(tmp_path):
    """repo_clean_verified must be populated even on successful runs."""
    engine = _make_engine(tmp_path)

    with patch("runtime.orchestration.loop.spine.LoopSpine") as mock_spine_cls, patch(
        "runtime.orchestration.dispatch.engine._check_repo_clean"
    ) as mock_clean:
        mock_spine = MagicMock()
        mock_spine.run.return_value = PASS_SPINE_RESULT
        mock_spine_cls.return_value = mock_spine
        mock_clean.return_value = True

        order = parse_order(MINIMAL_ORDER_RAW)
        result = engine.execute(order)

    mock_clean.assert_called_once()
    assert result.repo_clean_verified is True


def test_repo_clean_gate_always_runs_on_fail(tmp_path):
    """repo_clean_verified is checked even when spine fails."""
    engine = _make_engine(tmp_path)

    with patch("runtime.orchestration.loop.spine.LoopSpine") as mock_spine_cls, patch(
        "runtime.orchestration.dispatch.engine._check_repo_clean"
    ) as mock_clean:
        mock_spine = MagicMock()
        mock_spine.run.return_value = FAIL_SPINE_RESULT
        mock_spine_cls.return_value = mock_spine
        mock_clean.return_value = False

        order = parse_order(MINIMAL_ORDER_RAW)
        result = engine.execute(order)

    mock_clean.assert_called_once()
    assert result.repo_clean_verified is False


def test_orphan_check_placeholder_true(tmp_path):
    """Phase 1: orphan_check_passed is always True."""
    engine = _make_engine(tmp_path)

    with patch("runtime.orchestration.loop.spine.LoopSpine") as mock_spine_cls:
        mock_spine = MagicMock()
        mock_spine.run.return_value = PASS_SPINE_RESULT
        mock_spine_cls.return_value = mock_spine

        order = parse_order(MINIMAL_ORDER_RAW)
        result = engine.execute(order)

    assert result.orphan_check_passed is True


def test_gates_run_even_on_spine_exception(tmp_path):
    """Non-bypassable: gates run even when spine raises."""
    engine = _make_engine(tmp_path)

    with patch("runtime.orchestration.loop.spine.LoopSpine") as mock_spine_cls, patch(
        "runtime.orchestration.dispatch.engine._check_repo_clean"
    ) as mock_clean:
        mock_spine = MagicMock()
        mock_spine.run.side_effect = RuntimeError("spine crashed")
        mock_spine_cls.return_value = mock_spine
        mock_clean.return_value = True

        order = parse_order(MINIMAL_ORDER_RAW)
        result = engine.execute(order)

    # Gate must have run
    mock_clean.assert_called_once()
    # Outcome is CLEAN_FAIL
    assert result.outcome == "CLEAN_FAIL"
    assert "spine crashed" in result.reason


# ── Crash recovery ────────────────────────────────────────────────────────────


def test_crash_recovery_clears_active(tmp_path):
    engine = _make_engine(tmp_path)

    # Simulate a stranded order in active/
    stranded = engine.active / "exec_crashed_001.yaml"
    stranded.write_text(
        yaml.dump(
            {**MINIMAL_ORDER_RAW, "order_id": "exec_crashed_001"},
            sort_keys=True,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )

    recovered = engine.recover_crashed_runs()

    assert "exec_crashed_001" in recovered
    assert not stranded.exists()
    assert (engine.completed / "exec_crashed_001.yaml").exists()


def test_crash_recovery_writes_manifest_entry(tmp_path):
    engine = _make_engine(tmp_path)

    stranded = engine.active / "exec_crashed_002.yaml"
    stranded.write_text(
        yaml.dump(
            {**MINIMAL_ORDER_RAW, "order_id": "exec_crashed_002"},
            sort_keys=True,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )

    engine.recover_crashed_runs()

    entries = engine.manifest.read_all()
    assert len(entries) == 1
    assert entries[0]["order_id"] == "exec_crashed_002"
    assert entries[0]["reason"] == "CRASH_RECOVERY"


def test_crash_recovery_completed_file_has_reason(tmp_path):
    engine = _make_engine(tmp_path)

    stranded = engine.active / "exec_crashed_003.yaml"
    stranded.write_text(
        yaml.dump(
            {**MINIMAL_ORDER_RAW, "order_id": "exec_crashed_003"},
            sort_keys=True,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )

    engine.recover_crashed_runs()

    content = (engine.completed / "exec_crashed_003.yaml").read_text(encoding="utf-8")
    assert "CRASH_RECOVERY" in content


def test_crash_recovery_clears_orphan_run_lock(tmp_path):
    engine = _make_engine(tmp_path)

    stranded = engine.active / "exec_crashed_004.yaml"
    stranded.write_text(
        yaml.dump(
            {**MINIMAL_ORDER_RAW, "order_id": "exec_crashed_004"},
            sort_keys=True,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )

    lock_path = tmp_path / "artifacts" / "locks" / "run.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("{}", encoding="utf-8")

    engine.recover_crashed_runs()

    assert not lock_path.exists()


def test_crash_recovery_does_not_touch_lock_when_no_orphans(tmp_path):
    engine = _make_engine(tmp_path)
    lock_path = tmp_path / "artifacts" / "locks" / "run.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_text("{}", encoding="utf-8")

    recovered = engine.recover_crashed_runs()

    assert recovered == []
    assert lock_path.exists()


# ── execute_async is NotImplementedError in Phase 1 ──────────────────────────


def test_execute_async_not_available(tmp_path):
    engine = _make_engine(tmp_path)
    order = parse_order(MINIMAL_ORDER_RAW)
    with pytest.raises(NotImplementedError, match="Phase 1"):
        engine.execute_async(order)


# ── status ────────────────────────────────────────────────────────────────────


def test_status_counts(tmp_path):
    engine = _make_engine(tmp_path)
    order_file = _make_order_file(tmp_path)
    engine.submit_to_inbox(order_file)

    status = engine.status()
    assert status["pending_orders"] == 1
    assert status["active_orders"] == 0
    assert "exec_engine_test_001" in status["pending"]
