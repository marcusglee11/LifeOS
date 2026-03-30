"""Tests for runtime/receipts/receipt_emitter.py"""

import re

import pytest

from runtime.receipts.receipt_emitter import (
    build_acceptance_receipt,
    build_blocked_report,
    build_review_summary,
    compute_decision,
)
from runtime.receipts.runlog import RunLogEmitter
from runtime.receipts.validator import ReceiptValidationError, validate_artefact

ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

SAMPLE_WORKSPACE_SHA = "abc123def456abc123def456abc123def456abc1"
SAMPLE_TREE_OID = "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
SAMPLE_PLAN_SHA = "b" * 64


@pytest.fixture
def sample_emitter():
    return RunLogEmitter(phase_order=["init", "build"])


@pytest.fixture
def pass_rollup():
    return {"overall_status": "PASS"}


@pytest.fixture
def fail_rollup():
    return {"overall_status": "FAIL"}


@pytest.fixture
def blocked_rollup():
    return {"overall_status": "BLOCKED"}


def test_acceptance_receipt_valid_schema(sample_emitter, pass_rollup):
    decision = compute_decision(pass_rollup)
    receipt = build_acceptance_receipt(
        SAMPLE_WORKSPACE_SHA,
        SAMPLE_TREE_OID,
        SAMPLE_PLAN_SHA,
        sample_emitter,
        decision,
        pass_rollup,
    )
    errors = validate_artefact(receipt, "acceptance_receipt")
    assert errors == [], f"Expected valid receipt, got: {errors}"


def test_acceptance_receipt_has_tree_oid(sample_emitter, pass_rollup):
    decision = compute_decision(pass_rollup)
    receipt = build_acceptance_receipt(
        SAMPLE_WORKSPACE_SHA,
        SAMPLE_TREE_OID,
        SAMPLE_PLAN_SHA,
        sample_emitter,
        decision,
        pass_rollup,
    )
    assert receipt["workspace_tree_oid"] == SAMPLE_TREE_OID


def test_acceptance_receipt_has_id_and_timestamp(sample_emitter, pass_rollup):
    decision = compute_decision(pass_rollup)
    receipt = build_acceptance_receipt(
        SAMPLE_WORKSPACE_SHA,
        SAMPLE_TREE_OID,
        SAMPLE_PLAN_SHA,
        sample_emitter,
        decision,
        pass_rollup,
    )
    assert ULID_PATTERN.match(receipt["receipt_id"])
    assert receipt["issued_at"].endswith("+00:00") or receipt["issued_at"].endswith("Z")


def test_acceptance_receipt_accepted_has_no_reason(sample_emitter, pass_rollup):
    decision = compute_decision(pass_rollup)
    assert decision["status"] == "ACCEPTED"
    assert "reason_code" not in decision
    receipt = build_acceptance_receipt(
        SAMPLE_WORKSPACE_SHA,
        SAMPLE_TREE_OID,
        SAMPLE_PLAN_SHA,
        sample_emitter,
        decision,
        pass_rollup,
    )
    assert "reason_code" not in receipt["decision"]


def test_acceptance_receipt_decision_from_fail_rollup(sample_emitter, fail_rollup):
    decision = compute_decision(fail_rollup)
    receipt = build_acceptance_receipt(
        SAMPLE_WORKSPACE_SHA,
        SAMPLE_TREE_OID,
        SAMPLE_PLAN_SHA,
        sample_emitter,
        decision,
        fail_rollup,
    )
    assert receipt["decision"]["status"] == "REJECTED"
    assert receipt["decision"]["reason_code"] == "GATE_FAIL"


def test_compute_decision_accepted_from_pass(pass_rollup):
    d = compute_decision(pass_rollup)
    assert d["status"] == "ACCEPTED"
    assert "reason_code" not in d


def test_compute_decision_rejected_from_fail(fail_rollup):
    d = compute_decision(fail_rollup)
    assert d["status"] == "REJECTED"
    assert d["reason_code"] == "GATE_FAIL"


def test_compute_decision_blocked_from_blocked(blocked_rollup):
    d = compute_decision(blocked_rollup)
    assert d["status"] == "BLOCKED"
    assert d["reason_code"] == "BLOCKED_GATES"


def test_blocked_report_valid_schema():
    report = build_blocked_report(
        SAMPLE_WORKSPACE_SHA,
        SAMPLE_PLAN_SHA,
        reason_code="PREREQ_FAIL",
    )
    errors = validate_artefact(report, "blocked_report")
    assert errors == [], f"Expected valid report, got: {errors}"


def test_blocked_report_has_required_fields():
    report = build_blocked_report(
        SAMPLE_WORKSPACE_SHA,
        SAMPLE_PLAN_SHA,
        reason_code="PREREQ_FAIL",
    )
    assert ULID_PATTERN.match(report["report_id"])
    assert report["schema_version"] == "2.4"
    assert report["reason_code"] == "PREREQ_FAIL"


def test_acceptance_receipt_with_supersedes(sample_emitter, pass_rollup):
    decision = compute_decision(pass_rollup)
    # First receipt
    r1 = build_acceptance_receipt(
        SAMPLE_WORKSPACE_SHA,
        SAMPLE_TREE_OID,
        SAMPLE_PLAN_SHA,
        sample_emitter,
        decision,
        pass_rollup,
    )
    # Second supersedes first
    r2 = build_acceptance_receipt(
        SAMPLE_WORKSPACE_SHA,
        SAMPLE_TREE_OID,
        SAMPLE_PLAN_SHA,
        sample_emitter,
        decision,
        pass_rollup,
        supersedes=r1["receipt_id"],
    )
    assert r2["supersedes"] == r1["receipt_id"]
    errors = validate_artefact(r2, "acceptance_receipt")
    assert errors == []


def test_review_summary_deterministic(pass_rollup):
    s1 = build_review_summary(pass_rollup)
    s2 = build_review_summary(pass_rollup)
    assert s1 == s2


def test_compute_decision_rejects_unknown_status():
    with pytest.raises(ValueError, match="Unknown gate_rollup overall_status"):
        compute_decision({"overall_status": "MAYBE"})


def test_acceptance_receipt_does_not_fallback_invalid_policy_pack(sample_emitter, pass_rollup):
    decision = compute_decision(pass_rollup)
    with pytest.raises(ReceiptValidationError):
        build_acceptance_receipt(
            SAMPLE_WORKSPACE_SHA,
            SAMPLE_TREE_OID,
            SAMPLE_PLAN_SHA,
            sample_emitter,
            decision,
            pass_rollup,
            policy_pack={},
        )
