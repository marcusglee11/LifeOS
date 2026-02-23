"""Tests for runtime/receipts/schemas.py"""
import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError


from runtime.receipts.schemas import (
    ACCEPTANCE_RECEIPT_SCHEMA,
    BLOCKED_REPORT_SCHEMA,
    LAND_RECEIPT_SCHEMA,
    GATE_RESULT_SCHEMA,
    RUNLOG_EVENT_SCHEMA,
    REVIEW_SUMMARY_SCHEMA,
)


def check_schema_valid(schema):
    Draft202012Validator.check_schema(schema)


def test_acceptance_receipt_schema_valid_jsonschema():
    check_schema_valid(ACCEPTANCE_RECEIPT_SCHEMA)


def test_land_receipt_schema_valid_jsonschema():
    check_schema_valid(LAND_RECEIPT_SCHEMA)


def test_blocked_report_schema_valid_jsonschema():
    check_schema_valid(BLOCKED_REPORT_SCHEMA)


def test_gate_result_schema_valid_jsonschema():
    check_schema_valid(GATE_RESULT_SCHEMA)


def test_runlog_event_schema_valid_jsonschema():
    check_schema_valid(RUNLOG_EVENT_SCHEMA)


def test_acceptance_schema_requires_all_fields():
    validator = Draft202012Validator(ACCEPTANCE_RECEIPT_SCHEMA)
    errors = list(validator.iter_errors({}))
    # Should have errors for all required fields
    assert len(errors) > 0
    error_messages = " ".join(e.message for e in errors)
    assert "receipt_id" in error_messages or len(errors) >= 5


def test_acceptance_schema_rejects_invalid_receipt_id():
    validator = Draft202012Validator(ACCEPTANCE_RECEIPT_SCHEMA)
    receipt = {
        "receipt_id": "lowercase-invalid",  # lowercase is invalid
        "schema_version": "2.4",
        "workspace_sha": "abc123",
        "workspace_tree_oid": "a" * 40,
        "plan_core_sha256": "b" * 64,
        "issued_at": "2026-01-01T00:00:00Z",
        "policy_pack": {"policy_id": "test"},
        "decision": {"status": "ACCEPTED"},
    }
    errors = list(validator.iter_errors(receipt))
    assert any("receipt_id" in str(e.path) or "pattern" in e.message for e in errors)


def test_acceptance_schema_accepts_valid_receipt():
    validator = Draft202012Validator(ACCEPTANCE_RECEIPT_SCHEMA)
    receipt = {
        "receipt_id": "01HZZZZZZZZZZZZZZZZZZZZZZZ",
        "schema_version": "2.4",
        "workspace_sha": "abc123def456",
        "workspace_tree_oid": "a" * 40,
        "plan_core_sha256": "b" * 64,
        "issued_at": "2026-01-01T00:00:00Z",
        "policy_pack": {"policy_id": "pilot-default"},
        "decision": {"status": "ACCEPTED"},
    }
    errors = list(validator.iter_errors(receipt))
    assert errors == [], f"Expected valid receipt, got errors: {[e.message for e in errors]}"


def test_acceptance_schema_rejects_extra_properties():
    validator = Draft202012Validator(ACCEPTANCE_RECEIPT_SCHEMA)
    receipt = {
        "receipt_id": "01HZZZZZZZZZZZZZZZZZZZZZZZ",
        "schema_version": "2.4",
        "workspace_sha": "abc123",
        "workspace_tree_oid": "a" * 40,
        "plan_core_sha256": "b" * 64,
        "issued_at": "2026-01-01T00:00:00Z",
        "policy_pack": {"policy_id": "test"},
        "decision": {"status": "ACCEPTED"},
        "unknown_extra_field": "should be rejected",
    }
    errors = list(validator.iter_errors(receipt))
    assert any("unknown_extra_field" in e.message for e in errors)


def test_acceptance_schema_allows_ext():
    validator = Draft202012Validator(ACCEPTANCE_RECEIPT_SCHEMA)
    receipt = {
        "receipt_id": "01HZZZZZZZZZZZZZZZZZZZZZZZ",
        "schema_version": "2.4",
        "workspace_sha": "abc123",
        "workspace_tree_oid": "a" * 40,
        "plan_core_sha256": "b" * 64,
        "issued_at": "2026-01-01T00:00:00Z",
        "policy_pack": {"policy_id": "test"},
        "decision": {"status": "ACCEPTED"},
        "_ext": {"custom_field": "allowed"},
    }
    errors = list(validator.iter_errors(receipt))
    assert errors == [], f"Expected _ext to be allowed, got: {[e.message for e in errors]}"


def test_acceptance_conditional_reason_code_rejected():
    """REJECTED status MUST have reason_code"""
    validator = Draft202012Validator(ACCEPTANCE_RECEIPT_SCHEMA)
    receipt = {
        "receipt_id": "01HZZZZZZZZZZZZZZZZZZZZZZZ",
        "schema_version": "2.4",
        "workspace_sha": "abc123",
        "workspace_tree_oid": "a" * 40,
        "plan_core_sha256": "b" * 64,
        "issued_at": "2026-01-01T00:00:00Z",
        "policy_pack": {"policy_id": "test"},
        "decision": {"status": "REJECTED"},  # Missing reason_code
    }
    errors = list(validator.iter_errors(receipt))
    assert len(errors) > 0, "Expected validation error for REJECTED without reason_code"


def test_acceptance_conditional_reason_code_accepted():
    """ACCEPTED status MUST NOT have reason_code"""
    validator = Draft202012Validator(ACCEPTANCE_RECEIPT_SCHEMA)
    receipt = {
        "receipt_id": "01HZZZZZZZZZZZZZZZZZZZZZZZ",
        "schema_version": "2.4",
        "workspace_sha": "abc123",
        "workspace_tree_oid": "a" * 40,
        "plan_core_sha256": "b" * 64,
        "issued_at": "2026-01-01T00:00:00Z",
        "policy_pack": {"policy_id": "test"},
        "decision": {"status": "ACCEPTED", "reason_code": "should_not_be_here"},
    }
    errors = list(validator.iter_errors(receipt))
    assert len(errors) > 0, "Expected validation error for ACCEPTED with reason_code"
