"""
A9: TDD tests for advisory run_type end-to-end paths.

Advisory runs:
- Compile at any tier (not forced T0)
- Lens schema: recommendations[] + evidence_status (no verdict_recommendation required)
- Synthesis: no evidence_summary required
- FSM: skips closure gate

Tests:
 1. Advisory T1 compiles and produces advisory run_type in plan
 2. Advisory T2 compiles (not forced to T0)
 3. Advisory lens output passes validate_lens_output with advisory schema
 4. Advisory lens output rejects missing evidence_status
 5. Advisory FSM run skips closure gate (S3 not in states)
 6. Advisory synthesis passes without evidence_summary
"""

from __future__ import annotations

from runtime.orchestration.council.compiler import compile_council_run_plan_v2
from runtime.orchestration.council.fsm import (
    STATE_S3_CLOSURE_GATE,
    STATE_TERMINAL_COMPLETE,
    CouncilFSMv2,
)
from runtime.orchestration.council.models import (
    VERDICT_ACCEPT,
    CouncilRunMeta,
    CouncilRunPlanCore,
    compute_plan_core_hash,
)
from runtime.orchestration.council.policy import load_council_policy
from runtime.orchestration.council.schema_gate import (
    validate_lens_output,
    validate_synthesis_output,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _policy():
    return load_council_policy()


def _advisory_t1_ccp() -> dict:
    return {
        "header": {
            "aur_id": "AUR-ADV-T1",
            "aur_type": "code",
            "change_class": "amend",
            "blast_radius": "local",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["tests"],
            "safety_critical": False,
            "run_type": "advisory",
        },
        "sections": {
            "objective": "Explore advisory path.",
            "scope": "local",
            "constraints": ["non-binding"],
            "artifacts": [{"id": "code-1"}],
        },
    }


def _advisory_t2_ccp() -> dict:
    return {
        "header": {
            "aur_id": "AUR-ADV-T2",
            "aur_type": "code",
            "change_class": "new",
            "blast_radius": "module",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["runtime_core"],
            "safety_critical": False,
            "run_type": "advisory",
        },
        "sections": {
            "objective": "Advisory on runtime core change.",
            "scope": "runtime",
            "constraints": ["advisory only"],
            "artifacts": [{"id": "code-2"}],
        },
    }


def _valid_advisory_lens(lens_name: str = "Risk") -> dict:
    return {
        "run_type": "advisory",
        "lens_name": lens_name,
        "operator_view": ["proceed"],
        "confidence": "medium",
        "notes": "Advisory assessment.",
        "evidence_status": "evidenced",
        "recommendations": [
            {
                "action": "proceed_with_caution",
                "rationale": "low risk",
                "expected_impact": "low",
                "confidence": "high",
            }
        ],
    }


def _valid_advisory_synthesis(tier: str = "T1") -> dict:
    base = {
        "run_type": "advisory",
        "tier": tier,
        "verdict": VERDICT_ACCEPT,
        "fix_plan": [],
        "complexity_budget": {"net_human_steps": 0},
        "operator_view": ["advisory ok"],
        "coverage_degraded": False,
        "waived_lenses": [],
    }
    if tier in ("T2", "T3"):
        base["contradiction_ledger"] = []
    return base


def _valid_advisory_challenger() -> dict:
    return {
        "weakest_claim": "none",
        "stress_test": "holds",
        "material_issue": False,
        "issue_class": "other",
        "severity": "p2",
        "required_action": "rework_synthesis",
        "notes": "advisory challenger",
    }


def _make_core(**overrides) -> CouncilRunPlanCore:
    defaults = dict(
        aur_id="AUR-ADV",
        tier="T1",
        run_type="advisory",
        topology="HYBRID",
        required_lenses=(),
        model_assignments={"Chair": "claude-sonnet-4-5", "Challenger": "claude-sonnet-4-5"},
        lens_role_map={"Chair": "council_reviewer", "Challenger": "council_reviewer"},
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


def _make_fsm(
    core: CouncilRunPlanCore,
    synth_fn=None,
    chal_fn=None,
    lens_fn=None,
    closure_builder=None,
    closure_validator=None,
):
    policy = _policy()
    meta = CouncilRunMeta(
        run_id="advisory-test-01",
        timestamp="2026-02-23T00:00:00+00:00",
        plan_core_hash=compute_plan_core_hash(core),
    )

    def plan_factory(ccp, pol):
        return core, meta

    return CouncilFSMv2(
        policy=policy,
        plan_factory=plan_factory,
        lens_executor=lens_fn,
        synthesis_executor=synth_fn or (lambda lr, p, ccp: _valid_advisory_synthesis(p.tier)),
        challenger_executor=chal_fn or (lambda s, lr, p: _valid_advisory_challenger()),
        closure_builder=closure_builder or (lambda s, p: (True, {})),
        closure_validator=closure_validator or (lambda s, p: (True, {})),
    )


def _states(result) -> list[str]:
    return [t["to_state"] for t in result.run_log.get("state_transitions", [])]


# ---------------------------------------------------------------------------
# Test 1: Advisory T1 CCP -> plan has run_type=advisory
# ---------------------------------------------------------------------------


def test_advisory_t1_compiles_with_advisory_run_type():
    policy = _policy()
    result = compile_council_run_plan_v2(ccp=_advisory_t1_ccp(), policy=policy)
    core_dict = result["core"]
    assert core_dict["run_type"] == "advisory"
    assert core_dict["tier"] == "T1"


# ---------------------------------------------------------------------------
# Test 2: Advisory T2 CCP -> plan has run_type=advisory, tier=T2 (not forced T0)
# ---------------------------------------------------------------------------


def test_advisory_t2_compiles_at_t2_not_forced_t0():
    policy = _policy()
    result = compile_council_run_plan_v2(ccp=_advisory_t2_ccp(), policy=policy)
    core_dict = result["core"]
    assert core_dict["run_type"] == "advisory"
    # Advisory must NOT be forced to T0 — tier should reflect the CCP's risk profile
    assert core_dict["tier"] in ("T1", "T2", "T3")  # Not T0 for module-level code change


# ---------------------------------------------------------------------------
# Test 3: Advisory lens output passes validate_lens_output
# ---------------------------------------------------------------------------


def test_advisory_lens_passes_schema():
    policy = _policy()
    output = _valid_advisory_lens("Risk")
    gate = validate_lens_output(output, policy, run_type="advisory", tier="T1")
    assert gate.valid is True, f"Errors: {gate.errors}"


# ---------------------------------------------------------------------------
# Test 4: Advisory lens missing evidence_status is rejected
# ---------------------------------------------------------------------------


def test_advisory_lens_missing_evidence_status_rejected():
    policy = _policy()
    output = _valid_advisory_lens("Risk")
    del output["evidence_status"]
    gate = validate_lens_output(output, policy, run_type="advisory", tier="T1")
    assert gate.valid is False
    assert any("evidence_status" in e for e in gate.errors)


# ---------------------------------------------------------------------------
# Test 5: Advisory FSM run skips closure gate (S3 not in states)
# ---------------------------------------------------------------------------


def test_advisory_fsm_skips_closure_gate():
    core = _make_core(
        tier="T1",
        run_type="advisory",
        closure_gate_required=True,  # Even if set, advisory skips closure
    )
    closure_called = {"count": 0}

    def closure_build(s, p):
        closure_called["count"] += 1
        return True, {}

    fsm = _make_fsm(core, closure_builder=closure_build)
    result = fsm.run(_advisory_t1_ccp())
    assert result.status == "complete"
    states = _states(result)
    # Advisory MUST skip closure gate
    assert STATE_S3_CLOSURE_GATE not in states
    assert closure_called["count"] == 0
    assert STATE_TERMINAL_COMPLETE in states


# ---------------------------------------------------------------------------
# Test 6: Advisory synthesis passes validate_synthesis_output without evidence_summary
# ---------------------------------------------------------------------------


def test_advisory_synthesis_passes_without_evidence_summary():
    policy = _policy()
    synthesis = _valid_advisory_synthesis("T1")
    assert "evidence_summary" not in synthesis
    gate = validate_synthesis_output(synthesis, policy, tier="T1", run_type="advisory")
    assert gate.valid is True, f"Errors: {gate.errors}"
