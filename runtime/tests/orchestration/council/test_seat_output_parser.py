"""Unit tests for runtime/orchestration/council/seat_output_parser.py."""

from __future__ import annotations

from runtime.orchestration.council.models import SeatFailureClass
from runtime.orchestration.council.seat_output_parser import (
    REQUIRED_FIELDS,
    parse_seat_output,
)

_VALID_YAML = """
verdict: Accept
confidence: high
findings:
  - Implementation follows existing patterns.
risks:
  - Minor regression risk in edge cases.
fixes: []
open_questions: []
assumptions:
  - Tests cover the changed paths.
complexity_budget: low
"""

_VALID_DICT = {
    "verdict": "Accept",
    "confidence": "high",
    "findings": ["Good"],
    "risks": [],
    "fixes": [],
    "open_questions": [],
    "assumptions": ["n/a"],
    "complexity_budget": "low",
}


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_parse_valid_yaml_string():
    result = parse_seat_output(_VALID_YAML, seat_name="Architecture")
    assert result.verdict == "Accept"
    assert result.confidence == "high"
    assert result.provider_status == SeatFailureClass.seat_completed.value


def test_parse_valid_dict():
    result = parse_seat_output(_VALID_DICT, seat_name="Architecture")
    assert result.verdict == "Accept"
    assert result.provider_status == SeatFailureClass.seat_completed.value


def test_parse_raw_output_path_preserved():
    result = parse_seat_output(_VALID_DICT, seat_name="Architecture", raw_output_path="/tmp/seat.yaml")
    assert result.raw_output_path == "/tmp/seat.yaml"


def test_parse_list_fields_normalized():
    result = parse_seat_output(_VALID_DICT, seat_name="Architecture")
    assert isinstance(result.findings, list)
    assert isinstance(result.risks, list)
    assert isinstance(result.assumptions, list)


def test_parse_complexity_budget_none_when_absent():
    d = dict(_VALID_DICT)
    del d["complexity_budget"]
    result = parse_seat_output(d, seat_name="Architecture")
    assert result.complexity_budget is None


# ---------------------------------------------------------------------------
# Schema failure → retry
# ---------------------------------------------------------------------------


def test_parse_missing_field_triggers_retry():
    bad = dict(_VALID_DICT)
    del bad["verdict"]

    retry_calls: list[tuple[str, str]] = []

    def retry_fn(raw: str, error_ctx: str) -> str:
        retry_calls.append((raw, error_ctx))
        return _VALID_YAML  # Return valid YAML on retry

    result = parse_seat_output(bad, seat_name="Arch", retry_fn=retry_fn)
    assert len(retry_calls) == 1
    assert result.provider_status == SeatFailureClass.seat_completed.value


def test_parse_retry_called_exactly_once():
    bad_yaml = "verdict: BadVerdict\nconfidence: high"  # missing required fields

    call_count = 0

    def counting_retry(raw: str, error_ctx: str) -> str:
        nonlocal call_count
        call_count += 1
        return raw  # still bad — no required fields

    parse_seat_output(bad_yaml, seat_name="Arch", retry_fn=counting_retry)
    assert call_count == 1


def test_parse_no_retry_without_retry_fn():
    bad = {"verdict": "Accept"}  # missing most required fields
    result = parse_seat_output(bad, seat_name="Arch", retry_fn=None)
    assert result.provider_status == SeatFailureClass.seat_schema_invalid.value


# ---------------------------------------------------------------------------
# Both attempts fail → seat_schema_invalid
# ---------------------------------------------------------------------------


def test_parse_seat_schema_invalid_after_failed_retry():
    bad = {"verdict": "Accept"}  # missing required fields

    def always_bad_retry(raw: str, error_ctx: str) -> str:
        return raw  # same bad output

    result = parse_seat_output(bad, seat_name="Arch", retry_fn=always_bad_retry)
    assert result.provider_status == SeatFailureClass.seat_schema_invalid.value
    assert result.verdict == ""  # sentinel empty values


def test_parse_invalid_verdict_caught():
    d = dict(_VALID_DICT)
    d["verdict"] = "Maybe"
    result = parse_seat_output(d, seat_name="Arch", retry_fn=None)
    assert result.provider_status == SeatFailureClass.seat_schema_invalid.value


def test_parse_invalid_confidence_caught():
    d = dict(_VALID_DICT)
    d["confidence"] = "super_high"
    result = parse_seat_output(d, seat_name="Arch", retry_fn=None)
    assert result.provider_status == SeatFailureClass.seat_schema_invalid.value


def test_parse_list_field_not_a_list():
    d = dict(_VALID_DICT)
    d["findings"] = "a string, not a list"
    result = parse_seat_output(d, seat_name="Arch", retry_fn=None)
    assert result.provider_status == SeatFailureClass.seat_schema_invalid.value


def test_parse_unparseable_yaml_fails():
    result = parse_seat_output("{{not valid yaml{{", seat_name="Arch", retry_fn=None)
    assert result.provider_status == SeatFailureClass.seat_schema_invalid.value


def test_parse_retry_exception_handled():
    """If retry_fn raises, the parser marks schema_invalid rather than propagating."""
    bad = {"verdict": "Accept"}

    def exploding_retry(raw: str, error_ctx: str) -> str:
        raise RuntimeError("network error")

    result = parse_seat_output(bad, seat_name="Arch", retry_fn=exploding_retry)
    assert result.provider_status == SeatFailureClass.seat_schema_invalid.value


# ---------------------------------------------------------------------------
# Degraded-mode: all required fields in REQUIRED_FIELDS constant
# ---------------------------------------------------------------------------


def test_required_fields_constant():
    assert "verdict" in REQUIRED_FIELDS
    assert "findings" in REQUIRED_FIELDS
    assert "confidence" in REQUIRED_FIELDS
