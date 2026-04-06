"""
Seat output parser for the council runner.

Parses raw LLM seat output into NormalizedSeatOutput.
On schema failure, issues one correction retry with error context prepended.
If the retry also fails, marks the seat as seat_schema_invalid.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Mapping

import yaml

from runtime.orchestration.council.models import NormalizedSeatOutput, SeatFailureClass

logger = logging.getLogger(__name__)

# Fields required in a valid seat output
REQUIRED_FIELDS = frozenset(
    ["verdict", "findings", "risks", "fixes", "open_questions", "confidence", "assumptions"]
)
VALID_VERDICTS = {"Accept", "Revise", "Reject"}
VALID_CONFIDENCE = {"low", "medium", "high"}

# Type for the retry callable (injectable for tests)
RetryCallable = Callable[[str, str], Any]


def parse_seat_output(
    raw: str | Mapping[str, Any],
    *,
    seat_name: str,
    raw_output_path: str | None = None,
    retry_fn: RetryCallable | None = None,
) -> NormalizedSeatOutput:
    """
    Parse raw LLM output into a NormalizedSeatOutput.

    On schema failure, calls retry_fn once with the original raw output and
    a formatted error message. If retry_fn is None or the retry also fails,
    returns a NormalizedSeatOutput with provider_status=seat_schema_invalid.

    Args:
        raw: Raw output from the seat LLM (string or already-parsed dict).
        seat_name: Name of the seat (for logging).
        raw_output_path: Path where raw output was written (archived).
        retry_fn: Optional callable(raw_output_str, error_context) → raw_retry.
            Called at most once on schema failure.

    Returns:
        NormalizedSeatOutput with provider_status indicating success or failure.
    """
    parsed, errors = _parse_and_validate(raw)

    if not errors:
        return _to_normalized(parsed, raw_output_path, SeatFailureClass.seat_completed.value)

    # Schema failure — attempt one correction retry
    if retry_fn is not None:
        error_context = _format_error_context(errors)
        raw_str = raw if isinstance(raw, str) else yaml.dump(dict(raw), default_flow_style=False)
        logger.warning(
            "[%s] seat output schema failure; issuing correction retry: %s", seat_name, errors
        )
        try:
            raw_retry = retry_fn(raw_str, error_context)
        except Exception as exc:
            logger.warning("[%s] retry callable raised: %s", seat_name, exc)
            raw_retry = None

        if raw_retry is not None:
            parsed_retry, retry_errors = _parse_and_validate(raw_retry)
            if not retry_errors:
                return _to_normalized(
                    parsed_retry, raw_output_path, SeatFailureClass.seat_completed.value
                )
            logger.warning("[%s] post-retry schema still invalid: %s", seat_name, retry_errors)

    # Both attempts failed — return schema-invalid sentinel
    logger.error(
        "[%s] marking seat_schema_invalid after %d error(s): %s", seat_name, len(errors), errors
    )
    return NormalizedSeatOutput(
        verdict="",
        findings=[],
        risks=[],
        fixes=[],
        open_questions=[],
        confidence="",
        assumptions=[],
        complexity_budget=None,
        raw_output_path=raw_output_path,
        provider_status=SeatFailureClass.seat_schema_invalid.value,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_and_validate(raw: str | Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Parse raw output and return (parsed_dict, list_of_errors)."""
    if isinstance(raw, Mapping):
        packet = dict(raw)
    else:
        try:
            parsed = yaml.safe_load(str(raw))
        except Exception as exc:
            return {}, [f"YAML parse error: {exc}"]
        if isinstance(parsed, Mapping):
            packet = dict(parsed)
        else:
            return {}, [f"Expected mapping at top level, got {type(parsed).__name__}"]

    errors: list[str] = []

    # Check required fields
    for field in sorted(REQUIRED_FIELDS):
        if field not in packet:
            errors.append(f"missing required field: {field!r}")

    if errors:
        return packet, errors

    # Validate verdict
    verdict = str(packet.get("verdict", "")).strip()
    if verdict not in VALID_VERDICTS:
        errors.append(f"invalid verdict {verdict!r}; expected one of {sorted(VALID_VERDICTS)}")

    # Validate confidence
    confidence = str(packet.get("confidence", "")).strip().lower()
    if confidence not in VALID_CONFIDENCE:
        errors.append(
            f"invalid confidence {confidence!r}; expected one of {sorted(VALID_CONFIDENCE)}"
        )

    # Ensure list fields are actually lists
    for list_field in ("findings", "risks", "fixes", "open_questions", "assumptions"):
        value = packet.get(list_field)
        if value is not None and not isinstance(value, list):
            errors.append(f"field {list_field!r} must be a list, got {type(value).__name__}")

    return packet, errors


def _to_normalized(
    packet: dict[str, Any],
    raw_output_path: str | None,
    provider_status: str,
) -> NormalizedSeatOutput:
    """Convert a validated packet dict to NormalizedSeatOutput."""

    def _list(key: str) -> list[str]:
        value = packet.get(key)
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        return []

    return NormalizedSeatOutput(
        verdict=str(packet.get("verdict", "")).strip(),
        findings=_list("findings"),
        risks=_list("risks"),
        fixes=_list("fixes"),
        open_questions=_list("open_questions"),
        confidence=str(packet.get("confidence", "medium")).strip().lower(),
        assumptions=_list("assumptions"),
        complexity_budget=(
            str(packet["complexity_budget"]) if "complexity_budget" in packet else None
        ),
        raw_output_path=raw_output_path,
        provider_status=provider_status,
    )


def _format_error_context(errors: list[str]) -> str:
    """Format validation errors into a correction prompt prefix."""
    lines = ["Your previous response had schema errors. Please correct and resubmit:"]
    for err in errors:
        lines.append(f"  - {err}")
    lines.append(
        "\nReturn ONLY valid YAML with the required fields: "
        + ", ".join(sorted(REQUIRED_FIELDS))
        + ". No prose before or after the YAML block."
    )
    return "\n".join(lines)
