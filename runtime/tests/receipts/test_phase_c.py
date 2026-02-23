"""Tests for runtime/receipts Phase C — land receipts + reconciliation."""
from __future__ import annotations
import pytest


# ── Task 1: LAND_RECEIPT_SCHEMA ───────────────────────────────────────────

def test_land_receipt_schema_version_const():
    from runtime.receipts.schemas import LAND_RECEIPT_SCHEMA
    # v2.4 spec: schema_version const is "land_receipt.v2.4"
    const = LAND_RECEIPT_SCHEMA["properties"]["schema_version"].get("const")
    assert const == "land_receipt.v2.4", f"Expected 'land_receipt.v2.4', got {const!r}"


def test_land_receipt_schema_required_fields():
    from runtime.receipts.schemas import LAND_RECEIPT_SCHEMA
    required = set(LAND_RECEIPT_SCHEMA["required"])
    expected = {"receipt_id", "schema_version", "receipt_type", "created_at",
                "landed_sha", "landed_tree_oid", "land_target", "merge_method",
                "acceptance_lineage", "emitter"}
    assert expected.issubset(required), f"Missing required fields: {expected - required}"


def test_land_receipt_schema_has_tree_equivalence_property():
    from runtime.receipts.schemas import LAND_RECEIPT_SCHEMA
    assert "tree_equivalence" in LAND_RECEIPT_SCHEMA["properties"]


def test_land_receipt_schema_acceptance_lineage_required():
    from runtime.receipts.schemas import LAND_RECEIPT_SCHEMA
    lineage = LAND_RECEIPT_SCHEMA["properties"]["acceptance_lineage"]
    req = set(lineage["required"])
    assert {"acceptance_receipt_id", "workspace_sha", "workspace_tree_oid", "plan_core_sha256"}.issubset(req)


# ── Task 2: build_land_receipt ────────────────────────────────────────────

_SAMPLE_ACCEPTANCE_RECEIPT_ID = "01HN2P8QVKXJZ3MRSF4T6WBYDE"
_SAMPLE_WORKSPACE_SHA = "abc123def456abc123def456abc123def456abc1"
_SAMPLE_WORKSPACE_TREE_OID = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
_SAMPLE_LANDED_SHA = "cafe0000cafe0000cafe0000cafe0000cafe0000"
_SAMPLE_PLAN_CORE_SHA256 = "a" * 64


def test_build_land_receipt_schema_valid():
    from runtime.receipts.receipt_emitter import build_land_receipt
    receipt = build_land_receipt(
        landed_sha=_SAMPLE_LANDED_SHA,
        landed_tree_oid=_SAMPLE_WORKSPACE_TREE_OID,  # same = match
        land_target="refs/heads/main",
        merge_method="squash",
        acceptance_receipt_id=_SAMPLE_ACCEPTANCE_RECEIPT_ID,
        workspace_sha=_SAMPLE_WORKSPACE_SHA,
        workspace_tree_oid=_SAMPLE_WORKSPACE_TREE_OID,
        plan_core_sha256=_SAMPLE_PLAN_CORE_SHA256,
        agent_id="test-agent",
        run_id="run-001",
    )
    from runtime.receipts.validator import assert_valid
    assert_valid(receipt, "land_receipt")  # should not raise


def test_build_land_receipt_tree_equivalence_match_true():
    from runtime.receipts.receipt_emitter import build_land_receipt
    receipt = build_land_receipt(
        landed_sha=_SAMPLE_LANDED_SHA,
        landed_tree_oid=_SAMPLE_WORKSPACE_TREE_OID,
        land_target="refs/heads/main",
        merge_method="squash",
        acceptance_receipt_id=_SAMPLE_ACCEPTANCE_RECEIPT_ID,
        workspace_sha=_SAMPLE_WORKSPACE_SHA,
        workspace_tree_oid=_SAMPLE_WORKSPACE_TREE_OID,
        plan_core_sha256=_SAMPLE_PLAN_CORE_SHA256,
        agent_id="test-agent",
        run_id="run-001",
    )
    assert receipt["tree_equivalence"]["match"] is True
    assert receipt["tree_equivalence"]["verified_by"] == "land_emitter"


def test_build_land_receipt_tree_equivalence_match_false():
    from runtime.receipts.receipt_emitter import build_land_receipt
    different_oid = "0" * 40
    receipt = build_land_receipt(
        landed_sha=_SAMPLE_LANDED_SHA,
        landed_tree_oid=different_oid,
        land_target="refs/heads/main",
        merge_method="merge",
        acceptance_receipt_id=_SAMPLE_ACCEPTANCE_RECEIPT_ID,
        workspace_sha=_SAMPLE_WORKSPACE_SHA,
        workspace_tree_oid=_SAMPLE_WORKSPACE_TREE_OID,
        plan_core_sha256=_SAMPLE_PLAN_CORE_SHA256,
        agent_id="test-agent",
        run_id="run-001",
    )
    assert receipt["tree_equivalence"]["match"] is False


def test_build_land_receipt_required_fields_present():
    from runtime.receipts.receipt_emitter import build_land_receipt
    receipt = build_land_receipt(
        landed_sha=_SAMPLE_LANDED_SHA,
        landed_tree_oid=_SAMPLE_WORKSPACE_TREE_OID,
        land_target="refs/heads/main",
        merge_method="squash",
        acceptance_receipt_id=_SAMPLE_ACCEPTANCE_RECEIPT_ID,
        workspace_sha=_SAMPLE_WORKSPACE_SHA,
        workspace_tree_oid=_SAMPLE_WORKSPACE_TREE_OID,
        plan_core_sha256=_SAMPLE_PLAN_CORE_SHA256,
        agent_id="test-agent",
        run_id="run-001",
    )
    assert receipt["schema_version"] == "land_receipt.v2.4"
    assert receipt["receipt_type"] == "land"
    assert "receipt_id" in receipt
    assert "created_at" in receipt
    assert receipt["acceptance_lineage"]["acceptance_receipt_id"] == _SAMPLE_ACCEPTANCE_RECEIPT_ID


# ── Task 3: Store land receipt methods ───────────────────────────────────

def test_write_and_query_land_receipt(tmp_store):
    from runtime.receipts.store import ReceiptStore
    from runtime.receipts.receipt_emitter import build_land_receipt
    store = ReceiptStore(tmp_store)
    receipt = build_land_receipt(
        landed_sha=_SAMPLE_LANDED_SHA,
        landed_tree_oid=_SAMPLE_WORKSPACE_TREE_OID,
        land_target="refs/heads/main",
        merge_method="squash",
        acceptance_receipt_id=_SAMPLE_ACCEPTANCE_RECEIPT_ID,
        workspace_sha=_SAMPLE_WORKSPACE_SHA,
        workspace_tree_oid=_SAMPLE_WORKSPACE_TREE_OID,
        plan_core_sha256=_SAMPLE_PLAN_CORE_SHA256,
        agent_id="agent-1",
        run_id="run-1",
    )
    store.write_land_receipt(receipt)
    result = store.query_land_receipt_by_landed_sha(_SAMPLE_LANDED_SHA)
    assert result is not None
    assert result["receipt_id"] == receipt["receipt_id"]


def test_query_land_receipt_returns_none_when_absent(tmp_store):
    from runtime.receipts.store import ReceiptStore
    store = ReceiptStore(tmp_store)
    result = store.query_land_receipt_by_landed_sha("0" * 40)
    assert result is None


def test_write_land_receipt_is_append_only(tmp_store):
    """Second write for same receipt_id must raise."""
    from runtime.receipts.store import ReceiptStore
    from runtime.receipts.receipt_emitter import build_land_receipt
    store = ReceiptStore(tmp_store)
    receipt = build_land_receipt(
        landed_sha=_SAMPLE_LANDED_SHA, landed_tree_oid=_SAMPLE_WORKSPACE_TREE_OID,
        land_target="refs/heads/main", merge_method="squash",
        acceptance_receipt_id=_SAMPLE_ACCEPTANCE_RECEIPT_ID,
        workspace_sha=_SAMPLE_WORKSPACE_SHA, workspace_tree_oid=_SAMPLE_WORKSPACE_TREE_OID,
        plan_core_sha256=_SAMPLE_PLAN_CORE_SHA256,
        agent_id="agent-1", run_id="run-1",
    )
    store.write_land_receipt(receipt)
    with pytest.raises(Exception):
        store.write_land_receipt(receipt)  # duplicate write must fail


# ── Task 4: run_post_merge_land_gate ──────────────────────────────────────

def _write_acceptance_receipt_to_store(tmp_store):
    """Helper: seed an acceptance receipt for post-merge tests."""
    from runtime.receipts.store import ReceiptStore
    from datetime import datetime, timezone
    store = ReceiptStore(tmp_store)
    receipt = {
        "receipt_id": _SAMPLE_ACCEPTANCE_RECEIPT_ID,
        "schema_version": "2.4",
        "workspace_sha": _SAMPLE_WORKSPACE_SHA,
        "workspace_tree_oid": _SAMPLE_WORKSPACE_TREE_OID,
        "plan_core_sha256": _SAMPLE_PLAN_CORE_SHA256,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "policy_pack": {"policy_id": "pilot-default", "policy_version": "1.0"},
        "decision": {"status": "ACCEPTED"},
        "gate_rollup": {"overall_status": "PASS"},
        "_ext": {"pipeline_id": "lifeos-receipts-pilot-b1"},
    }
    store.write_acceptance_receipt(receipt)
    return store


def test_post_merge_gate_emits_land_receipt(tmp_store, monkeypatch):
    import runtime.receipts.plan_core as pc
    monkeypatch.setattr(pc, "resolve_tree_oid", lambda sha, **kw: _SAMPLE_WORKSPACE_TREE_OID)
    _write_acceptance_receipt_to_store(tmp_store)
    from runtime.receipts.post_merge import run_post_merge_land_gate
    result = run_post_merge_land_gate(
        landed_sha=_SAMPLE_LANDED_SHA,
        land_target="refs/heads/main",
        merge_method="squash",
        acceptance_receipt_id=_SAMPLE_ACCEPTANCE_RECEIPT_ID,
        store_root=tmp_store,
        agent_id="test-agent",
        run_id="run-1",
    )
    assert result.emitted is True
    assert result.land_receipt is not None
    assert result.land_receipt["tree_equivalence"]["match"] is True


def test_post_merge_gate_blocked_when_acceptance_receipt_missing(tmp_store):
    from runtime.receipts.store import ReceiptStore
    ReceiptStore(tmp_store)  # empty store
    from runtime.receipts.post_merge import run_post_merge_land_gate
    result = run_post_merge_land_gate(
        landed_sha=_SAMPLE_LANDED_SHA,
        land_target="refs/heads/main",
        merge_method="squash",
        acceptance_receipt_id=_SAMPLE_ACCEPTANCE_RECEIPT_ID,
        store_root=tmp_store,
        agent_id="test-agent",
        run_id="run-1",
    )
    assert result.emitted is False
    assert result.error_code == "ACCEPTANCE_RECEIPT_NOT_FOUND"


def test_post_merge_gate_records_tree_mismatch(tmp_store, monkeypatch):
    """match=False when git resolves different tree than workspace."""
    import runtime.receipts.plan_core as pc
    different_oid = "f" * 40
    monkeypatch.setattr(pc, "resolve_tree_oid", lambda sha, **kw: different_oid)
    _write_acceptance_receipt_to_store(tmp_store)
    from runtime.receipts.post_merge import run_post_merge_land_gate
    result = run_post_merge_land_gate(
        landed_sha=_SAMPLE_LANDED_SHA,
        land_target="refs/heads/main",
        merge_method="merge",
        acceptance_receipt_id=_SAMPLE_ACCEPTANCE_RECEIPT_ID,
        store_root=tmp_store,
        agent_id="test-agent",
        run_id="run-1",
    )
    # emitted=True even for mismatch — receipt is written; reconciliation flags it
    assert result.emitted is True
    assert result.land_receipt["tree_equivalence"]["match"] is False


def test_post_merge_result_is_frozen():
    from runtime.receipts.post_merge import PostMergeLandResult
    import dataclasses
    r = PostMergeLandResult(emitted=True, land_receipt={}, error_code=None, detail="ok")
    assert dataclasses.is_dataclass(r)
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
        r.emitted = False  # type: ignore[misc]


# ── Task 5: Reconciliation ────────────────────────────────────────────────

def test_reconciliation_compliant_when_land_receipt_exists_with_match(tmp_store, monkeypatch):
    import runtime.receipts.plan_core as pc
    monkeypatch.setattr(pc, "resolve_tree_oid", lambda sha, **kw: _SAMPLE_WORKSPACE_TREE_OID)
    _write_acceptance_receipt_to_store(tmp_store)
    from runtime.receipts.post_merge import run_post_merge_land_gate
    run_post_merge_land_gate(
        landed_sha=_SAMPLE_LANDED_SHA, land_target="refs/heads/main",
        merge_method="squash", acceptance_receipt_id=_SAMPLE_ACCEPTANCE_RECEIPT_ID,
        store_root=tmp_store, agent_id="a", run_id="r",
    )
    from runtime.receipts.reconciliation import run_reconciliation
    report = run_reconciliation([_SAMPLE_LANDED_SHA], store_root=tmp_store)
    assert report.total_checked == 1
    assert report.compliant == 1
    assert report.bypasses == 0
    assert report.violations == 0


def test_reconciliation_bypass_when_no_land_receipt(tmp_store):
    from runtime.receipts.store import ReceiptStore
    ReceiptStore(tmp_store)
    from runtime.receipts.reconciliation import run_reconciliation
    report = run_reconciliation([_SAMPLE_LANDED_SHA], store_root=tmp_store)
    assert report.bypasses == 1
    assert report.compliant == 0


def test_reconciliation_violation_when_tree_mismatch(tmp_store, monkeypatch):
    import runtime.receipts.plan_core as pc
    different_oid = "f" * 40
    monkeypatch.setattr(pc, "resolve_tree_oid", lambda sha, **kw: different_oid)
    _write_acceptance_receipt_to_store(tmp_store)
    from runtime.receipts.post_merge import run_post_merge_land_gate
    run_post_merge_land_gate(
        landed_sha=_SAMPLE_LANDED_SHA, land_target="refs/heads/main",
        merge_method="merge", acceptance_receipt_id=_SAMPLE_ACCEPTANCE_RECEIPT_ID,
        store_root=tmp_store, agent_id="a", run_id="r",
    )
    from runtime.receipts.reconciliation import run_reconciliation
    report = run_reconciliation([_SAMPLE_LANDED_SHA], store_root=tmp_store)
    assert report.violations == 1
    assert report.compliant == 0


def test_reconciliation_report_is_frozen():
    from runtime.receipts.reconciliation import ReconciliationReport
    import dataclasses
    r = ReconciliationReport(total_checked=0, compliant=0, bypasses=0, violations=0, findings=[], mode="audit")
    assert dataclasses.is_dataclass(r)
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
        r.total_checked = 1  # type: ignore[misc]


def test_reconciliation_mode_defaults_to_audit(tmp_store):
    from runtime.receipts.store import ReceiptStore
    ReceiptStore(tmp_store)
    from runtime.receipts.reconciliation import run_reconciliation
    report = run_reconciliation([], store_root=tmp_store)
    assert report.mode == "audit"


# ── Task 6: CLI + exports ─────────────────────────────────────────────────

import subprocess
import sys
import json
import os

LAND_SCRIPT = "/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/build/receipts-phase-a/scripts/receipts_post_merge_land.py"


def test_package_exports():
    from runtime.receipts import (
        PostMergeLandResult, run_post_merge_land_gate,
        ReconciliationReport, run_reconciliation,
        build_land_receipt,
    )
    assert callable(run_post_merge_land_gate)
    assert callable(run_reconciliation)
    assert callable(build_land_receipt)


def test_cli_exits_1_when_acceptance_receipt_missing(tmp_path):
    from runtime.receipts.store import ReceiptStore
    store_dir = tmp_path / "store"
    ReceiptStore(store_dir)
    r = subprocess.run(
        [sys.executable, LAND_SCRIPT,
         "--landed-sha", _SAMPLE_LANDED_SHA,
         "--land-target", "refs/heads/main",
         "--merge-method", "squash",
         "--acceptance-receipt-id", _SAMPLE_ACCEPTANCE_RECEIPT_ID,
         "--store", str(store_dir),
         "--agent-id", "test", "--run-id", "r1"],
        capture_output=True, text=True,
    )
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["emitted"] is False


def test_cli_exits_0_when_land_receipt_emitted(tmp_path):
    store_dir = tmp_path / "store"
    from runtime.receipts.store import ReceiptStore
    from datetime import datetime, timezone
    store = ReceiptStore(store_dir)
    receipt = {
        "receipt_id": _SAMPLE_ACCEPTANCE_RECEIPT_ID,
        "schema_version": "2.4",
        "workspace_sha": _SAMPLE_WORKSPACE_SHA,
        "workspace_tree_oid": _SAMPLE_WORKSPACE_TREE_OID,
        "plan_core_sha256": _SAMPLE_PLAN_CORE_SHA256,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "policy_pack": {"policy_id": "pilot-default", "policy_version": "1.0"},
        "decision": {"status": "ACCEPTED"},
        "gate_rollup": {"overall_status": "PASS"},
        "_ext": {"pipeline_id": "lifeos-receipts-pilot-b1"},
    }
    store.write_acceptance_receipt(receipt)
    env = os.environ.copy()
    env["LIFEOS_MOCK_TREE_OID"] = _SAMPLE_WORKSPACE_TREE_OID
    r = subprocess.run(
        [sys.executable, LAND_SCRIPT,
         "--landed-sha", _SAMPLE_LANDED_SHA,
         "--land-target", "refs/heads/main",
         "--merge-method", "squash",
         "--acceptance-receipt-id", _SAMPLE_ACCEPTANCE_RECEIPT_ID,
         "--store", str(store_dir),
         "--agent-id", "test", "--run-id", "r1"],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["emitted"] is True
