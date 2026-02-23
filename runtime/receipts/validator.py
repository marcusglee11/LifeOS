"""
Schema validation harness for LifeOS receipts artefacts.

Uses jsonschema Draft202012Validator for allOf/if/then/const features.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

from . import schemas as _schemas


# Map schema name -> schema dict
_SCHEMA_MAP: dict[str, dict] = {
    "acceptance_receipt": _schemas.ACCEPTANCE_RECEIPT_SCHEMA,
    "blocked_report": _schemas.BLOCKED_REPORT_SCHEMA,
    "land_receipt": _schemas.LAND_RECEIPT_SCHEMA,
    "gate_result": _schemas.GATE_RESULT_SCHEMA,
    "runlog_event": _schemas.RUNLOG_EVENT_SCHEMA,
    "review_summary": _schemas.REVIEW_SUMMARY_SCHEMA,
}

_FORMAT_CHECKER = FormatChecker()


@_FORMAT_CHECKER.checks("date-time")
def _check_datetime_format(value: object) -> bool:
    """Strict enough RFC3339-like datetime check for pilot receipts."""
    if not isinstance(value, str):
        return True

    normalized = value
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return False

    # date-time must include timezone offset
    return dt.tzinfo is not None


class ReceiptValidationError(Exception):
    """Raised when an artefact fails schema validation."""

    def __init__(self, schema_name: str, errors: list[str]) -> None:
        self.schema_name = schema_name
        self.errors = errors
        msg = f"Validation failed for {schema_name!r} ({len(errors)} error(s)):\n" + "\n".join(
            f"  - {e}" for e in errors
        )
        super().__init__(msg)


def _error_sort_key(error: Any) -> tuple[tuple[str, ...], str]:
    """Deterministic sort key that is robust to mixed int/str JSON paths."""
    path_tokens = tuple(str(token) for token in error.path)
    return (path_tokens, error.message)


def validate_artefact(artefact: dict, schema_name: str) -> list[str]:
    """
    Validate an artefact dict against a named schema.

    Args:
        artefact: The artefact dict to validate.
        schema_name: One of the keys in _SCHEMA_MAP.

    Returns:
        List of error messages. Empty list means valid.

    Raises:
        KeyError: If schema_name is not recognized.
    """
    schema = _SCHEMA_MAP[schema_name]
    validator = Draft202012Validator(schema, format_checker=_FORMAT_CHECKER)
    errors = sorted(validator.iter_errors(artefact), key=_error_sort_key)
    return [e.message for e in errors]


def assert_valid(artefact: dict, schema_name: str) -> None:
    """
    Assert that an artefact is valid against a named schema.

    Args:
        artefact: The artefact dict to validate.
        schema_name: One of the keys in _SCHEMA_MAP.

    Raises:
        ReceiptValidationError: If validation fails.
        KeyError: If schema_name is not recognized.
    """
    errors = validate_artefact(artefact, schema_name)
    if errors:
        raise ReceiptValidationError(schema_name, errors)
