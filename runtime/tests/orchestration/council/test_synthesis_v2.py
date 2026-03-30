"""
A6: TDD tests for default Chair synthesis executor.

The default synthesis function (build_synthesis_output) produces a v2.2.1-compliant
synthesis dict from lens results, plan core, and CCP. All outputs MUST pass
validate_synthesis_output().

Tests:
 1. T1 synthesis has all required base fields
 2. T1 synthesis passes validate_synthesis_output
 3. T1 synthesis has NO contradiction_ledger (not required)
 4. T2 synthesis has contradiction_ledger (may be empty but present)
 5. T3 synthesis has contradiction_ledger
 6. Review synthesis includes evidence_summary
 7. Advisory synthesis passes validate without evidence_summary
 8. Coverage degraded / waived_lenses reflected in output
"""

from __future__ import annotations

# Module under test
from runtime.orchestration.council.fsm import build_synthesis_output
from runtime.orchestration.council.models import (
    VERDICT_ACCEPT,
    CouncilRunPlanCore,
)
from runtime.orchestration.council.policy import load_council_policy
from runtime.orchestration.council.schema_gate import validate_synthesis_output

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _policy():
    return load_council_policy()


def _make_core(**overrides) -> CouncilRunPlanCore:
    defaults = dict(
        aur_id="AUR-SYNTH",
        tier="T1",
        run_type="review",
        topology="HYBRID",
        required_lenses=(),
        model_assignments={"Chair": "claude-sonnet-4-5"},
        lens_role_map={"Chair": "council_reviewer"},
        independence_required="none",
        independence_satisfied=True,
        independent_lenses=(),
        compliance_flags={},
        override_active=False,
        override_rationale=None,
        challenger_required=True,
        contradiction_ledger_required=False,
        closure_gate_required=True,
        mandatory_lenses=(),
        waivable_lenses=(),
        padded_lenses=(),
    )
    defaults.update(overrides)
    return CouncilRunPlanCore(**defaults)


def _valid_lens_output(lens_name: str = "Risk", run_type: str = "review") -> dict:
    base = {
        "run_type": run_type,
        "lens_name": lens_name,
        "operator_view": ["point 1"],
        "confidence": "high",
        "notes": "OK",
    }
    if run_type == "review":
        base["claims"] = [
            {"claim_id": "c1", "statement": "Safe", "evidence_refs": ["REF:1"]},
        ]
        base["verdict_recommendation"] = VERDICT_ACCEPT
    else:  # advisory
        base["evidence_status"] = "evidenced"
        base["recommendations"] = [{"action": "proceed", "rationale": "low risk"}]
    return base


def _t1_lens_results() -> dict:
    return {}  # T1 has no lenses


def _t2_lens_results() -> dict:
    return {
        "Risk": _valid_lens_output("Risk"),
        "Governance": _valid_lens_output("Governance"),
    }


# ---------------------------------------------------------------------------
# Test 1: T1 synthesis has all required base fields
# ---------------------------------------------------------------------------


def test_synthesis_t1_has_required_fields():
    core = _make_core(tier="T1", run_type="review")
    result = build_synthesis_output(
        lens_results=_t1_lens_results(),
        plan=core,
        ccp={},
        coverage_degraded=False,
        waived_lenses=[],
    )
    for field in (
        "run_type",
        "tier",
        "verdict",
        "fix_plan",
        "complexity_budget",
        "operator_view",
        "coverage_degraded",
        "waived_lenses",
    ):
        assert field in result, f"Missing field: {field}"
    assert result["tier"] == "T1"
    assert result["run_type"] == "review"


# ---------------------------------------------------------------------------
# Test 2: T1 synthesis passes validate_synthesis_output
# ---------------------------------------------------------------------------


def test_synthesis_t1_passes_schema_gate():
    policy = _policy()
    core = _make_core(tier="T1", run_type="review")
    result = build_synthesis_output(
        lens_results=_t1_lens_results(),
        plan=core,
        ccp={},
        coverage_degraded=False,
        waived_lenses=[],
    )
    gate = validate_synthesis_output(result, policy, tier="T1", run_type="review")
    assert gate.valid is True, f"Schema gate errors: {gate.errors}"


# ---------------------------------------------------------------------------
# Test 3: T1 synthesis has NO contradiction_ledger
# ---------------------------------------------------------------------------


def test_synthesis_t1_no_contradiction_ledger():
    core = _make_core(tier="T1", contradiction_ledger_required=False)
    result = build_synthesis_output(
        lens_results=_t1_lens_results(),
        plan=core,
        ccp={},
        coverage_degraded=False,
        waived_lenses=[],
    )
    assert "contradiction_ledger" not in result


# ---------------------------------------------------------------------------
# Test 4: T2 synthesis has contradiction_ledger (may be empty list)
# ---------------------------------------------------------------------------


def test_synthesis_t2_has_contradiction_ledger():
    policy = _policy()
    core = _make_core(
        tier="T2",
        required_lenses=("Risk", "Governance"),
        contradiction_ledger_required=True,
        run_type="review",
    )
    result = build_synthesis_output(
        lens_results=_t2_lens_results(),
        plan=core,
        ccp={},
        coverage_degraded=False,
        waived_lenses=[],
    )
    assert "contradiction_ledger" in result
    assert isinstance(result["contradiction_ledger"], list)
    gate = validate_synthesis_output(result, policy, tier="T2", run_type="review")
    assert gate.valid is True, f"Schema gate errors: {gate.errors}"


# ---------------------------------------------------------------------------
# Test 5: T3 synthesis has contradiction_ledger
# ---------------------------------------------------------------------------


def test_synthesis_t3_has_contradiction_ledger():
    policy = _policy()
    core = _make_core(
        tier="T3",
        required_lenses=("Risk", "Governance"),
        contradiction_ledger_required=True,
        run_type="review",
    )
    result = build_synthesis_output(
        lens_results=_t2_lens_results(),  # reuse T2 lens results shape
        plan=core,
        ccp={},
        coverage_degraded=False,
        waived_lenses=[],
    )
    assert "contradiction_ledger" in result
    gate = validate_synthesis_output(result, policy, tier="T3", run_type="review")
    assert gate.valid is True, f"Schema gate errors: {gate.errors}"


# ---------------------------------------------------------------------------
# Test 6: Review synthesis includes evidence_summary
# ---------------------------------------------------------------------------


def test_synthesis_review_has_evidence_summary():
    core = _make_core(tier="T1", run_type="review")
    result = build_synthesis_output(
        lens_results=_t1_lens_results(),
        plan=core,
        ccp={},
        coverage_degraded=False,
        waived_lenses=[],
    )
    assert "evidence_summary" in result
    assert "ref_count" in result["evidence_summary"]
    assert "assumption_count" in result["evidence_summary"]


# ---------------------------------------------------------------------------
# Test 7: Advisory synthesis passes validate without evidence_summary
# ---------------------------------------------------------------------------


def test_synthesis_advisory_passes_without_evidence_summary():
    policy = _policy()
    core = _make_core(tier="T1", run_type="advisory")
    result = build_synthesis_output(
        lens_results={},
        plan=core,
        ccp={},
        coverage_degraded=False,
        waived_lenses=[],
    )
    # Advisory synthesis should NOT include evidence_summary (not required)
    # and should still pass validate_synthesis_output for advisory
    gate = validate_synthesis_output(result, policy, tier="T1", run_type="advisory")
    assert gate.valid is True, f"Schema gate errors: {gate.errors}"


# ---------------------------------------------------------------------------
# Test 8: Coverage degraded / waived_lenses reflected in output
# ---------------------------------------------------------------------------


def test_synthesis_coverage_degraded_reflected():
    core = _make_core(tier="T2", run_type="review", contradiction_ledger_required=True)
    result = build_synthesis_output(
        lens_results={"Risk": _valid_lens_output("Risk")},
        plan=core,
        ccp={},
        coverage_degraded=True,
        waived_lenses=["Governance"],
    )
    assert result["coverage_degraded"] is True
    assert "Governance" in result["waived_lenses"]


def test_synthesis_ignores_non_dict_claim_entries():
    core = _make_core(tier="T1", run_type="review")
    lens_results = {
        "Risk": {
            "run_type": "review",
            "lens_name": "Risk",
            "operator_view": ["ok"],
            "confidence": "high",
            "notes": "ok",
            "claims": ["not-an-object"],
            "verdict_recommendation": VERDICT_ACCEPT,
        }
    }
    result = build_synthesis_output(
        lens_results=lens_results,
        plan=core,
        ccp={},
        coverage_degraded=False,
        waived_lenses=[],
    )
    assert result["evidence_summary"]["ref_count"] == 0
