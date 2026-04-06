"""Unit tests for runtime/orchestration/council/seat_payload_builder.py."""

from __future__ import annotations

from runtime.orchestration.council.seat_payload_builder import (
    REQUIRED_SECTIONS,
    build_seat_payload,
    hash_payload,
)

_MINIMAL_CCP = {
    "header": {"aur_id": "AUR-TEST-001", "touches": ["runtime_core"]},
    "sections": {
        "objective": "Review the test change.",
        "scope": "Scoped to runtime/tests/",
        "constraints": ["No external calls"],
    },
}


# ---------------------------------------------------------------------------
# Required sections present
# ---------------------------------------------------------------------------


def test_payload_contains_required_sections():
    payload = build_seat_payload(ccp=_MINIMAL_CCP, lens_name="Architecture")
    for section in REQUIRED_SECTIONS:
        assert section in payload, f"Missing required section: {section}"


def test_payload_review_objective_populated():
    payload = build_seat_payload(ccp=_MINIMAL_CCP, lens_name="Architecture")
    assert "test change" in payload["review_objective"].lower()


def test_payload_scope_statement_includes_constraints():
    payload = build_seat_payload(ccp=_MINIMAL_CCP, lens_name="Architecture")
    assert "No external calls" in payload["scope_statement"]


def test_payload_output_schema_present():
    payload = build_seat_payload(ccp=_MINIMAL_CCP, lens_name="Architecture")
    schema = payload["output_schema"]
    assert "required_fields" in schema
    assert "verdict" in schema["required_fields"]


def test_lens_instructions_appended():
    instructions = "Focus on security implications."
    payload = build_seat_payload(ccp=_MINIMAL_CCP, lens_name="Security", lens_instructions=instructions)
    assert payload["lens_instructions"] == instructions


# ---------------------------------------------------------------------------
# Token budget enforcement
# ---------------------------------------------------------------------------


def test_token_budget_truncates_optional_fields():
    long_evidence = "x" * 50_000
    payload = build_seat_payload(
        ccp=_MINIMAL_CCP,
        lens_name="Architecture",
        implementation_evidence=long_evidence,
        token_budget=500,
    )
    # Required sections must still be present
    for section in REQUIRED_SECTIONS:
        assert section in payload
    # implementation_evidence should have been truncated
    assert "_truncated_fields" in payload
    assert "implementation_evidence" in payload["_truncated_fields"]


def test_token_budget_truncation_warning(recwarn):
    long_evidence = "y" * 50_000
    build_seat_payload(
        ccp=_MINIMAL_CCP,
        lens_name="Architecture",
        implementation_evidence=long_evidence,
        token_budget=200,
    )
    assert any("truncated" in str(w.message).lower() for w in recwarn.list)


def test_no_truncation_within_budget():
    payload = build_seat_payload(
        ccp=_MINIMAL_CCP,
        lens_name="Architecture",
        implementation_evidence="short evidence",
        token_budget=8000,
    )
    assert "_truncated_fields" not in payload


# ---------------------------------------------------------------------------
# hash_payload
# ---------------------------------------------------------------------------


def test_hash_payload_deterministic():
    payload = build_seat_payload(ccp=_MINIMAL_CCP, lens_name="Architecture")
    h1 = hash_payload(payload)
    h2 = hash_payload(payload)
    assert h1 == h2


def test_hash_payload_differs_on_change():
    payload_a = build_seat_payload(ccp=_MINIMAL_CCP, lens_name="Architecture")
    payload_b = build_seat_payload(ccp=_MINIMAL_CCP, lens_name="Security")
    assert hash_payload(payload_a) != hash_payload(payload_b)


def test_hash_payload_is_hex_string():
    payload = build_seat_payload(ccp=_MINIMAL_CCP, lens_name="Architecture")
    h = hash_payload(payload)
    assert isinstance(h, str)
    assert len(h) == 64
    int(h, 16)  # must be valid hex
