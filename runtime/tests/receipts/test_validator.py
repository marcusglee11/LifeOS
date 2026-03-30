"""Tests for runtime/receipts/validator.py"""

import pytest

from runtime.receipts.validator import (
    ReceiptValidationError,
    assert_valid,
    validate_artefact,
)

VALID_RECEIPT = {
    "receipt_id": "01HZZZZZZZZZZZZZZZZZZZZZZZ",
    "schema_version": "2.4",
    "workspace_sha": "abc123",
    "workspace_tree_oid": "a" * 40,
    "plan_core_sha256": "b" * 64,
    "issued_at": "2026-01-01T00:00:00Z",
    "policy_pack": {"policy_id": "pilot-default"},
    "decision": {"status": "ACCEPTED"},
}


def test_validate_valid_acceptance_receipt():
    errors = validate_artefact(VALID_RECEIPT, "acceptance_receipt")
    assert errors == []


def test_validate_invalid_acceptance_receipt():
    bad = {"receipt_id": "bad"}
    errors = validate_artefact(bad, "acceptance_receipt")
    assert len(errors) > 0


def test_assert_valid_raises_on_invalid():
    with pytest.raises(ReceiptValidationError) as exc_info:
        assert_valid({"bad": "data"}, "acceptance_receipt")
    assert exc_info.value.errors


def test_assert_valid_passes_on_valid():
    assert_valid(VALID_RECEIPT, "acceptance_receipt")  # Should not raise


def test_validate_catches_invalid_pattern():
    bad_receipt = {**VALID_RECEIPT, "receipt_id": "lowercase-bad-id!!!"}
    errors = validate_artefact(bad_receipt, "acceptance_receipt")
    assert any("does not match" in e.lower() or "receipt_id" in e.lower() for e in errors)


def test_validate_conditional_reason_code():
    # ACCEPTED with reason_code should fail
    bad_accepted = {**VALID_RECEIPT, "decision": {"status": "ACCEPTED", "reason_code": "X"}}
    errors = validate_artefact(bad_accepted, "acceptance_receipt")
    assert len(errors) > 0, "ACCEPTED with reason_code should fail"

    # REJECTED without reason_code should fail
    bad_rejected = {**VALID_RECEIPT, "decision": {"status": "REJECTED"}}
    errors = validate_artefact(bad_rejected, "acceptance_receipt")
    assert len(errors) > 0, "REJECTED without reason_code should fail"

    # REJECTED with reason_code should pass
    good_rejected = {
        **VALID_RECEIPT,
        "decision": {"status": "REJECTED", "reason_code": "GATE_FAIL"},
    }
    errors = validate_artefact(good_rejected, "acceptance_receipt")
    assert errors == [], f"REJECTED with reason_code should pass, got: {errors}"


def test_validate_enforces_datetime_format():
    bad = {**VALID_RECEIPT, "issued_at": "not-a-datetime"}
    errors = validate_artefact(bad, "acceptance_receipt")
    assert any("date-time" in e for e in errors)
