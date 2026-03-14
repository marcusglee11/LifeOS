"""Tests: Transactional state snapshots (Phase 3A — Constitutional Compliance).

Verifies that run_workflow captures pre-step state snapshots, enabling
rollback to pre-failure state.
"""
from __future__ import annotations

import pytest

from runtime.orchestration.engine import (
    ExecutionContext,
    Orchestrator,
    StepSpec,
    WorkflowDefinition,
)


def _workflow(*steps: StepSpec, wf_id: str = "wf-snap-test") -> WorkflowDefinition:
    return WorkflowDefinition(id=wf_id, steps=list(steps))


def _noop(step_id: str = "s1") -> StepSpec:
    return StepSpec(id=step_id, kind="runtime", payload={"operation": "noop"})


def _fail(step_id: str = "fail") -> StepSpec:
    return StepSpec(id=step_id, kind="runtime", payload={"operation": "fail", "reason": "test"})


def _ctx(**initial) -> ExecutionContext:
    return ExecutionContext(initial_state=dict(initial))


# ---------------------------------------------------------------------------
# 3A-1: Single-step workflow produces one snapshot (pre-step state)
# ---------------------------------------------------------------------------

def test_single_step_produces_one_snapshot():
    orch = Orchestrator()
    result = orch.run_workflow(_workflow(_noop()), _ctx(x=1))
    assert len(result.state_snapshots) == 1
    assert result.state_snapshots[0] == {"x": 1}


# ---------------------------------------------------------------------------
# 3A-2: N executed steps → N snapshots
# ---------------------------------------------------------------------------

def test_n_steps_produce_n_snapshots():
    steps = [_noop(f"s{i}") for i in range(3)]
    orch = Orchestrator()
    result = orch.run_workflow(_workflow(*steps), _ctx(a=1))
    assert len(result.state_snapshots) == 3


# ---------------------------------------------------------------------------
# 3A-3: Snapshot count = executed_steps count (including failing step)
# ---------------------------------------------------------------------------

def test_failed_step_still_captured():
    steps = [_noop("s1"), _fail("s2")]
    orch = Orchestrator()
    result = orch.run_workflow(_workflow(*steps), _ctx(x=1))
    assert not result.success
    assert result.failed_step_id == "s2"
    assert len(result.state_snapshots) == 2  # snapshot before s1 AND s2


# ---------------------------------------------------------------------------
# 3A-4: rollback_to_step(0) returns pre-first-step state
# ---------------------------------------------------------------------------

def test_rollback_to_step_0_returns_initial_state():
    orch = Orchestrator()
    result = orch.run_workflow(_workflow(_noop()), _ctx(x=99))
    pre = result.rollback_to_step(0)
    assert pre == {"x": 99}


# ---------------------------------------------------------------------------
# 3A-5: rollback_to_step returns deep copy (not aliased)
# ---------------------------------------------------------------------------

def test_rollback_returns_deep_copy():
    orch = Orchestrator()
    result = orch.run_workflow(_workflow(_noop()), _ctx(lst=[1, 2, 3]))
    pre = result.rollback_to_step(0)
    pre["lst"].append(99)
    # Original snapshot should not be mutated
    assert result.state_snapshots[0]["lst"] == [1, 2, 3]


# ---------------------------------------------------------------------------
# 3A-6: rollback_to_step out of range raises IndexError
# ---------------------------------------------------------------------------

def test_rollback_out_of_range():
    orch = Orchestrator()
    result = orch.run_workflow(_workflow(_noop()), _ctx())
    with pytest.raises(IndexError):
        result.rollback_to_step(99)


# ---------------------------------------------------------------------------
# 3A-7: lineage includes snapshot_hashes
# ---------------------------------------------------------------------------

def test_lineage_includes_snapshot_hashes():
    orch = Orchestrator()
    result = orch.run_workflow(_workflow(_noop("s1"), _noop("s2")), _ctx(k="v"))
    assert "snapshot_hashes" in result.lineage
    hashes = result.lineage["snapshot_hashes"]
    assert len(hashes) == 2
    assert all(h.startswith("sha256:") for h in hashes)


# ---------------------------------------------------------------------------
# 3A-8: Failed workflow final_state is the pre-failure state (not corrupted)
# ---------------------------------------------------------------------------

def test_failed_workflow_returns_pre_failure_state():
    """final_state after failure is the state from BEFORE the failing step."""
    steps = [_noop("s1"), _fail("s2")]
    orch = Orchestrator()
    result = orch.run_workflow(_workflow(*steps), _ctx(counter=0))
    assert not result.success
    # The fail step doesn't modify state, so final_state == initial_state
    # (noop also doesn't modify state)
    assert result.final_state == {"counter": 0}
