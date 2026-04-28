"""Validator for EA worker receipts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

EA_RECEIPT_SCHEMA_VERSION = "ea_receipt.v0"
EA_RECEIPT_REQUIRED_FIELDS = (
    "schema_version",
    "status",
    "commands_run",
    "inner_exit_codes",
    "files_changed",
    "tests_run",
    "blockers",
)
EA_RECEIPT_STATUSES = {"success", "failure"}


class EAReceiptValidationError(Exception):
    """Raised when an EA receipt is missing or invalid."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("Invalid EA receipt:\n" + "\n".join(f"  - {error}" for error in errors))


def validate_ea_receipt(receipt: Any) -> list[str]:
    """Return validation errors for an ea_receipt.v0 object."""
    if not isinstance(receipt, dict):
        return ["receipt must be a JSON object"]

    errors: list[str] = []
    for field in EA_RECEIPT_REQUIRED_FIELDS:
        if field not in receipt:
            errors.append(f"missing required field: {field}")

    if errors:
        return errors

    if receipt["schema_version"] != EA_RECEIPT_SCHEMA_VERSION:
        errors.append("schema_version must be ea_receipt.v0")

    status = receipt["status"]
    if status not in EA_RECEIPT_STATUSES:
        errors.append("status must be one of: failure, success")

    for field in ("commands_run", "files_changed", "tests_run", "blockers"):
        value = receipt[field]
        if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
            errors.append(f"{field} must be a list of strings")

    exit_codes = receipt["inner_exit_codes"]
    if not isinstance(exit_codes, list) or not all(
        isinstance(item, int) and not isinstance(item, bool) for item in exit_codes
    ):
        errors.append("inner_exit_codes must be a list of integers")
        exit_codes = []

    if any(code != 0 for code in exit_codes) and status == "success":
        errors.append("status must be failure when any inner_exit_codes value is nonzero")

    blockers = receipt["blockers"]
    if status == "failure" and isinstance(blockers, list) and not blockers:
        errors.append("failure status requires non-empty blockers")

    return errors


def assert_valid_ea_receipt(receipt: Any) -> None:
    """Raise EAReceiptValidationError when receipt is invalid."""
    errors = validate_ea_receipt(receipt)
    if errors:
        raise EAReceiptValidationError(errors)


def load_and_validate_ea_receipt(path: str | Path) -> dict[str, Any]:
    """Load an EA receipt from disk and fail closed on missing or malformed JSON."""
    receipt_path = Path(path)
    try:
        raw = receipt_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise EAReceiptValidationError([f"receipt not found: {receipt_path}"]) from exc

    try:
        receipt = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise EAReceiptValidationError([f"receipt is not valid JSON: {exc.msg}"]) from exc

    assert_valid_ea_receipt(receipt)
    return receipt
