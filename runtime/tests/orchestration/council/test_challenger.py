"""
Tests for runtime.orchestration.council.challenger (Branch A7).

Mock types (CouncilRunPlanCore, CouncilRunMeta, CouncilRunPlan) are defined here
because the A2 models module has not yet merged. Real CouncilBlockedError and
SchemaGateResult come from the existing council package.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

# Module under test
from runtime.orchestration.council.challenger import (
    ChallengerResult,
    apply_challenger_outcome,
    evaluate_challenger,
)

# Real imports from the council package
from runtime.orchestration.council.models import CouncilBlockedError
from runtime.orchestration.council.schema_gate import SchemaGateResult

# ---------------------------------------------------------------------------
# Mock plan types (A2 has not merged yet)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CouncilRunPlanCore:
    tier: str
    run_type: str
    required_lenses: tuple
    model_assignments: dict
    mandatory_lenses: frozenset
    waivable_lenses: frozenset


@dataclass(frozen=True)
class CouncilRunMeta:
    run_id: str
    timestamp: str
    plan_core_hash: str


@dataclass(frozen=True)
class CouncilRunPlan:
    core: CouncilRunPlanCore
    meta: CouncilRunMeta


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_plan(tier: str = "T2", run_type: str = "review") -> CouncilRunPlan:
    core = CouncilRunPlanCore(
        tier=tier,
        run_type=run_type,
        required_lenses=("Risk",),
        model_assignments={"Risk": "model-x"},
        mandatory_lenses=frozenset({"Risk"}),
        waivable_lenses=frozenset(),
    )
    meta = CouncilRunMeta(
        run_id="run-a7-test",
        timestamp="2026-02-22T00:00:00Z",
        plan_core_hash="def456",
    )
    return CouncilRunPlan(core=core, meta=meta)


def _valid_gate_result(output: dict | None = None) -> SchemaGateResult:
    return SchemaGateResult(
        valid=True,
        rejected=False,
        normalized_output=output or _no_issue_challenger_output(),
        errors=[],
        warnings=[],
    )


def _invalid_gate_result() -> SchemaGateResult:
    return SchemaGateResult(
        valid=False,
        rejected=True,
        normalized_output=None,
        errors=["missing required field: weakest_claim"],
        warnings=[],
    )


def _no_issue_challenger_output() -> dict:
    return {
        "weakest_claim": "All claims are well-evidenced.",
        "stress_test": "Attempted adversarial reframe; synthesis held.",
        "material_issue": False,
        "issue_class": "none",
        "severity": "p2",
        "required_action": "none",
        "notes": "Synthesis is solid.",
    }


def _material_issue_output() -> dict:
    return {
        "weakest_claim": "Claim X lacks any evidence references.",
        "stress_test": "Under adversarial review, verdict collapses without Claim X.",
        "material_issue": True,
        "issue_class": "unsupported_verdict",
        "severity": "p0",
        "required_action": "rework_synthesis",
        "notes": "Synthesis verdict unsupported without evidence.",
    }


def _missing_ledger_output() -> dict:
    return {
        "weakest_claim": "Contradiction between Risk and Governance not resolved.",
        "stress_test": "Ledger is absent; disagreements unaddressed.",
        "material_issue": True,
        "issue_class": "missing_contradiction_ledger",
        "severity": "p0",
        "required_action": "rework_synthesis",
        "notes": "T2 requires contradiction ledger.",
        "ledger_completeness_ok": False,
        "missing_disagreements": ["Risk vs Governance on reversibility"],
    }


def _make_executor(output: dict):
    def executor(synthesis: dict, context: dict) -> dict:
        return output

    return executor


def _always_valid_validator(raw: dict, run_type: str, tier: str) -> SchemaGateResult:
    return _valid_gate_result(raw)


def _always_invalid_validator(raw: dict, run_type: str, tier: str) -> SchemaGateResult:
    return _invalid_gate_result()


# ---------------------------------------------------------------------------
# Test 1: no material issue -> proceed
# ---------------------------------------------------------------------------


def test_challenger_no_material_issue():
    plan = _make_plan(tier="T2")
    output = _no_issue_challenger_output()

    result = evaluate_challenger(
        synthesis_output={"verdict": "Accept"},
        plan=plan,
        executor=_make_executor(output),
        validator=_always_valid_validator,
    )

    assert isinstance(result, ChallengerResult)
    assert result.material_issue is False
    assert result.required_action == "none"

    outcome = apply_challenger_outcome(result, synthesis_rework_count=0)
    assert outcome["action"] == "proceed"
    assert outcome["verdict_override"] is None


# ---------------------------------------------------------------------------
# Test 2: material_issue + rework_count=0 -> rework
# ---------------------------------------------------------------------------


def test_challenger_material_issue_triggers_rework():
    plan = _make_plan(tier="T2")
    output = _material_issue_output()

    result = evaluate_challenger(
        synthesis_output={"verdict": "Accept"},
        plan=plan,
        executor=_make_executor(output),
        validator=_always_valid_validator,
    )

    assert result.material_issue is True

    outcome = apply_challenger_outcome(result, synthesis_rework_count=0)
    assert outcome["action"] == "rework"
    assert outcome["verdict_override"] is None
    assert outcome.get("decision_status") is None


# ---------------------------------------------------------------------------
# Test 3: material_issue + rework_count=1 -> force_revise
# ---------------------------------------------------------------------------


def test_challenger_persistent_issue_forces_revise():
    plan = _make_plan(tier="T2")
    output = _material_issue_output()

    result = evaluate_challenger(
        synthesis_output={"verdict": "Accept"},
        plan=plan,
        executor=_make_executor(output),
        validator=_always_valid_validator,
    )

    assert result.material_issue is True

    outcome = apply_challenger_outcome(result, synthesis_rework_count=1)
    assert outcome["action"] == "force_revise"
    assert outcome["verdict_override"] == "Revise"
    assert outcome["decision_status"] == "DEGRADED_CHALLENGER"
    assert outcome["closure_gate_status"] == "SKIPPED_DEGRADED_REVISE"


# ---------------------------------------------------------------------------
# Test 4: T2 with valid ledger -> ledger_completeness_ok=True
# ---------------------------------------------------------------------------


def test_challenger_t2_checks_ledger_completeness():
    plan = _make_plan(tier="T2")
    output = {
        **_no_issue_challenger_output(),
        "ledger_completeness_ok": True,
        "missing_disagreements": [],
    }

    result = evaluate_challenger(
        synthesis_output={"verdict": "Accept", "contradiction_ledger": [{"topic": "X"}]},
        plan=plan,
        executor=_make_executor(output),
        validator=_always_valid_validator,
    )

    assert result.ledger_completeness_ok is True
    assert result.missing_disagreements == []


# ---------------------------------------------------------------------------
# Test 5: T2 missing ledger -> material_issue with issue_class=missing_contradiction_ledger
# ---------------------------------------------------------------------------


def test_challenger_t2_missing_ledger_is_material():
    plan = _make_plan(tier="T2")
    output = _missing_ledger_output()

    result = evaluate_challenger(
        synthesis_output={"verdict": "Accept"},  # no contradiction_ledger key
        plan=plan,
        executor=_make_executor(output),
        validator=_always_valid_validator,
    )

    assert result.material_issue is True
    assert result.issue_class == "missing_contradiction_ledger"
    assert result.ledger_completeness_ok is False
    assert len(result.missing_disagreements) > 0


# ---------------------------------------------------------------------------
# Test 6: T1 -> ledger_completeness_ok is None (not checked)
# ---------------------------------------------------------------------------


def test_challenger_t1_skips_ledger_check():
    plan = _make_plan(tier="T1")
    output = _no_issue_challenger_output()
    # T1 output should NOT require ledger fields

    result = evaluate_challenger(
        synthesis_output={"verdict": "Accept"},
        plan=plan,
        executor=_make_executor(output),
        validator=_always_valid_validator,
    )

    assert result.ledger_completeness_ok is None


# ---------------------------------------------------------------------------
# Test 7: validator fails first, succeeds on retry
# ---------------------------------------------------------------------------


def test_challenger_validator_retry_then_success():
    plan = _make_plan(tier="T2")
    output = _no_issue_challenger_output()
    call_counts: dict[str, int] = {"n": 0}

    def counting_validator(raw: dict, run_type: str, tier: str) -> SchemaGateResult:
        call_counts["n"] += 1
        if call_counts["n"] == 1:
            return _invalid_gate_result()
        return _valid_gate_result(raw)

    result = evaluate_challenger(
        synthesis_output={"verdict": "Accept"},
        plan=plan,
        executor=_make_executor(output),
        validator=counting_validator,
        max_retries=2,
    )

    assert isinstance(result, ChallengerResult)
    assert result.material_issue is False
    assert call_counts["n"] >= 2


# ---------------------------------------------------------------------------
# Test 8: validator exhausted -> CouncilBlockedError
# ---------------------------------------------------------------------------


def test_challenger_validator_exhausted_blocks():
    plan = _make_plan(tier="T2")
    output = _no_issue_challenger_output()

    with pytest.raises(CouncilBlockedError) as exc_info:
        evaluate_challenger(
            synthesis_output={"verdict": "Accept"},
            plan=plan,
            executor=_make_executor(output),
            validator=_always_invalid_validator,
            max_retries=2,
        )

    err = exc_info.value
    assert err.category == "CHALLENGER_SCHEMA_FAILURE"
