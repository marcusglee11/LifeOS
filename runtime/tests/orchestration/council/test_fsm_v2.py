"""
v2.2.1 FSM tests: CouncilFSMv2 — 18 tests covering all 12 states,
challenger rework loop, lens waiver, coverage degradation, closure gate,
and deterministic log ordering.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# State name constants (FSM internals — imported to verify transitions)
# ---------------------------------------------------------------------------
from runtime.orchestration.council.fsm import (
    STATE_S1_5_COVERAGE_COMPLETE,
    STATE_S1_25_SCHEMA_GATE_LENSES,
    STATE_S1_55_EXECUTION_FIDELITY,
    STATE_S1_EXECUTE_LENSES,
    STATE_S2_5_CHALLENGER_REVIEW,
    STATE_S2_25_SCHEMA_GATE_SYNTHESIS,
    STATE_S2_SYNTHESIS,
    STATE_S3_CLOSURE_GATE,
    STATE_S4_CLOSEOUT,
    STATE_TERMINAL_BLOCKED,
    STATE_TERMINAL_COMPLETE,
    CouncilFSMv2,
)
from runtime.orchestration.council.models import (
    DECISION_STATUS_DEGRADED_CHALLENGER,
    DECISION_STATUS_DEGRADED_COVERAGE,
    VERDICT_ACCEPT,
    VERDICT_REJECT,
    VERDICT_REVISE,
    CouncilRunMeta,
    CouncilRunPlanCore,
)
from runtime.orchestration.council.policy import load_council_policy

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _policy():
    return load_council_policy()


def _make_plan_core(**overrides) -> CouncilRunPlanCore:
    defaults = dict(
        aur_id="AUR-TEST",
        tier="T1",
        run_type="review",
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


def _make_plan_meta(core: CouncilRunPlanCore) -> CouncilRunMeta:
    from runtime.orchestration.council.models import compute_plan_core_hash

    return CouncilRunMeta(
        run_id="council_test01",
        timestamp="2026-02-23T00:00:00+00:00",
        plan_core_hash=compute_plan_core_hash(core),
    )


def _valid_lens_output(lens_name: str = "Risk") -> dict:
    return {
        "run_type": "review",
        "lens_name": lens_name,
        "operator_view": ["point 1"],
        "confidence": "high",
        "notes": "OK",
        "claims": [{"claim_id": "c1", "statement": "Safe", "evidence_refs": ["REF:1"]}],
        "verdict_recommendation": VERDICT_ACCEPT,
    }


def _valid_synthesis(tier: str = "T1") -> dict:
    base = {
        "run_type": "review",
        "tier": tier,
        "verdict": VERDICT_ACCEPT,
        "fix_plan": [],
        "complexity_budget": {"net_human_steps": 0},
        "operator_view": ["all good"],
        "coverage_degraded": False,
        "waived_lenses": [],
        "evidence_summary": {"ref_count": 1, "assumption_count": 0},
    }
    if tier in ("T2", "T3"):
        base["contradiction_ledger"] = []
    return base


def _valid_challenger(material_issue: bool = False) -> dict:
    return {
        "weakest_claim": "None weak",
        "stress_test": "What if X fails?",
        "material_issue": material_issue,
        "issue_class": "other",
        "severity": "p2",
        "required_action": "rework_synthesis",
        "notes": "minor concern",
    }


def _t0_ccp() -> dict:
    return {
        "header": {
            "aur_id": "AUR-T0",
            "aur_type": "doc",
            "change_class": "hygiene",
            "blast_radius": "local",
            "reversibility": "easy",
            "uncertainty": "low",
            "touches": ["docs_only"],
            "safety_critical": False,
            "run_type": "review",
        },
        "sections": {
            "objective": "Update readme.",
            "scope": "docs",
            "constraints": ["none"],
            "artifacts": [{"id": "doc-1"}],
        },
    }


def _t1_ccp() -> dict:
    return {
        "header": {
            "aur_id": "AUR-T1",
            "aur_type": "code",
            "change_class": "amend",
            "blast_radius": "module",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["tests"],
            "safety_critical": False,
            "run_type": "review",
        },
        "sections": {
            "objective": "Add feature X.",
            "scope": "module",
            "constraints": ["pass tests"],
            "artifacts": [{"id": "code-1"}],
        },
    }


def _t2_ccp() -> dict:
    return {
        "header": {
            "aur_id": "AUR-T2",
            "aur_type": "code",
            "change_class": "new",
            "blast_radius": "module",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["runtime_core"],
            "safety_critical": False,
            "run_type": "review",
        },
        "sections": {
            "objective": "Modify runtime core.",
            "scope": "runtime",
            "constraints": ["no regressions"],
            "artifacts": [{"id": "code-2"}],
        },
    }


def _t3_ccp() -> dict:
    return {
        "header": {
            "aur_id": "AUR-T3",
            "aur_type": "governance",
            "change_class": "amend",
            "blast_radius": "system",
            "reversibility": "hard",
            "uncertainty": "high",
            "touches": ["governance_protocol"],
            "safety_critical": True,
            "run_type": "review",
        },
        "sections": {
            "objective": "Amend governance protocol.",
            "scope": "governance",
            "constraints": ["council approval"],
            "artifacts": [{"id": "gov-1"}],
        },
    }


def _make_fsm_with_plan(
    core: CouncilRunPlanCore,
    synthesis_fn=None,
    challenger_fn=None,
    lens_fn=None,
    closure_builder=None,
    closure_validator=None,
) -> "CouncilFSMv2":
    """Build an FSMv2 with a pre-compiled plan (bypasses real compiler)."""
    policy = _policy()
    meta = _make_plan_meta(core)

    def plan_factory(ccp, pol):
        return core, meta

    return CouncilFSMv2(
        policy=policy,
        plan_factory=plan_factory,
        lens_executor=lens_fn,
        synthesis_executor=synthesis_fn,
        challenger_executor=challenger_fn,
        closure_builder=closure_builder,
        closure_validator=closure_validator,
    )


def _last_states(result) -> list[str]:
    return [t["to_state"] for t in result.run_log.get("state_transitions", [])]


# ---------------------------------------------------------------------------
# Test 1: T1 happy path
# ---------------------------------------------------------------------------


def test_fsm_t1_happy_path_complete():
    core = _make_plan_core(
        tier="T1", required_lenses=(), challenger_required=True, closure_gate_required=True
    )
    fsm = _make_fsm_with_plan(
        core,
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T1"),
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=False),
        closure_builder=lambda s, p: (True, {}),
        closure_validator=lambda s, p: (True, {}),
    )
    result = fsm.run(_t1_ccp())
    assert result.status == "complete"
    assert result.decision_payload["verdict"] == VERDICT_ACCEPT
    states = _last_states(result)
    assert STATE_TERMINAL_COMPLETE in states
    # No S1 states for T1 (no lenses)
    assert STATE_S1_EXECUTE_LENSES not in states


# ---------------------------------------------------------------------------
# Test 2: T0 minimal path
# ---------------------------------------------------------------------------


def test_fsm_t0_minimal_path():
    core = _make_plan_core(
        tier="T0",
        required_lenses=(),
        challenger_required=False,
        closure_gate_required=False,
        model_assignments={"Chair": "claude-sonnet-4-5"},
        lens_role_map={"Chair": "council_reviewer"},
    )
    fsm = _make_fsm_with_plan(
        core,
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T0"),
    )
    result = fsm.run(_t0_ccp())
    assert result.status == "complete"
    states = _last_states(result)
    assert STATE_TERMINAL_COMPLETE in states
    # No S1 states (no lenses)
    assert STATE_S1_EXECUTE_LENSES not in states
    # No challenger
    assert STATE_S2_5_CHALLENGER_REVIEW not in states
    # No closure gate
    assert STATE_S3_CLOSURE_GATE not in states


# ---------------------------------------------------------------------------
# Test 3: T2 with lenses traverses S1 states
# ---------------------------------------------------------------------------


def test_fsm_t2_with_lenses():
    core = _make_plan_core(
        tier="T2",
        required_lenses=("Risk", "Governance"),
        mandatory_lenses=("Risk",),
        waivable_lenses=("Governance",),
        challenger_required=True,
        closure_gate_required=True,
        contradiction_ledger_required=True,
    )
    call_log = []

    def lens_fn(lens_name, ccp, plan, retry):
        call_log.append(lens_name)
        return _valid_lens_output(lens_name)

    fsm = _make_fsm_with_plan(
        core,
        lens_fn=lens_fn,
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T2"),
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=False),
        closure_builder=lambda s, p: (True, {}),
        closure_validator=lambda s, p: (True, {}),
    )
    result = fsm.run(_t2_ccp())
    assert result.status == "complete"
    states = _last_states(result)
    assert STATE_S1_EXECUTE_LENSES in states
    assert STATE_S1_25_SCHEMA_GATE_LENSES in states
    assert STATE_S1_5_COVERAGE_COMPLETE in states
    assert STATE_S1_55_EXECUTION_FIDELITY in states
    assert STATE_S2_SYNTHESIS in states


def test_fsm_default_synthesis_executor_uses_lens_recommendations():
    core = _make_plan_core(
        tier="T2",
        required_lenses=("Risk",),
        mandatory_lenses=("Risk",),
        waivable_lenses=(),
        challenger_required=True,
        closure_gate_required=False,
        contradiction_ledger_required=True,
    )

    def lens_fn(lens_name, ccp, plan, retry):
        output = _valid_lens_output(lens_name)
        output["verdict_recommendation"] = VERDICT_REVISE
        return output

    def challenger_fn(s, lr, p):
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

    fsm = _make_fsm_with_plan(
        core,
        lens_fn=lens_fn,
        challenger_fn=challenger_fn,
        synthesis_fn=None,  # use FSM default synthesis executor
        closure_builder=lambda s, p: (True, {}),
        closure_validator=lambda s, p: (True, {}),
    )
    result = fsm.run(_t2_ccp())

    assert result.status == "complete"
    assert result.decision_payload["verdict"] == VERDICT_REVISE
    synthesis = result.run_log.get("synthesis", {})
    assert synthesis.get("coverage_degraded") is False
    assert isinstance(synthesis.get("contradiction_ledger"), list)


# ---------------------------------------------------------------------------
# Test 4: T3 full path — all 12 states traversed
# ---------------------------------------------------------------------------


def test_fsm_t3_full_path():
    core = _make_plan_core(
        tier="T3",
        required_lenses=("Risk", "Governance", "Architecture"),
        mandatory_lenses=("Risk", "Governance"),
        waivable_lenses=("Architecture",),
        challenger_required=True,
        closure_gate_required=True,
        contradiction_ledger_required=True,
    )
    fsm = _make_fsm_with_plan(
        core,
        lens_fn=lambda name, ccp, p, r: _valid_lens_output(name),
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T3"),
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=False),
        closure_builder=lambda s, p: (True, {}),
        closure_validator=lambda s, p: (True, {}),
    )
    result = fsm.run(_t3_ccp())
    assert result.status == "complete"
    states = _last_states(result)
    # All S1 states
    for state in (
        STATE_S1_EXECUTE_LENSES,
        STATE_S1_25_SCHEMA_GATE_LENSES,
        STATE_S1_5_COVERAGE_COMPLETE,
        STATE_S1_55_EXECUTION_FIDELITY,
    ):
        assert state in states, f"Missing state: {state}"
    # S2 states
    for state in (
        STATE_S2_SYNTHESIS,
        STATE_S2_25_SCHEMA_GATE_SYNTHESIS,
        STATE_S2_5_CHALLENGER_REVIEW,
    ):
        assert state in states, f"Missing state: {state}"
    # Closure + complete
    assert STATE_S3_CLOSURE_GATE in states
    assert STATE_S4_CLOSEOUT in states
    assert STATE_TERMINAL_COMPLETE in states


# ---------------------------------------------------------------------------
# Test 5: Lens schema retry recovers
# ---------------------------------------------------------------------------


def test_fsm_lens_schema_retry_recovers():
    core = _make_plan_core(
        tier="T2",
        required_lenses=("Risk",),
        mandatory_lenses=("Risk",),
        waivable_lenses=(),
        challenger_required=True,
        closure_gate_required=True,
        contradiction_ledger_required=True,
    )
    call_counts = {"Risk": 0}

    def lens_fn(name, ccp, plan, retry):
        call_counts[name] = call_counts.get(name, 0) + 1
        if call_counts[name] == 1:
            return {"broken": True}  # Invalid — will fail schema gate
        return _valid_lens_output(name)

    fsm = _make_fsm_with_plan(
        core,
        lens_fn=lens_fn,
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T2"),
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=False),
        closure_builder=lambda s, p: (True, {}),
        closure_validator=lambda s, p: (True, {}),
    )
    result = fsm.run(_t2_ccp())
    assert result.status == "complete"
    assert call_counts["Risk"] == 2  # First failed, second succeeded


# ---------------------------------------------------------------------------
# Test 6: Mandatory lens failure after retries -> BLOCKED
# ---------------------------------------------------------------------------


def test_fsm_mandatory_lens_failure_blocks():
    core = _make_plan_core(
        tier="T2",
        required_lenses=("Risk",),
        mandatory_lenses=("Risk",),
        waivable_lenses=(),
        challenger_required=True,
        closure_gate_required=True,
        contradiction_ledger_required=True,
    )

    def always_fail(name, ccp, plan, retry):
        return {"broken": True}  # Never valid

    fsm = _make_fsm_with_plan(core, lens_fn=always_fail)
    result = fsm.run(_t2_ccp())
    assert result.status == "blocked"
    assert result.decision_payload["status"] == "BLOCKED"


# ---------------------------------------------------------------------------
# Test 7: Waivable lens failure -> waived, coverage_degraded
# ---------------------------------------------------------------------------


def test_fsm_waivable_lens_failure_waived():
    core = _make_plan_core(
        tier="T2",
        required_lenses=("Risk", "Governance"),
        mandatory_lenses=("Risk",),
        waivable_lenses=("Governance",),
        challenger_required=True,
        closure_gate_required=True,
        contradiction_ledger_required=True,
    )

    def lens_fn(name, ccp, plan, retry):
        if name == "Governance":
            return {"broken": True}
        return _valid_lens_output(name)

    fsm = _make_fsm_with_plan(
        core,
        lens_fn=lens_fn,
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T2"),
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=False),
        closure_builder=lambda s, p: (True, {}),
        closure_validator=lambda s, p: (True, {}),
    )
    result = fsm.run(_t2_ccp())
    # Degraded but complete (not blocked)
    assert result.status == "complete"
    assert result.decision_payload.get("decision_status") == DECISION_STATUS_DEGRADED_COVERAGE


# ---------------------------------------------------------------------------
# Test 8: Coverage degraded floors Accept -> Revise
# ---------------------------------------------------------------------------


def test_fsm_coverage_degraded_floors_verdict():
    core = _make_plan_core(
        tier="T2",
        required_lenses=("Risk", "Governance"),
        mandatory_lenses=("Risk",),
        waivable_lenses=("Governance",),
        challenger_required=True,
        closure_gate_required=True,
        contradiction_ledger_required=True,
    )

    def lens_fn(name, ccp, plan, retry):
        if name == "Governance":
            return {"broken": True}
        return _valid_lens_output(name)

    fsm = _make_fsm_with_plan(
        core,
        lens_fn=lens_fn,
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T2"),
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=False),
        closure_builder=lambda s, p: (True, {}),
        closure_validator=lambda s, p: (True, {}),
    )
    result = fsm.run(_t2_ccp())
    # Accept floored to Revise due to coverage degradation
    assert result.decision_payload["verdict"] == VERDICT_REVISE


# ---------------------------------------------------------------------------
# Test 9: Challenger no material issue -> proceed normally
# ---------------------------------------------------------------------------


def test_fsm_challenger_no_material_issue():
    core = _make_plan_core(tier="T1", challenger_required=True, closure_gate_required=True)
    fsm = _make_fsm_with_plan(
        core,
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T1"),
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=False),
        closure_builder=lambda s, p: (True, {}),
        closure_validator=lambda s, p: (True, {}),
    )
    result = fsm.run(_t1_ccp())
    assert result.status == "complete"
    assert result.decision_payload["verdict"] == VERDICT_ACCEPT


# ---------------------------------------------------------------------------
# Test 10: Challenger material_issue=True, count=0 -> rework synthesis
# ---------------------------------------------------------------------------


def test_fsm_challenger_material_issue_rework():
    core = _make_plan_core(tier="T1", challenger_required=True, closure_gate_required=True)
    call_counts = {"synthesis": 0, "challenger": 0}

    def synth(lr, p, ccp):
        call_counts["synthesis"] += 1
        return _valid_synthesis("T1")

    def challenger(s, lr, p):
        call_counts["challenger"] += 1
        # First call raises material issue; second passes
        if call_counts["challenger"] == 1:
            return _valid_challenger(material_issue=True)
        return _valid_challenger(material_issue=False)

    fsm = _make_fsm_with_plan(
        core,
        synthesis_fn=synth,
        challenger_fn=challenger,
        closure_builder=lambda s, p: (True, {}),
        closure_validator=lambda s, p: (True, {}),
    )
    result = fsm.run(_t1_ccp())
    assert result.status == "complete"
    assert call_counts["synthesis"] == 2  # rework triggered
    assert call_counts["challenger"] == 2


# ---------------------------------------------------------------------------
# Test 11: Challenger persistent issue -> DEGRADED_CHALLENGER + forced Revise
# ---------------------------------------------------------------------------


def test_fsm_challenger_persistent_issue_forces_revise():
    core = _make_plan_core(tier="T1", challenger_required=True, closure_gate_required=True)
    fsm = _make_fsm_with_plan(
        core,
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T1"),
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=True),
    )
    result = fsm.run(_t1_ccp())
    assert result.status == "complete"  # Degraded, not blocked
    assert result.decision_payload["verdict"] == VERDICT_REVISE
    assert result.decision_payload.get("decision_status") == DECISION_STATUS_DEGRADED_CHALLENGER


# ---------------------------------------------------------------------------
# Test 12: Closure gate entered only for Accept + non-degraded
# ---------------------------------------------------------------------------


def test_fsm_closure_gate_accept_only():
    core = _make_plan_core(tier="T1", challenger_required=True, closure_gate_required=True)
    closure_called = {"count": 0}

    def closure_build(s, p):
        closure_called["count"] += 1
        return True, {}

    fsm = _make_fsm_with_plan(
        core,
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T1"),
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=False),
        closure_builder=closure_build,
        closure_validator=lambda s, p: (True, {}),
    )
    result = fsm.run(_t1_ccp())
    assert result.status == "complete"
    states = _last_states(result)
    assert STATE_S3_CLOSURE_GATE in states
    assert closure_called["count"] >= 1


# ---------------------------------------------------------------------------
# Test 13: Reject verdict skips closure gate
# ---------------------------------------------------------------------------


def test_fsm_closure_gate_reject_skips():
    core = _make_plan_core(tier="T1", challenger_required=True, closure_gate_required=True)
    closure_called = {"count": 0}

    def synth(lr, p, ccp):
        s = _valid_synthesis("T1")
        s["verdict"] = VERDICT_REJECT
        return s

    def closure_build(s, p):
        closure_called["count"] += 1
        return True, {}

    fsm = _make_fsm_with_plan(
        core,
        synthesis_fn=synth,
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=False),
        closure_builder=closure_build,
        closure_validator=lambda s, p: (True, {}),
    )
    result = fsm.run(_t1_ccp())
    assert result.status == "complete"
    states = _last_states(result)
    assert STATE_S3_CLOSURE_GATE not in states
    assert closure_called["count"] == 0


# ---------------------------------------------------------------------------
# Test 14: Closure gate exhaustion -> verdict=Revise
# ---------------------------------------------------------------------------


def test_fsm_closure_gate_exhaustion():
    core = _make_plan_core(tier="T1", challenger_required=True, closure_gate_required=True)
    fsm = _make_fsm_with_plan(
        core,
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T1"),
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=False),
        closure_builder=lambda s, p: (False, {"error": "closure failed"}),
        closure_validator=lambda s, p: (False, {"error": "validation failed"}),
    )
    result = fsm.run(_t1_ccp())
    assert result.status == "complete"
    # Closure exhaustion demotes verdict to Revise
    assert result.decision_payload["verdict"] == VERDICT_REVISE


# ---------------------------------------------------------------------------
# Test 15: Degraded outcome still emits fix_plan
# ---------------------------------------------------------------------------


def test_fsm_degraded_emits_fix_plan():
    core = _make_plan_core(tier="T1", challenger_required=True, closure_gate_required=True)
    fsm = _make_fsm_with_plan(
        core,
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T1"),
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=True),
    )
    result = fsm.run(_t1_ccp())
    assert result.decision_payload.get("decision_status") == DECISION_STATUS_DEGRADED_CHALLENGER
    assert "fix_plan" in result.decision_payload


# ---------------------------------------------------------------------------
# Test 16: BLOCKED before S2 has no fix_plan
# ---------------------------------------------------------------------------


def test_fsm_blocked_before_s2_no_fix_plan():
    core = _make_plan_core(
        tier="T2",
        required_lenses=("Risk",),
        mandatory_lenses=("Risk",),
        waivable_lenses=(),
        challenger_required=True,
        closure_gate_required=True,
    )
    fsm = _make_fsm_with_plan(core, lens_fn=lambda n, ccp, p, r: {"broken": True})
    result = fsm.run(_t2_ccp())
    assert result.status == "blocked"
    # Decision payload for BLOCKED should not have fix_plan (or it's empty/None)
    fix_plan = result.decision_payload.get("fix_plan")
    assert not fix_plan  # None, [], or absent


# ---------------------------------------------------------------------------
# Test 17: Deterministic log ordering — lens events sorted by lens_name
# ---------------------------------------------------------------------------


def test_fsm_deterministic_log_ordering():
    core = _make_plan_core(
        tier="T2",
        required_lenses=("Governance", "Architecture", "Risk"),
        mandatory_lenses=("Risk",),
        waivable_lenses=("Governance", "Architecture"),
        challenger_required=True,
        closure_gate_required=True,
        contradiction_ledger_required=True,
    )
    fsm = _make_fsm_with_plan(
        core,
        lens_fn=lambda name, ccp, p, r: _valid_lens_output(name),
        synthesis_fn=lambda lr, p, ccp: _valid_synthesis("T2"),
        challenger_fn=lambda s, lr, p: _valid_challenger(material_issue=False),
        closure_builder=lambda s, p: (True, {}),
        closure_validator=lambda s, p: (True, {}),
    )
    result = fsm.run(_t2_ccp())
    assert result.status == "complete"
    lens_results = result.run_log.get("lens_results", {})
    lens_names = list(lens_results.keys())
    assert lens_names == sorted(lens_names)


# ---------------------------------------------------------------------------
# Test 18: No deadlock — state machine always terminates
# ---------------------------------------------------------------------------


def test_fsm_no_deadlock():
    """Run multiple scenarios and verify each terminates at a terminal state."""
    terminal_states = {STATE_TERMINAL_BLOCKED, STATE_TERMINAL_COMPLETE}

    scenarios = [
        # T0 minimal
        (
            _make_plan_core(
                tier="T0",
                required_lenses=(),
                challenger_required=False,
                closure_gate_required=False,
                model_assignments={"Chair": "claude-sonnet-4-5"},
                lens_role_map={"Chair": "council_reviewer"},
            ),
            _t0_ccp(),
            None,
            lambda lr, p, ccp: _valid_synthesis("T0"),
            None,
        ),
        # T1 happy
        (
            _make_plan_core(tier="T1"),
            _t1_ccp(),
            None,
            lambda lr, p, ccp: _valid_synthesis("T1"),
            lambda s, lr, p: _valid_challenger(False),
        ),
        # T1 always-blocked lens (T1 has no lenses, so blocked on synthesis schema fail)
        (
            _make_plan_core(tier="T1"),
            _t1_ccp(),
            None,
            lambda lr, p, ccp: {"bad": "output"},  # invalid synthesis
            None,
        ),
    ]

    policy = _policy()
    for core, ccp, lens_fn, synth_fn, chal_fn in scenarios:
        meta = _make_plan_meta(core)

        def pf(c, p, _core=core, _meta=meta):
            return _core, _meta

        fsm = CouncilFSMv2(
            policy=policy,
            plan_factory=pf,
            lens_executor=lens_fn,
            synthesis_executor=synth_fn,
            challenger_executor=chal_fn,
        )
        result = fsm.run(ccp)
        states = _last_states(result)
        terminal_hit = terminal_states.intersection(set(states))
        assert terminal_hit, f"No terminal state reached for tier={core.tier}: states={states}"
