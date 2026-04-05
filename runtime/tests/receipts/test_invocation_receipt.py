"""Tests for per-invocation receipt collector and schema validation."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from runtime.receipts.invocation_receipt import (
    InvocationReceiptCollector,
    finalize_run_receipts,
    get_or_create_collector,
    reset_invocation_receipt_collectors,
)
from runtime.receipts.validator import validate_artefact
from runtime.util.canonical import compute_sha256


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture(autouse=True)
def _reset_collectors() -> None:
    reset_invocation_receipt_collectors()
    yield
    reset_invocation_receipt_collectors()


def test_collector_records_and_finalizes(tmp_path):
    """Happy path: record invocations, finalize to index.json."""
    collector = InvocationReceiptCollector(run_id="run_test_001")

    collector.record(
        provider_id="zen",
        mode="api",
        seat_id="designer",
        start_ts=_ts(),
        end_ts=_ts(),
        exit_status=0,
        output_content="design output here",
        schema_validation="pass",
        token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    )

    collector.record(
        provider_id="claude_code",
        mode="cli",
        seat_id="reviewer_architect",
        start_ts=_ts(),
        end_ts=_ts(),
        exit_status=0,
        output_content="review output here",
        schema_validation="n/a",
    )

    index_path = collector.finalize(tmp_path)

    assert index_path.exists()
    assert index_path.name == "index.json"
    assert "run_test_001" in str(index_path)

    index = json.loads(index_path.read_text("utf-8"))
    assert index["schema_version"] == "invocation_index_v1"
    assert index["run_id"] == "run_test_001"
    assert index["receipt_count"] == 2
    assert len(index["receipts"]) == 2
    assert (index_path.parent / "0001_zen.json").exists()
    assert (index_path.parent / "0002_claude_code.json").exists()


def test_receipt_schema_validation():
    """Invocation receipt validates against its schema."""
    collector = InvocationReceiptCollector(run_id="run_schema_test")
    collector.record(
        provider_id="zen",
        mode="api",
        seat_id="designer",
        start_ts=_ts(),
        end_ts=_ts(),
        exit_status=0,
        output_content="test content",
        schema_validation="pass",
    )

    from dataclasses import asdict

    receipt_dict = asdict(collector.receipts[0])
    errors = validate_artefact(receipt_dict, "invocation_receipt")
    assert errors == [], f"Schema validation failed: {errors}"


def test_index_schema_validation(tmp_path):
    """Finalized index validates against invocation_index schema."""
    collector = InvocationReceiptCollector(run_id="run_index_test")
    collector.record(
        provider_id="zen",
        mode="api",
        seat_id="designer",
        start_ts=_ts(),
        end_ts=_ts(),
        exit_status=0,
        output_content="test",
        schema_validation="n/a",
    )

    index_path = collector.finalize(tmp_path)
    index = json.loads(index_path.read_text("utf-8"))
    errors = validate_artefact(index, "invocation_index")
    assert errors == [], f"Index schema validation failed: {errors}"


def test_output_hash_deterministic():
    """Same content produces same output_hash."""
    collector = InvocationReceiptCollector(run_id="run_hash_test")
    content = "identical output"

    r1 = collector.record(
        provider_id="zen",
        mode="api",
        seat_id="a",
        start_ts=_ts(),
        end_ts=_ts(),
        exit_status=0,
        output_content=content,
        schema_validation="n/a",
    )
    r2 = collector.record(
        provider_id="zen",
        mode="api",
        seat_id="b",
        start_ts=_ts(),
        end_ts=_ts(),
        exit_status=0,
        output_content=content,
        schema_validation="n/a",
    )

    assert r1.output_hash == r2.output_hash
    assert r1.output_hash == compute_sha256(content)


def test_seq_monotonic():
    """Sequence numbers increase monotonically."""
    collector = InvocationReceiptCollector(run_id="run_seq_test")

    for i in range(5):
        collector.record(
            provider_id="zen",
            mode="api",
            seat_id=f"seat_{i}",
            start_ts=_ts(),
            end_ts=_ts(),
            exit_status=0,
            output_content=f"output_{i}",
            schema_validation="n/a",
        )

    seqs = [r.seq for r in collector.receipts]
    assert seqs == [1, 2, 3, 4, 5]
    assert all(seqs[i] < seqs[i + 1] for i in range(len(seqs) - 1))


def test_run_level_finalize_writes_index_and_receipts(tmp_path):
    collector = get_or_create_collector("run_finalize")
    collector.record(
        provider_id="openai-codex",
        mode="api",
        seat_id="builder",
        start_ts=_ts(),
        end_ts=_ts(),
        exit_status=0,
        output_content="ok",
        schema_validation="pass",
    )

    index_path = finalize_run_receipts("run_finalize", tmp_path)
    assert index_path is not None
    assert index_path.exists()
    assert (index_path.parent / "0001_openai-codex.json").exists()
    assert finalize_run_receipts("run_finalize", tmp_path) is None


def test_run_level_finalize_can_emit_empty_index(tmp_path):
    index_path = finalize_run_receipts("run_empty", tmp_path, include_empty=True)
    assert index_path is not None
    index = json.loads(index_path.read_text("utf-8"))
    assert index["run_id"] == "run_empty"
    assert index["receipt_count"] == 0
