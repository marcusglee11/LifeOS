"""
A8: TDD tests for S1_55_EXECUTION_FIDELITY gate.

The fidelity gate compares the model actually used per lens against
plan_core.model_assignments and blocks on MUST-independence mismatches.

Tests:
 1. All lenses match plan -> fidelity passes, run completes
 2. MUST-independence lens on wrong vendor -> BLOCKED
 3. SHOULD-independence mismatch -> warning logged, run continues
 4. Emergency CEO override bypasses MUST-block
 5. No lenses (T1) -> fidelity state still reached via transitions, no block
"""
from __future__ import annotations

import pytest

from runtime.orchestration.council.fsm import CouncilFSMv2, STATE_S1_55_EXECUTION_FIDELITY, STATE_TERMINAL_BLOCKED
from runtime.orchestration.council.models import (
    CouncilRunPlanCore,
    CouncilRunMeta,
    compute_plan_core_hash,
    VERDICT_ACCEPT,
)
from runtime.orchestration.council.policy import load_council_policy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _policy():
    return load_council_policy()


def _make_core(**overrides) -> CouncilRunPlanCore:
    defaults = dict(
        aur_id="AUR-FIDELITY",
        tier="T2",
        run_type="review",
        topology="HYBRID",
        required_lenses=("Risk",),
        model_assignments={
            "Risk": "claude-sonnet-4-5",
            "Chair": "claude-sonnet-4-5",
            "Challenger": "claude-sonnet-4-5",
        },
        lens_role_map={"Risk": "council_reviewer", "Chair": "council_reviewer",
                       "Challenger": "council_reviewer"},
        independence_required="none",
        independence_satisfied=True,
        independent_lenses=(),
        compliance_flags={},
        override_active=False,
        override_rationale=None,
        challenger_required=True,
        contradiction_ledger_required=True,
        closure_gate_required=False,
        mandatory_lenses=("Risk",),
        waivable_lenses=(),
        padded_lenses=(),
    )
    defaults.update(overrides)
    return CouncilRunPlanCore(**defaults)


def _make_meta(core: CouncilRunPlanCore) -> CouncilRunMeta:
    return CouncilRunMeta(
        run_id="fidelity-test-01",
        timestamp="2026-02-23T00:00:00+00:00",
        plan_core_hash=compute_plan_core_hash(core),
    )


def _valid_lens_output(lens_name: str, actual_model: str | None = None) -> dict:
    out = {
        "run_type": "review",
        "lens_name": lens_name,
        "operator_view": ["OK"],
        "confidence": "high",
        "notes": "OK",
        "claims": [{"claim_id": "c1", "statement": "safe", "evidence_refs": ["REF:1"]}],
        "verdict_recommendation": VERDICT_ACCEPT,
    }
    if actual_model is not None:
        out["_actual_model"] = actual_model
    return out


def _valid_synthesis_t2() -> dict:
    return {
        "run_type": "review",
        "tier": "T2",
        "verdict": VERDICT_ACCEPT,
        "fix_plan": [],
        "complexity_budget": {"net_human_steps": 0},
        "operator_view": ["ok"],
        "coverage_degraded": False,
        "waived_lenses": [],
        "evidence_summary": {"ref_count": 1, "assumption_count": 0},
        "contradiction_ledger": [],
    }


def _valid_challenger() -> dict:
    return {
        "weakest_claim": "none",
        "stress_test": "holds",
        "material_issue": False,
        "issue_class": "other",
        "severity": "p2",
        "required_action": "rework_synthesis",
        "notes": "ok",
        "ledger_completeness_ok": True,
        "missing_disagreements": [],
    }


def _make_fsm(core: CouncilRunPlanCore, lens_fn=None, synth_fn=None, chal_fn=None):
    policy = _policy()
    meta = _make_meta(core)

    def plan_factory(ccp, pol):
        return core, meta

    return CouncilFSMv2(
        policy=policy,
        plan_factory=plan_factory,
        lens_executor=lens_fn,
        synthesis_executor=synth_fn or (lambda lr, p, ccp: _valid_synthesis_t2()),
        challenger_executor=chal_fn or (lambda s, lr, p: _valid_challenger()),
    )


def _ccp():
    return {
        "header": {"aur_id": "AUR-FID", "run_type": "review"},
        "sections": {
            "objective": "Fidelity test",
            "scope": "runtime",
            "constraints": ["pass"],
            "artifacts": [{"id": "a1"}],
        },
    }


def _states(result) -> list[str]:
    return [t["to_state"] for t in result.run_log.get("state_transitions", [])]


# ---------------------------------------------------------------------------
# Test 1: actual model matches plan -> fidelity passes, run completes
# ---------------------------------------------------------------------------


def test_fidelity_match_passes():
    core = _make_core(
        independence_required="must",
        independence_satisfied=True,
        independent_lenses=("Risk",),
    )
    # Executor returns the planned model
    def lens_fn(name, ccp, plan, retry):
        model = plan.model_assignments.get(name, "")
        return _valid_lens_output(name, actual_model=model)

    fsm = _make_fsm(core, lens_fn=lens_fn)
    result = fsm.run(_ccp())
    assert result.status == "complete"
    states = _states(result)
    assert STATE_S1_55_EXECUTION_FIDELITY in states
    assert STATE_TERMINAL_BLOCKED not in states


def test_fidelity_prefixed_model_ids_same_family_pass():
    core = _make_core(
        independence_required="must",
        independence_satisfied=True,
        independent_lenses=("Risk",),
        model_assignments={
            "Risk": "openai-codex/gpt-5.3-codex",
            "Chair": "claude-sonnet-4-5",
            "Challenger": "claude-sonnet-4-5",
        },
    )

    def lens_fn(name, ccp, plan, retry):
        if name == "Risk":
            return _valid_lens_output(name, actual_model="gpt-5.3-codex")
        return _valid_lens_output(name)

    fsm = _make_fsm(core, lens_fn=lens_fn)
    result = fsm.run(_ccp())
    assert result.status == "complete"
    states = _states(result)
    assert STATE_TERMINAL_BLOCKED not in states


# ---------------------------------------------------------------------------
# Test 2: MUST-independence lens on wrong vendor family -> BLOCKED
# ---------------------------------------------------------------------------


def test_fidelity_must_mismatch_blocks():
    core = _make_core(
        independence_required="must",
        independence_satisfied=True,
        independent_lenses=("Risk",),
        model_assignments={
            "Risk": "claude-sonnet-4-5",  # anthropic family
            "Chair": "claude-sonnet-4-5",
            "Challenger": "claude-sonnet-4-5",
        },
    )

    def lens_fn(name, ccp, plan, retry):
        if name == "Risk":
            # Actually ran on wrong family (same as Chair = anthropic) — independence violated
            return _valid_lens_output(name, actual_model="gpt-4o")  # openai family
        return _valid_lens_output(name)

    fsm = _make_fsm(core, lens_fn=lens_fn)
    result = fsm.run(_ccp())
    assert result.status == "blocked"
    states = _states(result)
    assert STATE_TERMINAL_BLOCKED in states


# ---------------------------------------------------------------------------
# Test 3: SHOULD-independence mismatch -> warning, run continues
# ---------------------------------------------------------------------------


def test_fidelity_should_mismatch_warns_but_continues():
    core = _make_core(
        independence_required="should",
        independence_satisfied=False,
        independent_lenses=(),
    )

    def lens_fn(name, ccp, plan, retry):
        # All lenses ran on same family as Chair — SHOULD violation
        return _valid_lens_output(name, actual_model="claude-sonnet-4-5")

    fsm = _make_fsm(core, lens_fn=lens_fn)
    result = fsm.run(_ccp())
    # SHOULD mismatch: run continues (not blocked)
    assert result.status == "complete"
    states = _states(result)
    assert STATE_TERMINAL_BLOCKED not in states


# ---------------------------------------------------------------------------
# Test 4: Emergency CEO override bypasses MUST block
# ---------------------------------------------------------------------------


def test_fidelity_emergency_override_bypasses_block():
    core = _make_core(
        independence_required="must",
        independence_satisfied=False,  # Not satisfied
        independent_lenses=(),
        compliance_flags={"ceo_override": True},
        override_active=True,
    )

    def lens_fn(name, ccp, plan, retry):
        # Wrong model — but emergency override active
        return _valid_lens_output(name, actual_model="gpt-4o")

    fsm = _make_fsm(core, lens_fn=lens_fn)
    result = fsm.run(_ccp())
    # Emergency override: should NOT block (continue with warning)
    assert result.status == "complete"


# ---------------------------------------------------------------------------
# Test 5: T1 (no lenses) -> fidelity state not in path (no S1 states)
# ---------------------------------------------------------------------------


def test_fidelity_no_lenses_skips_s1_states():
    core = _make_core(
        tier="T1",
        required_lenses=(),
        mandatory_lenses=(),
        waivable_lenses=(),
        contradiction_ledger_required=False,
        independence_required="none",
    )
    fsm = _make_fsm(
        core,
        synth_fn=lambda lr, p, ccp: {
            "run_type": "review",
            "tier": "T1",
            "verdict": VERDICT_ACCEPT,
            "fix_plan": [],
            "complexity_budget": {"net_human_steps": 0},
            "operator_view": ["ok"],
            "coverage_degraded": False,
            "waived_lenses": [],
            "evidence_summary": {"ref_count": 0, "assumption_count": 0},
        },
        chal_fn=lambda s, lr, p: {
            "weakest_claim": "none",
            "stress_test": "holds",
            "material_issue": False,
            "issue_class": "other",
            "severity": "p2",
            "required_action": "rework_synthesis",
            "notes": "ok",
        },
    )
    result = fsm.run(_ccp())
    assert result.status == "complete"
    states = _states(result)
    assert STATE_S1_55_EXECUTION_FIDELITY not in states
