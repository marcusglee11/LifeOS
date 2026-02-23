"""
v2.2.1 model tests: CouncilRunPlanCore, CouncilRunMeta, compute_plan_core_hash,
ChallengerResult, ContradictionLedgerEntry, and new constants. 13 tests.
"""
from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from runtime.orchestration.council.models import (
    CouncilRunPlanCore,
    CouncilRunMeta,
    ChallengerResult,
    ContradictionLedgerEntry,
    compute_plan_core_hash,
    VERDICT_ACCEPT,
    VERDICT_REVISE,
    VERDICT_REJECT,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_plan_core(**overrides) -> CouncilRunPlanCore:
    defaults = dict(
        aur_id="AUR-TEST",
        tier="T1",
        run_type="review",
        topology="MONO",
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


# ---------------------------------------------------------------------------
# CouncilRunPlanCore immutability + field separation
# ---------------------------------------------------------------------------


def test_plan_core_is_frozen():
    core = make_plan_core()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        core.tier = "T2"  # type: ignore[misc]


def test_plan_core_excludes_run_id():
    core = make_plan_core()
    assert not hasattr(core, "run_id")


def test_plan_core_excludes_timestamp():
    core = make_plan_core()
    assert not hasattr(core, "timestamp")


def test_plan_meta_has_run_id():
    meta = CouncilRunMeta(run_id="r1", timestamp="t1", plan_core_hash="h1")
    assert meta.run_id == "r1"
    assert meta.plan_core_hash == "h1"


# ---------------------------------------------------------------------------
# Canonical hashing
# ---------------------------------------------------------------------------


def test_plan_core_hash_deterministic():
    core = make_plan_core()
    h1 = compute_plan_core_hash(core)
    h2 = compute_plan_core_hash(core)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_plan_core_hash_changes_on_diff():
    core1 = make_plan_core(tier="T1")
    core2 = make_plan_core(tier="T2")
    assert compute_plan_core_hash(core1) != compute_plan_core_hash(core2)


def test_plan_core_hash_sorts_keys():
    core = make_plan_core()
    d = core.to_dict()
    assert list(d.keys()) == sorted(d.keys())


def test_plan_core_hash_sorts_set_arrays():
    """Same lenses in different tuple order -> same hash."""
    core1 = make_plan_core(
        required_lenses=("Risk", "Governance"),
        mandatory_lenses=("Risk",),
        waivable_lenses=("Governance",),
    )
    core2 = make_plan_core(
        required_lenses=("Governance", "Risk"),
        mandatory_lenses=("Risk",),
        waivable_lenses=("Governance",),
    )
    assert compute_plan_core_hash(core1) == compute_plan_core_hash(core2)


# ---------------------------------------------------------------------------
# Verdict enum (v2.2.1: "Go with Fixes" -> "Revise")
# ---------------------------------------------------------------------------


def test_verdict_accept_valid():
    assert VERDICT_ACCEPT == "Accept"


def test_verdict_revise_valid():
    assert VERDICT_REVISE == "Revise"


def test_verdict_go_with_fixes_gone():
    import runtime.orchestration.council.models as m
    assert not hasattr(m, "VERDICT_GO_WITH_FIXES")
    assert "Go with Fixes" not in {VERDICT_ACCEPT, VERDICT_REVISE, VERDICT_REJECT}


# ---------------------------------------------------------------------------
# New dataclass fields
# ---------------------------------------------------------------------------


def test_challenger_result_fields():
    r = ChallengerResult(
        weakest_claim="c",
        stress_test="s",
        material_issue=False,
        issue_class="other",
        severity="p2",
        required_action="rework_synthesis",
        notes="n",
    )
    assert r.material_issue is False
    assert r.ledger_completeness_ok is None   # optional, defaults to None
    assert r.missing_disagreements is None     # optional, defaults to None


def test_contradiction_ledger_entry_fields():
    e = ContradictionLedgerEntry(
        topic="scope",
        positions={"Risk": "c1", "Governance": "c2"},
        resolution={"decision": "keep", "rationale": "ok"},
        status="resolved",
    )
    assert e.topic == "scope"
    assert len(e.positions) == 2
    assert e.status == "resolved"
