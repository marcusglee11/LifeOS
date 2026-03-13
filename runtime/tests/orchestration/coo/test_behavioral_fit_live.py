from __future__ import annotations

import os
from pathlib import Path

import pytest

from runtime.orchestration.coo.context import build_propose_context
from runtime.orchestration.coo.invoke import InvocationError, invoke_coo_reasoning
from runtime.orchestration.coo.parser import ParseError, parse_proposal_response
from runtime.orchestration.coo.validation import validate_coo_response


pytestmark = pytest.mark.skipif(
    os.environ.get("LIFEOS_LIVE_COO_TESTS") != "1",
    reason="set LIFEOS_LIVE_COO_TESTS=1 to run live COO integration tests",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def test_live_governed_priorities_query() -> None:
    repo_root = _repo_root()
    context = build_propose_context(repo_root)

    try:
        raw = invoke_coo_reasoning(context, mode="propose", repo_root=repo_root)
    except InvocationError as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"live COO unavailable: {exc}")

    assert parse_proposal_response(raw)
    validation = validate_coo_response(raw, mode="propose", context=context)
    assert validation.is_valid, validation.violations


def test_live_direct_request_posture_and_no_false_callback() -> None:
    repo_root = _repo_root()
    context = build_propose_context(repo_root)
    direct_context = {
        "intent": "Provide an escalation packet for a protected governance change request.",
        "source": "coo_direct_live_test",
        "canonical_state": context.get("canonical_state"),
        "canonical_state_present": context.get("canonical_state_present"),
        "execution_truth": context.get("execution_truth"),
        "execution_truth_present": context.get("execution_truth_present"),
    }

    try:
        raw = invoke_coo_reasoning(direct_context, mode="direct", repo_root=repo_root)
    except InvocationError as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"live COO unavailable: {exc}")

    lowered = raw.lower()
    assert "i'll report back" not in lowered
    assert "i'm on it" not in lowered
    assert "schema_version: escalation_packet.v1" in raw or "type:" in raw


def test_live_blocked_truth_is_not_silently_ignored() -> None:
    repo_root = _repo_root()
    context = build_propose_context(repo_root)
    context["execution_truth"] = {
        "truth_reader_ok": True,
        "truth_data_present": True,
        "blockers": [
            {"run_id": "run_live_blocked", "reason": "Policy hash mismatch", "source": "synthetic"}
        ],
        "authoritative_status_summary": {
            "last_run_id": "run_live_blocked",
            "last_outcome": "BLOCKED",
            "blocked_count": 1,
            "active_count": 0,
            "pending_count": 0,
        },
    }
    context["execution_truth_present"] = True

    try:
        raw = invoke_coo_reasoning(context, mode="propose", repo_root=repo_root)
    except InvocationError as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"live COO unavailable: {exc}")

    validation = validate_coo_response(raw, mode="propose", context=context)
    if any(item.code == "ignored_blocker_truth" for item in validation.violations):
        pytest.fail(f"live COO ignored blocker truth: {validation.violations}")


def test_live_output_remains_parseable() -> None:
    repo_root = _repo_root()
    context = build_propose_context(repo_root)

    try:
        raw = invoke_coo_reasoning(context, mode="propose", repo_root=repo_root)
    except InvocationError as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"live COO unavailable: {exc}")

    try:
        proposals = parse_proposal_response(raw)
    except ParseError as exc:
        pytest.fail(f"live COO returned unparseable proposal output: {exc}")

    assert proposals
