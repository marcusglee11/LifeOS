from dataclasses import asdict

from runtime.receipts.intent_fidelity import (
    FORBIDDEN_NEXT_STEPS,
    build_conductor_verification,
)

SHA = "b" * 64


def _verification(**overrides):
    payload = {
        "work_item_id": "W-1",
        "brief_type": "worker_prompt",
        "brief_hash": SHA,
        "brief_author_session": "brief-session",
        "conductor_session": "conductor-session",
        "source_manifest_hash": SHA,
        "fidelity_report_hash": SHA,
        "fidelity_status": "preserved_intent",
    }
    payload.update(overrides)
    return build_conductor_verification(**payload)


def test_implementation_authority_granted_is_always_false():
    verification = _verification()
    assert verification.implementation_authority_granted is False


def test_handoff_candidate_true_only_with_separate_session_and_independent_confirmation():
    verification = _verification(conductor_independently_confirmed=True)
    assert verification.handoff_candidate is True

    not_independent = _verification(conductor_independently_confirmed=False)
    assert not_independent.handoff_candidate is False


def test_handoff_candidate_false_when_brief_author_equals_conductor():
    verification = _verification(conductor_session="brief-session")
    assert verification.handoff_candidate is False


def test_forbidden_next_steps_are_set_correctly():
    verification = _verification()
    payload = asdict(verification)
    assert payload["forbidden_next_steps"] == FORBIDDEN_NEXT_STEPS
    assert "reviewer_output_as_authority" in payload["forbidden_next_steps"]
