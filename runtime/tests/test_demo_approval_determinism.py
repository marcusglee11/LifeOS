from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from runtime.orchestration.ceo_queue import CEOQueue, EscalationEntry, EscalationType
from runtime.receipts.invocation_receipt import (
    finalize_run_receipts,
    reset_invocation_receipt_collectors,
)

FIXED_RUN_ID = "test-run-determinism-001"
FIXED_TIMESTAMP = "2026-01-01T00:00:00+00:00"
FIXED_CREATED_AT = datetime(2026, 1, 1, tzinfo=timezone.utc)
FIXED_CONTEXT = {
    "title": "Review T-022 proof path",
    "description": "Approve the CI proof workflow for deterministic certification evidence.",
    "priority": "P1",
}


def _normalize_queue_row(db_path: Path, escalation_id: str) -> dict[str, str]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM escalations WHERE id = ?", (escalation_id,)).fetchone()

    assert row is not None
    return dict(row)


def _run_roundtrip(tmp_path: Path, monkeypatch) -> tuple[dict[str, str], bytes, list[str]]:
    reset_invocation_receipt_collectors()
    monkeypatch.setattr("runtime.orchestration.ceo_queue._utc_now", lambda: FIXED_TIMESTAMP)

    repo_root = tmp_path
    db_path = repo_root / "artifacts" / "queue" / "escalations.db"
    queue = CEOQueue(db_path=db_path)

    escalation_id = queue.add_escalation(
        EscalationEntry(
            type=EscalationType.AMBIGUOUS_TASK,
            context=FIXED_CONTEXT,
            run_id=FIXED_RUN_ID,
            created_at=FIXED_CREATED_AT,
        )
    )
    assert queue.approve(escalation_id, note="approved", resolver="test-resolver") is True

    index_path = finalize_run_receipts(FIXED_RUN_ID, output_dir=repo_root)
    assert index_path is not None

    queue_row = _normalize_queue_row(db_path, escalation_id)
    index_bytes = index_path.read_bytes()
    index_payload = json.loads(index_bytes.decode("utf-8"))
    seat_ids = [receipt["seat_id"] for receipt in index_payload["receipts"]]

    reset_invocation_receipt_collectors()
    return queue_row, index_bytes, seat_ids


def test_demo_approval_determinism(monkeypatch, tmp_path: Path):
    """CEOQueue approval round-trips must remain deterministic across clean runs."""
    queue_row_1, index_bytes_1, seat_ids_1 = _run_roundtrip(tmp_path / "run1", monkeypatch)
    queue_row_2, index_bytes_2, seat_ids_2 = _run_roundtrip(tmp_path / "run2", monkeypatch)

    assert queue_row_1 == queue_row_2
    assert index_bytes_1 == index_bytes_2
    assert seat_ids_1 == ["queue_add", "queue_approve"]
    assert seat_ids_2 == ["queue_add", "queue_approve"]
