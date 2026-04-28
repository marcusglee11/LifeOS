"""Tests for ea_receipt.v0 validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.receipts.ea_receipt import (
    EAReceiptValidationError,
    load_and_validate_ea_receipt,
    validate_ea_receipt,
)


def _valid_receipt() -> dict[str, object]:
    return {
        "schema_version": "ea_receipt.v0",
        "status": "success",
        "commands_run": ["pytest runtime/tests/receipts/test_ea_receipt.py -q"],
        "inner_exit_codes": [0],
        "files_changed": ["runtime/receipts/ea_receipt.py"],
        "tests_run": ["runtime/tests/receipts/test_ea_receipt.py"],
        "blockers": [],
    }


def test_success_receipt_valid() -> None:
    assert validate_ea_receipt(_valid_receipt()) == []


def test_failure_receipt_valid_with_blocker() -> None:
    receipt = _valid_receipt()
    receipt["status"] = "failure"
    receipt["inner_exit_codes"] = [1]
    receipt["blockers"] = ["targeted tests failed"]

    assert validate_ea_receipt(receipt) == []


def test_missing_receipt_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(EAReceiptValidationError, match="receipt not found"):
        load_and_validate_ea_receipt(tmp_path / "ea_receipt.json")


def test_malformed_json_fails_closed(tmp_path: Path) -> None:
    path = tmp_path / "ea_receipt.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(EAReceiptValidationError, match="receipt is not valid JSON"):
        load_and_validate_ea_receipt(path)


def test_missing_keys_fail() -> None:
    receipt = _valid_receipt()
    del receipt["commands_run"]

    assert validate_ea_receipt(receipt) == ["missing required field: commands_run"]


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("schema_version", "ea_receipt.v1", "schema_version must be ea_receipt.v0"),
        ("status", "blocked", "status must be one of: failure, success"),
    ],
)
def test_bad_schema_or_status_fail(field: str, value: str, expected: str) -> None:
    receipt = _valid_receipt()
    receipt[field] = value

    assert expected in validate_ea_receipt(receipt)


def test_nonzero_success_mismatch_fails() -> None:
    receipt = _valid_receipt()
    receipt["inner_exit_codes"] = [0, 2]

    assert (
        "status must be failure when any inner_exit_codes value is nonzero"
        in validate_ea_receipt(receipt)
    )


def test_failure_without_blocker_fails() -> None:
    receipt = _valid_receipt()
    receipt["status"] = "failure"

    assert "failure status requires non-empty blockers" in validate_ea_receipt(receipt)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("commands_run", ["ok", 1], "commands_run must be a list of strings"),
        ("inner_exit_codes", [False], "inner_exit_codes must be a list of integers"),
        (
            "files_changed",
            "runtime/receipts/ea_receipt.py",
            "files_changed must be a list of strings",
        ),
        ("tests_run", [None], "tests_run must be a list of strings"),
        ("blockers", [1], "blockers must be a list of strings"),
    ],
)
def test_field_type_errors(field: str, value: object, expected: str) -> None:
    receipt = _valid_receipt()
    receipt[field] = value

    assert expected in validate_ea_receipt(receipt)


def test_load_and_validate_returns_receipt(tmp_path: Path) -> None:
    receipt = _valid_receipt()
    path = tmp_path / "ea_receipt.json"
    path.write_text(json.dumps(receipt), encoding="utf-8")

    assert load_and_validate_ea_receipt(path) == receipt
