# runtime/tests/test_tier2_daily_loop.py
"""
TDD Tests for Tier-2 Daily Loop Runner.

These tests define the contract for the daily loop runner that composes
the Workflow Builder and Orchestrator into a single deterministic entrypoint.
"""
import hashlib
import json
import hashlib
import json
import copy
from typing import Any

import pytest

from runtime.orchestration.engine import (
    ExecutionContext,
    OrchestrationResult,
    AntiFailureViolation,
)
from runtime.orchestration.daily_loop import run_daily_loop


def _stable_hash(obj: Any) -> str:
    """
    Deterministic hash helper for asserting byte-identical behaviour.
    Serialises via JSON with sorted keys before hashing.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# =============================================================================
# Basic Contract Tests
# =============================================================================

def test_daily_loop_basic_contract():
    """
    Daily loop runs and returns an OrchestrationResult with expected fields.
    """
    ctx = ExecutionContext(initial_state={"run_id": "test-daily"})
    result: OrchestrationResult = run_daily_loop(ctx, params={"mode": "default"})

    assert isinstance(result.success, bool)
    assert isinstance(result.executed_steps, list)
    assert isinstance(result.final_state, dict)
    assert result.lineage is not None
    assert result.receipt is not None


def test_daily_loop_returns_orchestration_result():
    """
    run_daily_loop returns a proper OrchestrationResult instance.
    """
    ctx = ExecutionContext(initial_state={})
    result = run_daily_loop(ctx)

    assert isinstance(result, OrchestrationResult)
    assert result.id == "wf-daily-loop"


def test_daily_loop_with_empty_params():
    """
    Daily loop works with no params provided (defaults to empty dict).
    """
    ctx = ExecutionContext(initial_state={"test": True})
    result = run_daily_loop(ctx)

    assert isinstance(result, OrchestrationResult)
    assert len(result.executed_steps) > 0


# =============================================================================
# Determinism Tests
# =============================================================================

def test_daily_loop_is_deterministic():
    """
    Given identical ctx.initial_state and params, output must be identical across runs.
    """
    ctx_base = ExecutionContext(initial_state={"seed": 123, "run_id": "det-test"})

    ctx1 = ExecutionContext(initial_state=dict(ctx_base.initial_state))
    ctx2 = ExecutionContext(initial_state=dict(ctx_base.initial_state))

    result1 = run_daily_loop(ctx1, params={"mode": "default"})
    result2 = run_daily_loop(ctx2, params={"mode": "default"})

    h1 = _stable_hash(result1.to_dict())
    h2 = _stable_hash(result2.to_dict())

    assert h1 == h2, "Daily loop must be deterministic for identical inputs"


def test_daily_loop_deterministic_across_multiple_runs():
    """
    Running daily loop multiple times with same inputs produces identical results.
    """
    ctx = ExecutionContext(initial_state={"counter": 0})
    params = {"mode": "standard"}

    hashes = []
    for _ in range(5):
        result = run_daily_loop(
            ExecutionContext(initial_state=dict(ctx.initial_state)),
            params=params
        )
        hashes.append(_stable_hash(result.to_dict()))

    # All hashes must be identical
    assert len(set(hashes)) == 1, "All runs must produce identical result hashes"


# =============================================================================
# Anti-Failure Compliance Tests
# =============================================================================

def test_daily_loop_respects_anti_failure_limits():
    """
    Daily loop must not trigger AntiFailureViolation and stays within limits.
    """
    ctx = ExecutionContext(initial_state={})

    # Should not raise AntiFailureViolation
    result = run_daily_loop(ctx, params={"mode": "default"})

    assert len(result.executed_steps) <= 5, "Must have at most 5 steps"
    
    human_steps = [s for s in result.executed_steps if getattr(s, "kind", None) == "human"]
    assert len(human_steps) <= 2, "Must have at most 2 human steps"


def test_daily_loop_uses_only_allowed_step_kinds():
    """
    All steps must use allowed kinds: 'runtime' or 'human'.
    """
    ctx = ExecutionContext(initial_state={})
    result = run_daily_loop(ctx)

    allowed_kinds = {"runtime", "human"}
    for step in result.executed_steps:
        assert step.kind in allowed_kinds, f"Step {step.id} has invalid kind: {step.kind}"


# =============================================================================
# Receipt and Lineage Tests
# =============================================================================

def test_daily_loop_receipt_mentions_human_steps_if_present():
    """
    If the underlying builder uses human steps, they must appear in the receipt.
    """
    ctx = ExecutionContext(initial_state={})
    result = run_daily_loop(ctx, params={"mode": "default"})

    receipt = result.receipt
    step_ids = receipt.get("steps", [])

    for s in result.executed_steps:
        if getattr(s, "kind", None) == "human":
            assert s.id in step_ids, f"Human step '{s.id}' must appear in receipt"


def test_daily_loop_lineage_is_populated():
    """
    Lineage must be populated with workflow and step information.
    """
    ctx = ExecutionContext(initial_state={})
    result = run_daily_loop(ctx)

    assert result.lineage is not None
    assert "workflow_id" in result.lineage
    assert "executed_step_ids" in result.lineage
    assert result.lineage["workflow_id"] == "wf-daily-loop"


def test_daily_loop_receipt_contains_all_executed_steps():
    """
    Receipt must contain IDs of all executed steps.
    """
    ctx = ExecutionContext(initial_state={})
    result = run_daily_loop(ctx)

    receipt_step_ids = result.receipt.get("steps", [])
    executed_step_ids = [s.id for s in result.executed_steps]

    assert receipt_step_ids == executed_step_ids, "Receipt must list all executed steps"


# =============================================================================
# Integration Tests
# =============================================================================

def test_daily_loop_does_not_mutate_input_context():
    """
    Daily loop must not mutate the input context's initial_state.
    """
    initial = {"foo": "bar", "count": 42}
    ctx = ExecutionContext(initial_state=initial.copy())

    before = dict(ctx.initial_state)
    _ = run_daily_loop(ctx)
    after = dict(ctx.initial_state)

    assert before == after, "ExecutionContext.initial_state must remain immutable"


def test_daily_loop_does_not_mutate_params():
    """
    The params dictionary passed to run_daily_loop must not be mutated.
    """
    ctx = ExecutionContext(initial_state={})
    params = {"mode": "default", "extra": [1, 2, 3]}
    params_copy = copy.deepcopy(params)
    
    _ = run_daily_loop(ctx, params=params)
    
    assert params == params_copy, "Params input must be preserved (immutability check)"


def test_daily_loop_final_state_is_independent_of_input():
    """
    final_state must not alias ctx.initial_state.
    """
    ctx = ExecutionContext(initial_state={"value": 1})
    result = run_daily_loop(ctx)

    # Modifying final_state should not affect original
    result.final_state["new_key"] = "test"
    assert "new_key" not in ctx.initial_state


def test_daily_loop_success_for_valid_workflow():
    """
    Daily loop with default params should succeed (no 'fail' operations).
    """
    ctx = ExecutionContext(initial_state={})
    result = run_daily_loop(ctx)

    assert result.success is True
    assert result.failed_step_id is None
    assert result.error_message is None
