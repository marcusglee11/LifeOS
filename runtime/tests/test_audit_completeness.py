"""Tests: Audit completeness (Phase 4A+4B+4C — Constitutional Compliance)."""

from __future__ import annotations

from pathlib import Path

import pytest

from runtime.orchestration.ceo_queue import (
    CEOQueue,
    EscalationEntry,
    EscalationType,
)
from runtime.receipts.invocation_receipt import (
    get_or_create_collector,
    reset_invocation_receipt_collectors,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_invocation_receipt_collectors()
    yield
    reset_invocation_receipt_collectors()


# ===========================================================================
# Phase 4A: input_hash field on InvocationReceipt
# ===========================================================================


def test_receipt_has_input_hash_field():
    from runtime.receipts.invocation_receipt import InvocationReceiptCollector

    collector = InvocationReceiptCollector(run_id="test-4a")
    from datetime import datetime, timezone

    ts = datetime.now(timezone.utc).isoformat()
    r = collector.record(
        provider_id="test",
        mode="api",
        seat_id="tester",
        start_ts=ts,
        end_ts=ts,
        exit_status=0,
        output_content="hello",
        input_hash="sha256:abc123",
    )
    assert r.input_hash == "sha256:abc123"


def test_receipt_input_hash_defaults_to_none():
    from datetime import datetime, timezone

    from runtime.receipts.invocation_receipt import InvocationReceiptCollector

    collector = InvocationReceiptCollector(run_id="test-4a-none")
    ts = datetime.now(timezone.utc).isoformat()
    r = collector.record(
        provider_id="test",
        mode="api",
        seat_id="tester",
        start_ts=ts,
        end_ts=ts,
        exit_status=0,
        output_content="hello",
    )
    assert r.input_hash is None


def test_receipt_serializes_input_hash(tmp_path: Path):
    """input_hash survives finalize → JSON round-trip."""
    import json
    from datetime import datetime, timezone

    from runtime.receipts.invocation_receipt import InvocationReceiptCollector

    collector = InvocationReceiptCollector(run_id="test-4a-serial")
    ts = datetime.now(timezone.utc).isoformat()
    collector.record(
        provider_id="test",
        mode="api",
        seat_id="tester",
        start_ts=ts,
        end_ts=ts,
        exit_status=0,
        output_content="hello",
        input_hash="sha256:deadbeef",
    )
    index_path = collector.finalize(tmp_path)
    index = json.loads(index_path.read_text())
    assert index["receipts"][0]["input_hash"] == "sha256:deadbeef"


# ===========================================================================
# Phase 4B: repo_map_hash in llm_call metadata
# ===========================================================================


def test_engine_stores_repo_map_hash_when_path_provided(tmp_path: Path):
    """When repo_map_path is in payload and exists, hash stored in metadata."""
    from unittest.mock import MagicMock, patch

    from runtime.orchestration.engine import (
        ExecutionContext,
        Orchestrator,
        StepSpec,
        WorkflowDefinition,
    )

    repo_map_file = tmp_path / "REPO_MAP.md"
    repo_map_file.write_text("# map content")

    step = StepSpec(
        id="s1",
        kind="runtime",
        payload={
            "operation": "llm_call",
            "prompt": "describe the repo",
            "repo_map_path": str(repo_map_file),
        },
    )
    workflow = WorkflowDefinition(id="wf-4b", steps=[step])
    ctx = ExecutionContext(initial_state={})

    orch = Orchestrator()
    mock_response = MagicMock()
    mock_response.content = "ok"
    mock_response.call_id = "test-call"
    mock_response.model_used = "test-model"
    mock_response.latency_ms = 10
    mock_response.timestamp = "2026-01-01T00:00:00Z"

    with patch.object(orch, "_get_llm_client") as mock_client:
        mock_client.return_value.call.return_value = mock_response
        result = orch.run_workflow(workflow, ctx)

    assert result.success
    meta = result.final_state.get("llm_response_metadata", {})
    assert "repo_map_hash" in meta
    assert meta["repo_map_hash"] is not None


# ===========================================================================
# Phase 4C: CEO queue emits receipts on add_escalation and approve/reject
# ===========================================================================


def test_add_escalation_emits_receipt(tmp_path: Path):
    """add_escalation emits an invocation receipt."""
    run_id = "ceo-queue-test-4c"
    queue = CEOQueue(db_path=tmp_path / "q.db")
    entry = EscalationEntry(
        type=EscalationType.GOVERNANCE_SURFACE_TOUCH,
        context={"summary": "test escalation"},
        run_id=run_id,
    )
    esc_id = queue.add_escalation(entry)
    assert esc_id.startswith("ESC-")

    collector = get_or_create_collector(run_id)
    assert len(collector.receipts) >= 1
    r = collector.receipts[0]
    assert r.provider_id == "ceo_queue"
    assert r.seat_id == "queue_add"
    assert r.exit_status == 0


def test_approve_emits_receipt(tmp_path: Path):
    """approve emits an invocation receipt."""
    run_id = "ceo-queue-approve-4c"
    queue = CEOQueue(db_path=tmp_path / "q.db")
    entry = EscalationEntry(
        type=EscalationType.BUDGET_ESCALATION,
        context={"amount": 100},
        run_id=run_id,
    )
    esc_id = queue.add_escalation(entry)
    reset_invocation_receipt_collectors()  # clear add receipt

    ok = queue.approve(esc_id, note="approved by test", resolver="CEO")
    assert ok is True

    collector = get_or_create_collector(run_id)
    assert len(collector.receipts) >= 1
    r = collector.receipts[0]
    assert r.seat_id == "queue_approve"


def test_reject_emits_receipt(tmp_path: Path):
    """reject emits an invocation receipt."""
    run_id = "ceo-queue-reject-4c"
    queue = CEOQueue(db_path=tmp_path / "q.db")
    entry = EscalationEntry(
        type=EscalationType.AMBIGUOUS_TASK,
        context={"detail": "unclear"},
        run_id=run_id,
    )
    esc_id = queue.add_escalation(entry)
    reset_invocation_receipt_collectors()

    ok = queue.reject(esc_id, reason="not approved", resolver="CEO")
    assert ok is True

    collector = get_or_create_collector(run_id)
    assert len(collector.receipts) >= 1
    r = collector.receipts[0]
    assert r.seat_id == "queue_reject"
