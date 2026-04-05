"""Tests for runtime/receipts/store.py"""

import json

import pytest

from runtime.receipts.plan_core import compute_plan_core_sha256
from runtime.receipts.receipt_emitter import (
    build_acceptance_receipt,
    build_blocked_report,
    build_land_receipt,
    compute_decision,
)
from runtime.receipts.store import ReceiptStore

SAMPLE_PLAN_CORE = {
    "plan_id": "plan-test-001",
    "schema_version": "1.0",
    "phase_order": ["init", "build"],
}
SAMPLE_WORKSPACE_SHA = "abc123def456abc123def456abc123def456abc1"
SAMPLE_TREE_OID = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
SAMPLE_PLAN_SHA = compute_plan_core_sha256(SAMPLE_PLAN_CORE)
SAMPLE_ACCEPTANCE_RECEIPT_ID = "01HN2P8QVKXJZ3MRSF4T6WBYDE"
SAMPLE_LANDED_SHA = "cafe0000cafe0000cafe0000cafe0000cafe0000"

PASS_ROLLUP = {"overall_status": "PASS"}
FAIL_ROLLUP = {"overall_status": "FAIL"}


def make_acceptance_receipt(supersedes=None):
    from runtime.receipts.runlog import RunLogEmitter

    emitter = RunLogEmitter(phase_order=["init", "build"])
    decision = compute_decision(PASS_ROLLUP)
    return build_acceptance_receipt(
        SAMPLE_WORKSPACE_SHA,
        SAMPLE_TREE_OID,
        SAMPLE_PLAN_SHA,
        emitter,
        decision,
        PASS_ROLLUP,
        supersedes=supersedes,
    )


def make_blocked_report():
    return build_blocked_report(
        SAMPLE_WORKSPACE_SHA,
        SAMPLE_PLAN_SHA,
        reason_code="GATE_FAIL",
        gate_rollup=FAIL_ROLLUP,
    )


def test_write_creates_directory_structure(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    store.write_run_artefacts(
        SAMPLE_WORKSPACE_SHA,
        SAMPLE_PLAN_SHA,
        {
            "plan_core.json": SAMPLE_PLAN_CORE,
        },
    )
    run_dir = tmp_path / "store" / "artefacts" / SAMPLE_WORKSPACE_SHA / SAMPLE_PLAN_SHA
    assert run_dir.exists()


def test_write_all_files_present(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    files = {
        "plan_core.json": SAMPLE_PLAN_CORE,
        "gate_results.json": {"gates": []},
        "meta.json": {"version": "1.0"},
        "runlog.jsonl": '{"event": "test"}\n',
    }
    written = store.write_run_artefacts(SAMPLE_WORKSPACE_SHA, SAMPLE_PLAN_SHA, files)
    for filename in files:
        assert filename in written
        assert written[filename].exists()


def test_write_acceptance_receipt_append_only(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    receipt = make_acceptance_receipt()
    path = store.write_acceptance_receipt(receipt)
    assert path.exists()
    assert path.name == f"{receipt['receipt_id']}.json"
    # Path must be in receipts/acceptance/
    assert "acceptance" in str(path)


def test_no_rename_on_supersession(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    r1 = make_acceptance_receipt()
    r2 = make_acceptance_receipt(supersedes=r1["receipt_id"])
    path1 = store.write_acceptance_receipt(r1)
    path2 = store.write_acceptance_receipt(r2)
    # Both files must exist (no rename)
    assert path1.exists(), "First receipt should still exist after supersession"
    assert path2.exists()
    assert path1 != path2


def test_index_appended_on_write(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    receipt = make_acceptance_receipt()
    store.write_acceptance_receipt(receipt)
    index_path = tmp_path / "store" / "index.jsonl"
    assert index_path.exists()
    lines = [line for line in index_path.read_text().splitlines() if line.strip()]
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["receipt_id"] == receipt["receipt_id"]


def test_query_active_follows_chain(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    r1 = make_acceptance_receipt()
    r2 = make_acceptance_receipt(supersedes=r1["receipt_id"])
    store.write_acceptance_receipt(r1)
    store.write_acceptance_receipt(r2)
    active = store.query_active_acceptance(SAMPLE_WORKSPACE_SHA, SAMPLE_PLAN_SHA)
    assert active is not None
    assert active["receipt_id"] == r2["receipt_id"]


def test_query_active_returns_none_when_empty(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    result = store.query_active_acceptance("nonexistent", "nonexistent")
    assert result is None


def test_query_by_id_returns_receipt(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    receipt = make_acceptance_receipt()
    store.write_acceptance_receipt(receipt)
    result = store.query_acceptance_by_id(receipt["receipt_id"])
    assert result is not None
    assert result["receipt_id"] == receipt["receipt_id"]


def test_write_blocked_report(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    report = make_blocked_report()
    path = store.write_blocked_report(report)
    assert path.exists()
    assert path.name == f"{report['report_id']}.json"
    assert "blocked" in str(path)


def test_query_all_for_workspace(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    receipt = make_acceptance_receipt()
    report = make_blocked_report()
    store.write_acceptance_receipt(receipt)
    store.write_blocked_report(report)
    results = store.query_all_receipts_for_workspace(SAMPLE_WORKSPACE_SHA)
    result_ids = {r.get("receipt_id") or r.get("report_id") for r in results}
    assert receipt["receipt_id"] in result_ids
    assert report["report_id"] in result_ids


def test_write_uses_atomic_operations(tmp_path):
    """No .tmp files should be left behind after writes."""
    store = ReceiptStore(tmp_path / "store")
    receipt = make_acceptance_receipt()
    store.write_acceptance_receipt(receipt)
    tmp_files = list((tmp_path / "store").rglob("*.tmp"))
    assert tmp_files == [], f"Found leftover .tmp files: {tmp_files}"


def test_rebuild_index_recovers(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    receipt = make_acceptance_receipt()
    store.write_acceptance_receipt(receipt)
    # Delete the index
    index_path = tmp_path / "store" / "index.jsonl"
    index_path.unlink()
    assert not index_path.exists()
    # Rebuild
    store.rebuild_index()
    assert index_path.exists()
    # Query should work again
    result = store.query_active_acceptance(SAMPLE_WORKSPACE_SHA, SAMPLE_PLAN_SHA)
    assert result is not None
    assert result["receipt_id"] == receipt["receipt_id"]


def test_artefact_refs_resolve(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    files = {
        "plan_core.json": SAMPLE_PLAN_CORE,
        "gate_results.json": {},
    }
    written = store.write_run_artefacts(SAMPLE_WORKSPACE_SHA, SAMPLE_PLAN_SHA, files)
    for filename, path in written.items():
        assert path.exists(), f"Artefact ref {filename} does not resolve to existing file"


def test_write_acceptance_receipt_rejects_overwrite(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    receipt = make_acceptance_receipt()
    store.write_acceptance_receipt(receipt)
    with pytest.raises(ValueError, match="refuses overwrite"):
        store.write_acceptance_receipt(receipt)


def test_write_blocked_report_rejects_overwrite(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    report = make_blocked_report()
    store.write_blocked_report(report)
    with pytest.raises(ValueError, match="refuses overwrite"):
        store.write_blocked_report(report)


def test_write_run_artefacts_rejects_path_traversal(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    with pytest.raises(ValueError, match="path separators"):
        store.write_run_artefacts(SAMPLE_WORKSPACE_SHA, SAMPLE_PLAN_SHA, {"../evil.json": {"x": 1}})


def test_write_run_artefacts_rejects_overwrite(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    store.write_run_artefacts(
        SAMPLE_WORKSPACE_SHA, SAMPLE_PLAN_SHA, {"plan_core.json": SAMPLE_PLAN_CORE}
    )
    with pytest.raises(ValueError, match="refuses overwrite"):
        store.write_run_artefacts(
            SAMPLE_WORKSPACE_SHA, SAMPLE_PLAN_SHA, {"plan_core.json": SAMPLE_PLAN_CORE}
        )


def test_query_ignores_index_path_traversal(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    index_path = tmp_path / "store" / "index.jsonl"
    index_path.write_text(
        json.dumps(
            {
                "type": "acceptance",
                "receipt_id": "01HZZZZZZZZZZZZZZZZZZZZZZZ",
                "workspace_sha": SAMPLE_WORKSPACE_SHA,
                "plan_core_sha256": SAMPLE_PLAN_SHA,
                "path": "../../outside.json",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = store.query_active_acceptance(SAMPLE_WORKSPACE_SHA, SAMPLE_PLAN_SHA)
    assert result is None


def test_write_acceptance_receipt_rejects_path_traversal_id(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    receipt = make_acceptance_receipt()
    receipt["receipt_id"] = "../evil"
    with pytest.raises(ValueError, match="receipt_id"):
        store.write_acceptance_receipt(receipt)


def test_write_blocked_report_rejects_path_traversal_id(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    report = make_blocked_report()
    report["report_id"] = "../evil"
    with pytest.raises(ValueError, match="report_id"):
        store.write_blocked_report(report)


def test_query_by_id_rejects_path_traversal(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    assert store.query_acceptance_by_id("../evil") is None


def test_rebuild_index_recovers_land_receipts(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    receipt = build_land_receipt(
        landed_sha=SAMPLE_LANDED_SHA,
        landed_tree_oid=SAMPLE_TREE_OID,
        land_target="refs/heads/main",
        merge_method="squash",
        acceptance_receipt_id=SAMPLE_ACCEPTANCE_RECEIPT_ID,
        workspace_sha=SAMPLE_WORKSPACE_SHA,
        workspace_tree_oid=SAMPLE_TREE_OID,
        plan_core_sha256=SAMPLE_PLAN_SHA,
        agent_id="agent-1",
        run_id="run-1",
    )
    store.write_land_receipt(receipt)

    index_path = tmp_path / "store" / "index.jsonl"
    index_path.unlink()
    store.rebuild_index()

    reloaded = store.query_land_receipt_by_landed_sha(SAMPLE_LANDED_SHA)
    assert reloaded is not None
    assert reloaded["receipt_id"] == receipt["receipt_id"]


def test_query_land_receipts_for_workspace_filters_plan_core(tmp_path):
    store = ReceiptStore(tmp_path / "store")
    plan_a = "a" * 64
    plan_b = "b" * 64

    receipt_a = build_land_receipt(
        landed_sha="1111111111111111111111111111111111111111",
        landed_tree_oid=SAMPLE_TREE_OID,
        land_target="refs/heads/main",
        merge_method="squash",
        acceptance_receipt_id=SAMPLE_ACCEPTANCE_RECEIPT_ID,
        workspace_sha=SAMPLE_WORKSPACE_SHA,
        workspace_tree_oid=SAMPLE_TREE_OID,
        plan_core_sha256=plan_a,
        agent_id="agent-a",
        run_id="run-a",
    )
    receipt_b = build_land_receipt(
        landed_sha="2222222222222222222222222222222222222222",
        landed_tree_oid=SAMPLE_TREE_OID,
        land_target="refs/heads/main",
        merge_method="squash",
        acceptance_receipt_id=SAMPLE_ACCEPTANCE_RECEIPT_ID,
        workspace_sha=SAMPLE_WORKSPACE_SHA,
        workspace_tree_oid=SAMPLE_TREE_OID,
        plan_core_sha256=plan_b,
        agent_id="agent-b",
        run_id="run-b",
    )
    store.write_land_receipt(receipt_a)
    store.write_land_receipt(receipt_b)

    filtered = store.query_land_receipts_for_workspace(
        SAMPLE_WORKSPACE_SHA, plan_core_sha256=plan_a
    )
    assert len(filtered) == 1
    assert filtered[0]["acceptance_lineage"]["plan_core_sha256"] == plan_a
