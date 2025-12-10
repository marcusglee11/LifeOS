# runtime/tests/test_tier2_builder.py
"""
TDD Tests for Tier-2 Workflow Builder.

These tests define the contract for the builder module before implementation.
The builder must produce Anti-Failure-compliant WorkflowDefinitions.
"""
import copy
import hashlib
import json
from typing import Any, Dict

import pytest

from runtime.orchestration.engine import (
    Orchestrator,
    WorkflowDefinition,
    StepSpec,
    ExecutionContext,
    OrchestrationResult,
    AntiFailureViolation,
    EnvelopeViolation,
)
from runtime.orchestration.builder import (
    MissionSpec,
    build_workflow,
    AntiFailurePlanningError,
)


def _stable_hash(obj: Any) -> str:
    """
    Deterministic hash helper for asserting byte-identical behaviour.
    Serialises via JSON with sorted keys before hashing.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# =============================================================================
# Basic Mission → Workflow Tests
# =============================================================================

def test_build_workflow_daily_loop_produces_valid_workflow():
    """
    MissionSpec(type="daily_loop") yields a WorkflowDefinition with:
    - Stable id (e.g. "wf-daily-loop")
    - Non-empty steps list
    - All steps use allowed kinds ("runtime" or "human")
    """
    mission = MissionSpec(type="daily_loop", params={})
    workflow = build_workflow(mission)
    
    assert isinstance(workflow, WorkflowDefinition)
    assert workflow.id == "wf-daily-loop"
    assert len(workflow.steps) > 0
    
    # All steps must use allowed kinds
    allowed_kinds = {"runtime", "human"}
    for step in workflow.steps:
        assert step.kind in allowed_kinds, f"Step {step.id} has invalid kind: {step.kind}"


def test_build_workflow_run_tests_produces_valid_workflow():
    """
    MissionSpec(type="run_tests", params={"target": "runtime"}) yields a valid workflow.
    """
    mission = MissionSpec(type="run_tests", params={"target": "runtime"})
    workflow = build_workflow(mission)
    
    assert isinstance(workflow, WorkflowDefinition)
    assert "run-tests" in workflow.id or "run_tests" in workflow.id
    assert len(workflow.steps) > 0
    
    # All steps must use allowed kinds
    allowed_kinds = {"runtime", "human"}
    for step in workflow.steps:
        assert step.kind in allowed_kinds


def test_build_workflow_unknown_type_raises_error():
    """
    Unknown mission types should raise a clear error.
    """
    mission = MissionSpec(type="unknown_mission_type", params={})
    
    with pytest.raises(ValueError):
        build_workflow(mission)


# =============================================================================
# Anti-Failure By Construction Tests
# =============================================================================

def test_build_workflow_respects_max_steps_limit():
    """
    For any supported mission, len(workflow.steps) <= 5.
    """
    # Test all supported mission types
    mission_types = ["daily_loop", "run_tests"]
    
    for mission_type in mission_types:
        mission = MissionSpec(type=mission_type, params={})
        workflow = build_workflow(mission)
        
        assert len(workflow.steps) <= 5, (
            f"Mission type '{mission_type}' produced {len(workflow.steps)} steps, "
            f"exceeds Anti-Failure limit of 5"
        )


def test_build_workflow_respects_max_human_steps_limit():
    """
    For any supported mission, human step count <= 2.
    """
    mission_types = ["daily_loop", "run_tests"]
    
    for mission_type in mission_types:
        mission = MissionSpec(type=mission_type, params={})
        workflow = build_workflow(mission)
        
        human_steps = sum(1 for s in workflow.steps if s.kind == "human")
        assert human_steps <= 2, (
            f"Mission type '{mission_type}' produced {human_steps} human steps, "
            f"exceeds Anti-Failure limit of 2"
        )


def test_build_workflow_excessive_steps_raises_or_truncates():
    """
    If a mission explicitly requests more steps than allowed,
    either AntiFailurePlanningError is raised or workflow is truncated.
    """
    # Request a workflow with explicit step count exceeding limits
    mission = MissionSpec(
        type="daily_loop",
        params={"requested_steps": 10}  # Exceeds max of 5
    )
    
    # Either raises or truncates
    try:
        workflow = build_workflow(mission)
        # If no exception, must be truncated to valid limits
        assert len(workflow.steps) <= 5
        human_steps = sum(1 for s in workflow.steps if s.kind == "human")
        assert human_steps <= 2
    except AntiFailurePlanningError:
        # This is also acceptable
        pass


def test_build_workflow_excessive_human_steps_raises_or_truncates():
    """
    If a mission explicitly requests more human steps than allowed,
    either AntiFailurePlanningError is raised or workflow is truncated.
    """
    mission = MissionSpec(
        type="daily_loop",
        params={"requested_human_steps": 5}  # Exceeds max of 2
    )
    
    # Either raises or truncates
    try:
        workflow = build_workflow(mission)
        human_steps = sum(1 for s in workflow.steps if s.kind == "human")
        assert human_steps <= 2
    except AntiFailurePlanningError:
        # This is also acceptable
        pass


# =============================================================================
# Determinism Tests
# =============================================================================

def test_build_workflow_is_deterministic():
    """
    Two identical MissionSpec instances must produce WorkflowDefinitions
    that hash identically via stable JSON serialization.
    """
    mission1 = MissionSpec(type="daily_loop", params={"priority": "high"})
    mission2 = MissionSpec(type="daily_loop", params={"priority": "high"})
    
    workflow1 = build_workflow(mission1)
    workflow2 = build_workflow(mission2)
    
    h1 = _stable_hash(workflow1.to_dict())
    h2 = _stable_hash(workflow2.to_dict())
    
    assert h1 == h2, "Identical missions must produce identical workflows"


def test_build_workflow_deterministic_across_runs():
    """
    Running build_workflow multiple times with the same input
    must produce byte-identical results.
    """
    mission = MissionSpec(type="run_tests", params={"target": "runtime"})
    
    hashes = []
    for _ in range(5):
        workflow = build_workflow(mission)
        hashes.append(_stable_hash(workflow.to_dict()))
    
    # All hashes must be identical
    assert len(set(hashes)) == 1, "All runs must produce identical workflow hashes"


# =============================================================================
# Integration with Orchestrator Tests
# =============================================================================

def test_build_workflow_integrates_with_orchestrator():
    """
    A workflow built with build_workflow can be run through Orchestrator
    without Anti-Failure or envelope violations.
    """
    orchestrator = Orchestrator()
    mission = MissionSpec(type="daily_loop", params={})
    workflow = build_workflow(mission)
    ctx = ExecutionContext(initial_state={"test": True})
    
    # Should not raise any violations
    result = orchestrator.run_workflow(workflow, ctx)
    
    assert isinstance(result, OrchestrationResult)
    # Success depends on mission semantics, but no violations
    assert result.id == workflow.id


def test_build_workflow_orchestrator_deterministic():
    """
    Running the same mission through builder and orchestrator
    must produce deterministic results.
    """
    orchestrator = Orchestrator()
    mission = MissionSpec(type="run_tests", params={"target": "runtime"})
    
    workflow1 = build_workflow(mission)
    workflow2 = build_workflow(mission)
    
    ctx1 = ExecutionContext(initial_state={"seed": 42})
    ctx2 = ExecutionContext(initial_state={"seed": 42})
    
    result1 = orchestrator.run_workflow(workflow1, ctx1)
    result2 = orchestrator.run_workflow(workflow2, ctx2)
    
    h1 = _stable_hash(result1.to_dict())
    h2 = _stable_hash(result2.to_dict())
    
    assert h1 == h2, "Orchestrator results must be deterministic for identical inputs"


def test_build_workflow_does_not_cause_envelope_violation():
    """
    Workflows produced by build_workflow must only use allowed step kinds.
    """
    orchestrator = Orchestrator()
    mission_types = ["daily_loop", "run_tests"]
    
    for mission_type in mission_types:
        mission = MissionSpec(type=mission_type, params={})
        workflow = build_workflow(mission)
        ctx = ExecutionContext(initial_state={})
        
        # Should not raise EnvelopeViolation
        try:
            result = orchestrator.run_workflow(workflow, ctx)
            assert isinstance(result, OrchestrationResult)
        except EnvelopeViolation:
            pytest.fail(f"Mission type '{mission_type}' produced workflow with invalid step kinds")


# =============================================================================
# Edge Cases
# =============================================================================

def test_build_workflow_empty_params_works():
    """
    Missions with empty params dict should work.
    """
    mission = MissionSpec(type="daily_loop", params={})
    workflow = build_workflow(mission)
    
    assert isinstance(workflow, WorkflowDefinition)
    assert len(workflow.steps) > 0


def test_build_workflow_preserves_params_in_metadata():
    """
    Mission params should be preserved in workflow metadata for traceability.
    """
    mission = MissionSpec(type="run_tests", params={"target": "runtime", "verbose": True})
    workflow = build_workflow(mission)
    
    # Metadata should contain mission info
    assert workflow.metadata is not None
    assert "mission_type" in workflow.metadata or "type" in workflow.metadata
