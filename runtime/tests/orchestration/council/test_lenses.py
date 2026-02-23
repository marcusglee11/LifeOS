"""
Tests for runtime.orchestration.council.lenses (Branch A5).

Mock types (CouncilRunPlanCore, CouncilRunMeta, CouncilRunPlan) are defined here
because the A2 models module has not yet merged. Real CouncilBlockedError and
SchemaGateResult come from the existing council package.
"""
from __future__ import annotations

import pytest
from dataclasses import dataclass, field
from typing import Any

# Real imports from the council package
from runtime.orchestration.council.models import CouncilBlockedError
from runtime.orchestration.council.schema_gate import SchemaGateResult

# The module under test
from runtime.orchestration.council.lenses import (
    dispatch_lenses,
    LensResult,
    LensDispatchResult,
)


# ---------------------------------------------------------------------------
# Mock plan types (A2 has not merged yet; these mirror the real spec shapes)
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

def _make_plan(
    required_lenses: tuple = ("Risk",),
    model_assignments: dict | None = None,
    mandatory_lenses: frozenset | None = None,
    waivable_lenses: frozenset | None = None,
    tier: str = "T2",
    run_type: str = "standard",
) -> CouncilRunPlan:
    core = CouncilRunPlanCore(
        tier=tier,
        run_type=run_type,
        required_lenses=required_lenses,
        model_assignments=model_assignments or {l: "model-x" for l in required_lenses},
        mandatory_lenses=mandatory_lenses if mandatory_lenses is not None else frozenset(),
        waivable_lenses=waivable_lenses if waivable_lenses is not None else frozenset(required_lenses),
    )
    meta = CouncilRunMeta(
        run_id="run-a5-test",
        timestamp="2026-02-22T00:00:00Z",
        plan_core_hash="abc123",
    )
    return CouncilRunPlan(core=core, meta=meta)


def _valid_gate_result() -> SchemaGateResult:
    return SchemaGateResult(
        valid=True,
        rejected=False,
        normalized_output={"verdict": "Accept"},
        errors=[],
        warnings=[],
    )


def _invalid_gate_result() -> SchemaGateResult:
    return SchemaGateResult(
        valid=False,
        rejected=True,
        normalized_output=None,
        errors=["schema mismatch"],
        warnings=[],
    )


def _always_valid_executor(lens_name: str, model: str, context: dict) -> dict:
    return {"output": f"{lens_name}_ok"}


def _always_valid_validator(raw: dict, lens_name: str, run_type: str, tier: str) -> SchemaGateResult:
    return _valid_gate_result()


def _always_invalid_validator(raw: dict, lens_name: str, run_type: str, tier: str) -> SchemaGateResult:
    return _invalid_gate_result()


# ---------------------------------------------------------------------------
# Test 1: single lens happy path
# ---------------------------------------------------------------------------

def test_dispatch_single_lens_success():
    plan = _make_plan(required_lenses=("Risk",), mandatory_lenses=frozenset(), waivable_lenses=frozenset({"Risk"}))
    result = dispatch_lenses(plan=plan, executor=_always_valid_executor, validator=_always_valid_validator)

    assert isinstance(result, LensDispatchResult)
    assert result.all_passed is True
    assert result.coverage_degraded is False
    assert result.blocked is False
    assert result.block_reason is None
    assert len(result.lens_results) == 1
    lr = result.lens_results[0]
    assert lr.lens_name == "Risk"
    assert lr.status == "success"
    assert lr.retries_used == 0
    assert lr.waived is False


# ---------------------------------------------------------------------------
# Test 2: multiple lenses -- results sorted deterministically by lens_name
# ---------------------------------------------------------------------------

def test_dispatch_multiple_lenses_sorted_by_name():
    lenses = ("Risk", "Governance", "Architecture")
    plan = _make_plan(
        required_lenses=lenses,
        model_assignments={l: "model-x" for l in lenses},
        mandatory_lenses=frozenset(),
        waivable_lenses=frozenset(lenses),
    )
    result = dispatch_lenses(plan=plan, executor=_always_valid_executor, validator=_always_valid_validator)

    names = [lr.lens_name for lr in result.lens_results]
    assert names == sorted(names), "results must be sorted by lens_name"
    assert names == ["Architecture", "Governance", "Risk"]
    assert result.all_passed is True


# ---------------------------------------------------------------------------
# Test 3: retry then success (validator fails on first call, succeeds on second)
# ---------------------------------------------------------------------------

def test_dispatch_lens_retry_then_success():
    call_counts: dict[str, int] = {"n": 0}

    def counting_validator(raw: dict, lens_name: str, run_type: str, tier: str) -> SchemaGateResult:
        call_counts["n"] += 1
        if call_counts["n"] == 1:
            return _invalid_gate_result()
        return _valid_gate_result()

    plan = _make_plan(
        required_lenses=("Risk",),
        mandatory_lenses=frozenset(),
        waivable_lenses=frozenset({"Risk"}),
    )
    result = dispatch_lenses(plan=plan, executor=_always_valid_executor, validator=counting_validator, max_retries=2)

    assert result.all_passed is True
    assert len(result.lens_results) == 1
    lr = result.lens_results[0]
    assert lr.status == "success"
    assert lr.retries_used == 1


# ---------------------------------------------------------------------------
# Test 4: retries exhausted, lens is waivable -> waived, coverage_degraded
# ---------------------------------------------------------------------------

def test_dispatch_lens_retry_exhausted_waivable():
    plan = _make_plan(
        required_lenses=("Risk",),
        mandatory_lenses=frozenset(),
        waivable_lenses=frozenset({"Risk"}),
    )
    result = dispatch_lenses(
        plan=plan,
        executor=_always_valid_executor,
        validator=_always_invalid_validator,
        max_retries=2,
    )

    assert result.all_passed is False
    assert result.coverage_degraded is True
    assert result.blocked is False
    assert "Risk" in result.waived_lenses
    assert len(result.lens_results) == 1
    lr = result.lens_results[0]
    assert lr.status == "waived"
    assert lr.waived is True


# ---------------------------------------------------------------------------
# Test 5: retries exhausted, lens is mandatory -> CouncilBlockedError raised
# ---------------------------------------------------------------------------

def test_dispatch_lens_retry_exhausted_mandatory_blocks():
    plan = _make_plan(
        required_lenses=("Risk",),
        mandatory_lenses=frozenset({"Risk"}),
        waivable_lenses=frozenset(),
    )
    with pytest.raises(CouncilBlockedError) as exc_info:
        dispatch_lenses(
            plan=plan,
            executor=_always_valid_executor,
            validator=_always_invalid_validator,
            max_retries=2,
        )

    err = exc_info.value
    assert err.category == "LENS_MANDATORY_FAILURE"
    assert "Risk" in err.detail


# ---------------------------------------------------------------------------
# Test 6: mixed results -- one success, one waived -> coverage_degraded
# ---------------------------------------------------------------------------

def test_dispatch_mixed_results_coverage_degraded():
    lenses = ("Alpha", "Beta")
    call_counts: dict[str, int] = {}

    def mixed_validator(raw: dict, lens_name: str, run_type: str, tier: str) -> SchemaGateResult:
        call_counts.setdefault(lens_name, 0)
        call_counts[lens_name] += 1
        if lens_name == "Alpha":
            return _valid_gate_result()
        return _invalid_gate_result()

    plan = _make_plan(
        required_lenses=lenses,
        model_assignments={l: "model-x" for l in lenses},
        mandatory_lenses=frozenset(),
        waivable_lenses=frozenset({"Beta"}),
    )
    result = dispatch_lenses(plan=plan, executor=_always_valid_executor, validator=mixed_validator, max_retries=2)

    assert result.coverage_degraded is True
    assert result.all_passed is False
    assert result.waived_lenses == ["Beta"]
    assert len(result.lens_results) == 2
    statuses = {lr.lens_name: lr.status for lr in result.lens_results}
    assert statuses["Alpha"] == "success"
    assert statuses["Beta"] == "waived"


# ---------------------------------------------------------------------------
# Test 7: empty required_lenses (T1 fast path) -> all_passed, no coverage degradation
# ---------------------------------------------------------------------------

def test_dispatch_no_lenses_t1():
    plan = _make_plan(
        required_lenses=(),
        model_assignments={},
        mandatory_lenses=frozenset(),
        waivable_lenses=frozenset(),
        tier="T1",
    )
    result = dispatch_lenses(plan=plan, executor=_always_valid_executor, validator=_always_valid_validator)

    assert isinstance(result, LensDispatchResult)
    assert result.lens_results == []
    assert result.all_passed is True
    assert result.coverage_degraded is False
    assert result.blocked is False
    assert result.waived_lenses == []


# ---------------------------------------------------------------------------
# Test 8: executor raises exception -> counts as failure; waivable -> waived
# ---------------------------------------------------------------------------

def test_dispatch_executor_exception_counts_as_failure():
    def raising_executor(lens_name: str, model: str, context: dict) -> dict:
        raise ValueError("model timeout")

    plan = _make_plan(
        required_lenses=("Risk",),
        mandatory_lenses=frozenset(),
        waivable_lenses=frozenset({"Risk"}),
    )
    result = dispatch_lenses(
        plan=plan,
        executor=raising_executor,
        validator=_always_valid_validator,
        max_retries=2,
    )

    assert result.coverage_degraded is True
    assert "Risk" in result.waived_lenses
    lr = result.lens_results[0]
    assert lr.status == "waived"
    assert lr.waived is True
    assert any("model timeout" in e or "ValueError" in e for e in lr.errors)
