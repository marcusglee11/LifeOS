"""Tests for runtime/receipts/pre_merge.py — Phase B enforcement."""
from __future__ import annotations
import pytest


# ── Task 1: Policy version ────────────────────────────────────────────────

def test_pilot_policy_has_policy_version():
    from runtime.receipts.receipt_emitter import PILOT_POLICY
    assert "policy_version" in PILOT_POLICY, "Phase B: PILOT_POLICY must carry policy_version"


def test_pilot_policy_version_is_string():
    from runtime.receipts.receipt_emitter import PILOT_POLICY
    assert isinstance(PILOT_POLICY["policy_version"], str)
    assert len(PILOT_POLICY["policy_version"]) > 0


def test_built_receipt_carries_policy_version(
    sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256
):
    from runtime.receipts.receipt_emitter import build_acceptance_receipt, compute_decision
    from runtime.receipts.runlog import RunLogEmitter
    emitter = RunLogEmitter(phase_order=["init"])
    decision = compute_decision({"overall_status": "PASS"})
    receipt = build_acceptance_receipt(
        sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256,
        emitter, decision, {"overall_status": "PASS"},
    )
    assert "policy_version" in receipt["policy_pack"]


# ── Task 2: Pipeline label ────────────────────────────────────────────────

def test_pipeline_id_constant_exported():
    from runtime.receipts.receipt_emitter import PIPELINE_ID
    assert isinstance(PIPELINE_ID, str)
    assert len(PIPELINE_ID) > 0


def test_acceptance_receipt_carries_pipeline_id_in_ext(
    sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256
):
    from runtime.receipts.receipt_emitter import build_acceptance_receipt, compute_decision, PIPELINE_ID
    from runtime.receipts.runlog import RunLogEmitter
    emitter = RunLogEmitter(phase_order=["init"])
    decision = compute_decision({"overall_status": "PASS"})
    receipt = build_acceptance_receipt(
        sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256,
        emitter, decision, {"overall_status": "PASS"},
    )
    assert "_ext" in receipt
    assert receipt["_ext"].get("pipeline_id") == PIPELINE_ID


# ── Task 3: PreMergeResult dataclass ─────────────────────────────────────

def test_pre_merge_result_allowed_fields():
    from runtime.receipts.pre_merge import PreMergeResult
    r = PreMergeResult(allowed=True, reason_code="ACCEPTED", receipt={"receipt_id": "X"}, detail="ok")
    assert r.allowed is True
    assert r.reason_code == "ACCEPTED"
    assert r.receipt == {"receipt_id": "X"}
    assert r.detail == "ok"


def test_pre_merge_result_blocked_fields():
    from runtime.receipts.pre_merge import PreMergeResult
    r = PreMergeResult(allowed=False, reason_code="NO_RECEIPT", receipt=None, detail="no receipt")
    assert r.allowed is False
    assert r.receipt is None


def test_pre_merge_result_is_frozen():
    from runtime.receipts.pre_merge import PreMergeResult
    import dataclasses
    r = PreMergeResult(allowed=True, reason_code="ACCEPTED", receipt={}, detail="ok")
    assert dataclasses.is_dataclass(r)
    with pytest.raises((AttributeError, dataclasses.FrozenInstanceError)):
        r.allowed = False  # type: ignore[misc]


def test_reason_codes_are_defined_constants():
    from runtime.receipts.pre_merge import (
        RC_ACCEPTED, RC_NO_RECEIPT, RC_DECISION_NOT_ACCEPTED,
        RC_MISSING_POLICY_VERSION, RC_TREE_OID_MISMATCH, RC_STORE_ERROR,
    )
    for rc in [RC_ACCEPTED, RC_NO_RECEIPT, RC_DECISION_NOT_ACCEPTED,
               RC_MISSING_POLICY_VERSION, RC_TREE_OID_MISMATCH, RC_STORE_ERROR]:
        assert isinstance(rc, str) and len(rc) > 0


# ── Task 4: run_pre_merge_check ───────────────────────────────────────────

def _make_store_with_receipt(
    tmp_store, workspace_sha, tree_oid, plan_sha,
    decision_status="ACCEPTED", policy_version="1.0", supersedes=None
):
    """Helper: write one acceptance receipt to a tmp store, return (store, receipt)."""
    from runtime.receipts.store import ReceiptStore
    from runtime.receipts.receipt_emitter import build_acceptance_receipt
    from runtime.receipts.runlog import RunLogEmitter
    store = ReceiptStore(tmp_store)
    emitter = RunLogEmitter(phase_order=["init"])
    if decision_status == "ACCEPTED":
        rollup = {"overall_status": "PASS"}
        decision = {"status": "ACCEPTED"}
    else:
        rollup = {"overall_status": "FAIL"}
        decision = {"status": "REJECTED", "reason_code": "GATE_FAIL"}
    policy = {"policy_id": "pilot-default", "policy_version": policy_version}
    receipt = build_acceptance_receipt(
        workspace_sha, tree_oid, plan_sha,
        emitter, decision, rollup,
        policy_pack=policy, supersedes=supersedes,
    )
    store.write_acceptance_receipt(receipt)
    return store, receipt


def test_allowed_when_active_accepted_receipt_exists(
    tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256, monkeypatch
):
    import runtime.receipts.plan_core as pc
    monkeypatch.setattr(pc, "resolve_tree_oid", lambda sha, **kw: sample_workspace_tree_oid)
    from runtime.receipts.pre_merge import run_pre_merge_check, RC_ACCEPTED
    _make_store_with_receipt(tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256)
    result = run_pre_merge_check(sample_workspace_sha, sample_plan_core_sha256, tmp_store)
    assert result.allowed is True
    assert result.reason_code == RC_ACCEPTED
    assert result.receipt is not None


def test_blocked_when_no_receipt_exists(
    tmp_store, sample_workspace_sha, sample_plan_core_sha256
):
    from runtime.receipts.store import ReceiptStore
    from runtime.receipts.pre_merge import run_pre_merge_check, RC_NO_RECEIPT
    ReceiptStore(tmp_store)  # empty store
    result = run_pre_merge_check(sample_workspace_sha, sample_plan_core_sha256, tmp_store)
    assert result.allowed is False
    assert result.reason_code == RC_NO_RECEIPT
    assert result.receipt is None


def test_blocked_when_decision_is_rejected(
    tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256, monkeypatch
):
    import runtime.receipts.plan_core as pc
    monkeypatch.setattr(pc, "resolve_tree_oid", lambda sha, **kw: sample_workspace_tree_oid)
    from runtime.receipts.pre_merge import run_pre_merge_check, RC_DECISION_NOT_ACCEPTED
    _make_store_with_receipt(tmp_store, sample_workspace_sha, sample_workspace_tree_oid,
                             sample_plan_core_sha256, decision_status="REJECTED")
    result = run_pre_merge_check(sample_workspace_sha, sample_plan_core_sha256, tmp_store)
    assert result.allowed is False
    assert result.reason_code == RC_DECISION_NOT_ACCEPTED


def test_blocked_when_missing_policy_version(
    tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256, monkeypatch
):
    import runtime.receipts.plan_core as pc
    monkeypatch.setattr(pc, "resolve_tree_oid", lambda sha, **kw: sample_workspace_tree_oid)
    from runtime.receipts.store import ReceiptStore
    from runtime.receipts.receipt_emitter import build_acceptance_receipt
    from runtime.receipts.runlog import RunLogEmitter
    from runtime.receipts.pre_merge import run_pre_merge_check, RC_MISSING_POLICY_VERSION
    store = ReceiptStore(tmp_store)
    emitter = RunLogEmitter(phase_order=["init"])
    receipt = build_acceptance_receipt(
        sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256,
        emitter, {"status": "ACCEPTED"}, {"overall_status": "PASS"},
        policy_pack={"policy_id": "pilot-default"},  # no policy_version
    )
    store.write_acceptance_receipt(receipt)
    result = run_pre_merge_check(sample_workspace_sha, sample_plan_core_sha256, tmp_store)
    assert result.allowed is False
    assert result.reason_code == RC_MISSING_POLICY_VERSION


def test_blocked_when_tree_oid_mismatches(
    tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256, monkeypatch
):
    import runtime.receipts.plan_core as pc
    different_oid = "0" * 40
    assert different_oid != sample_workspace_tree_oid
    monkeypatch.setattr(pc, "resolve_tree_oid", lambda sha, **kw: different_oid)
    from runtime.receipts.pre_merge import run_pre_merge_check, RC_TREE_OID_MISMATCH
    _make_store_with_receipt(tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256)
    result = run_pre_merge_check(sample_workspace_sha, sample_plan_core_sha256, tmp_store)
    assert result.allowed is False
    assert result.reason_code == RC_TREE_OID_MISMATCH


def test_tree_oid_verification_passes_when_matches(
    tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256, monkeypatch
):
    import runtime.receipts.plan_core as pc
    monkeypatch.setattr(pc, "resolve_tree_oid", lambda sha, **kw: sample_workspace_tree_oid)
    from runtime.receipts.pre_merge import run_pre_merge_check
    _make_store_with_receipt(tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256)
    result = run_pre_merge_check(sample_workspace_sha, sample_plan_core_sha256, tmp_store)
    assert result.allowed is True


def test_fail_closed_when_store_root_missing(
    tmp_path, sample_workspace_sha, sample_plan_core_sha256
):
    from runtime.receipts.pre_merge import run_pre_merge_check, RC_STORE_ERROR
    result = run_pre_merge_check(sample_workspace_sha, sample_plan_core_sha256, tmp_path / "no_such_store")
    assert result.allowed is False
    assert result.reason_code == RC_STORE_ERROR


def test_fail_closed_on_resolve_tree_oid_error(
    tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256, monkeypatch
):
    import runtime.receipts.plan_core as pc
    monkeypatch.setattr(pc, "resolve_tree_oid", lambda sha, **kw: (_ for _ in ()).throw(ValueError("git unavailable")))
    from runtime.receipts.pre_merge import run_pre_merge_check, RC_STORE_ERROR
    _make_store_with_receipt(tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256)
    result = run_pre_merge_check(sample_workspace_sha, sample_plan_core_sha256, tmp_store)
    assert result.allowed is False
    assert result.reason_code == RC_STORE_ERROR


def test_result_includes_receipt_on_allow(
    tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256, monkeypatch
):
    import runtime.receipts.plan_core as pc
    monkeypatch.setattr(pc, "resolve_tree_oid", lambda sha, **kw: sample_workspace_tree_oid)
    from runtime.receipts.pre_merge import run_pre_merge_check
    _, receipt = _make_store_with_receipt(tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256)
    result = run_pre_merge_check(sample_workspace_sha, sample_plan_core_sha256, tmp_store)
    assert result.receipt is not None
    assert result.receipt["receipt_id"] == receipt["receipt_id"]


def test_result_detail_nonempty_on_block(
    tmp_store, sample_workspace_sha, sample_plan_core_sha256
):
    from runtime.receipts.store import ReceiptStore
    from runtime.receipts.pre_merge import run_pre_merge_check
    ReceiptStore(tmp_store)
    result = run_pre_merge_check(sample_workspace_sha, sample_plan_core_sha256, tmp_store)
    assert not result.allowed
    assert len(result.detail) > 0


# ── Task 5: Package exports ───────────────────────────────────────────────

def test_pre_merge_exports_from_package():
    from runtime.receipts import PreMergeResult, run_pre_merge_check
    assert callable(run_pre_merge_check)
    assert PreMergeResult is not None


# ── Task 6: CLI script ────────────────────────────────────────────────────

import subprocess, sys, json, os

SCRIPT = "/mnt/c/Users/cabra/Projects/LifeOS/.worktrees/build/receipts-phase-a/scripts/receipts_pre_merge_check.py"


def test_cli_exits_1_when_no_receipt(tmp_path, sample_workspace_sha, sample_plan_core_sha256):
    from runtime.receipts.store import ReceiptStore
    store_dir = tmp_path / "store"
    ReceiptStore(store_dir)
    r = subprocess.run(
        [sys.executable, SCRIPT, "--workspace-sha", sample_workspace_sha,
         "--plan-sha", sample_plan_core_sha256, "--store", str(store_dir)],
        capture_output=True, text=True,
    )
    assert r.returncode == 1
    out = json.loads(r.stdout)
    assert out["allowed"] is False
    assert out["reason_code"] == "NO_RECEIPT"


def test_cli_exits_0_when_receipt_accepted(
    tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256
):
    """Uses LIFEOS_MOCK_TREE_OID env var to bypass git in subprocess."""
    _make_store_with_receipt(tmp_store, sample_workspace_sha, sample_workspace_tree_oid, sample_plan_core_sha256)
    env = os.environ.copy()
    env["LIFEOS_MOCK_TREE_OID"] = sample_workspace_tree_oid
    r = subprocess.run(
        [sys.executable, SCRIPT, "--workspace-sha", sample_workspace_sha,
         "--plan-sha", sample_plan_core_sha256, "--store", str(tmp_store)],
        capture_output=True, text=True, env=env,
    )
    assert r.returncode == 0
    out = json.loads(r.stdout)
    assert out["allowed"] is True
    assert out["reason_code"] == "ACCEPTED"


def test_cli_outputs_valid_json(tmp_path, sample_workspace_sha, sample_plan_core_sha256):
    from runtime.receipts.store import ReceiptStore
    store_dir = tmp_path / "store"
    ReceiptStore(store_dir)
    r = subprocess.run(
        [sys.executable, SCRIPT, "--workspace-sha", sample_workspace_sha,
         "--plan-sha", sample_plan_core_sha256, "--store", str(store_dir)],
        capture_output=True, text=True,
    )
    out = json.loads(r.stdout)
    assert "allowed" in out
    assert "reason_code" in out
    assert "detail" in out
