# runtime/tests/test_tier2_orchestrator.py
import copy
import hashlib
import json
import subprocess
from dataclasses import dataclass
from typing import List, Dict, Any

import pytest

# These imports define the Tier-2 orchestration interface you will implement.
from runtime.orchestration.engine import (
    Orchestrator,
    WorkflowDefinition,
    StepSpec,
    ExecutionContext,
    OrchestrationResult,
    AntiFailureViolation,
    EnvelopeViolation,
)


@pytest.fixture
def temp_git_repo(tmp_path):
    """
    Create temporary git repository for mission testing.

    CRITICAL: Tests must NOT rely on existing git repo.
    This fixture creates a minimal git repo to exercise runtime detection deterministically.
    """
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, check=True, capture_output=True)

    # Create initial commit (required for baseline_commit detection)
    (repo_dir / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "README.md"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, check=True, capture_output=True)

    return repo_dir


def _stable_hash(obj: Any) -> str:
    """
    Deterministic hash helper for asserting byte-identical behaviour.
    Serialises via JSON with sorted keys before hashing.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _simple_workflow(num_steps: int = 3, human_steps: int = 1) -> WorkflowDefinition:
    """
    Helper to construct a simple, valid workflow for testing.
    - All non-human steps are 'runtime' steps.
    - Human steps are explicitly marked.
    """
    steps: List[StepSpec] = []
    for i in range(num_steps):
        if i < human_steps:
            steps.append(
                StepSpec(
                    id=f"step-{i}",
                    kind="human",
                    payload={"description": f"Human approval {i}"},
                )
            )
        else:
            steps.append(
                StepSpec(
                    id=f"step-{i}",
                    kind="runtime",
                    payload={"operation": "noop", "sequence": i},
                )
            )
    return WorkflowDefinition(
        id="wf-simple",
        steps=steps,
        metadata={"purpose": "unit-test"},
    )


def test_orchestrator_runs_steps_in_order():
    orchestrator = Orchestrator()
    workflow = _simple_workflow(num_steps=3, human_steps=1)
    ctx = ExecutionContext(initial_state={"counter": 0})

    result: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)

    assert result.success is True
    assert [s.id for s in result.executed_steps] == ["step-0", "step-1", "step-2"]
    assert result.final_state is not None
    # Ensure state was updated in a deterministic, sequential manner
    assert isinstance(result.final_state, dict)


def test_orchestrator_respects_anti_failure_limits_max_steps():
    orchestrator = Orchestrator()
    # 6 steps should violate the Anti-Failure constraint (max 5 total)
    workflow = _simple_workflow(num_steps=6, human_steps=1)
    ctx = ExecutionContext(initial_state={})

    with pytest.raises(AntiFailureViolation):
        orchestrator.run_workflow(workflow, ctx)


def test_orchestrator_respects_anti_failure_limits_max_human_steps():
    orchestrator = Orchestrator()
    # 3 human steps is over the limit (max 2 human steps)
    workflow = _simple_workflow(num_steps=5, human_steps=3)
    ctx = ExecutionContext(initial_state={})

    with pytest.raises(AntiFailureViolation):
        orchestrator.run_workflow(workflow, ctx)


def test_orchestrator_is_deterministic_for_same_workflow_and_state():
    orchestrator = Orchestrator()
    workflow = _simple_workflow(num_steps=4, human_steps=1)
    ctx_base = ExecutionContext(initial_state={"seed": 42})

    # Run twice from clean copies
    ctx1 = copy.deepcopy(ctx_base)
    ctx2 = copy.deepcopy(ctx_base)

    result1: OrchestrationResult = orchestrator.run_workflow(workflow, ctx1)
    result2: OrchestrationResult = orchestrator.run_workflow(workflow, ctx2)

    assert result1.success is True
    assert result2.success is True

    # Compare stable hashes of result objects (converted to serialisable dicts)
    h1 = _stable_hash(result1.to_dict())
    h2 = _stable_hash(result2.to_dict())
    assert h1 == h2, "Orchestrator must be fully deterministic for identical inputs."


def test_orchestrator_records_lineage_and_receipt_deterministically():
    orchestrator = Orchestrator()
    workflow = _simple_workflow(num_steps=3, human_steps=0)
    ctx = ExecutionContext(initial_state={"run_id": "test-run"})

    result: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)

    assert result.lineage is not None
    assert result.receipt is not None

    # Lineage and receipt must be serialisable and stable
    h_lineage = _stable_hash(result.lineage)
    h_receipt = _stable_hash(result.receipt)

    # Running again should produce identical hashes
    result2: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)
    assert _stable_hash(result2.lineage) == h_lineage
    assert _stable_hash(result2.receipt) == h_receipt


def test_orchestrator_halts_on_step_failure_with_deterministic_state():
    """
    If a runtime step fails, the orchestrator must halt deterministically
    and record the failure in the result without leaving ambiguous state.
    """
    orchestrator = Orchestrator()

    failing_step = StepSpec(
        id="step-fail",
        kind="runtime",
        payload={"operation": "fail", "reason": "synthetic"},
    )
    workflow = WorkflowDefinition(
        id="wf-failing",
        steps=[
            StepSpec(id="step-0", kind="runtime", payload={"operation": "noop"}),
            failing_step,
            StepSpec(id="step-2", kind="runtime", payload={"operation": "noop"}),
        ],
        metadata={"purpose": "unit-test-failure"},
    )
    ctx = ExecutionContext(initial_state={"value": 1})

    result: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)

    assert result.success is False
    assert result.failed_step_id == "step-fail"
    assert "synthetic" in (result.error_message or "")
    # No steps after the failing one should be executed
    executed_ids = [s.id for s in result.executed_steps]
    assert executed_ids == ["step-0", "step-fail"]


def test_orchestrator_enforces_execution_envelope():
    """
    Tier-2 must stay inside the execution envelope:
    - No network IO
    - No arbitrary subprocesses
    - No parallel/multi-process escalation

    This test uses a synthetic 'forbidden' step type to assert envelope enforcement.
    """
    orchestrator = Orchestrator()

    forbidden_step = StepSpec(
        id="step-forbidden",
        kind="forbidden",  # e.g. 'network_call', 'subprocess', etc.
        payload={"target": "https://example.com"},
    )
    workflow = WorkflowDefinition(
        id="wf-envelope-violation",
        steps=[forbidden_step],
        metadata={"purpose": "unit-test-envelope"},
    )
    ctx = ExecutionContext(initial_state={})

    with pytest.raises(EnvelopeViolation):
        orchestrator.run_workflow(workflow, ctx)


def test_executed_steps_are_snapshotted() -> None:
    """
    Ensure the orchestrator snapshots (deepcopies) executed steps so that 
    subsequent mutation of the input payload does not corrupt the history.
    """
    # Construct a workflow with a mutable payload in the StepSpec
    mutable_payload = {"value": 1}

    workflow = WorkflowDefinition(
        id="mutable-step",
        name="mutable-step",
        steps=[
            StepSpec(
                id="step-1",
                kind="runtime",
                payload=mutable_payload,
            )
        ],
    )

    ctx = ExecutionContext(initial_state={"x": 0})
    orchestrator = Orchestrator()

    result: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)

    # Mutate the original payload after the run
    mutable_payload["value"] = 999

    # Assert the executed_steps snapshot has not changed
    executed_step = result.executed_steps[0]
    # StepSpec does not have to_dict, but we can access payload directly
    assert executed_step.payload["value"] == 1
    assert executed_step.payload is not mutable_payload  # Must be a different object


def test_orchestrator_dispatches_mission_successfully(temp_git_repo, monkeypatch):
    """
    Test orchestrator executes mission and stores results correctly.

    ENFORCES ECHO-OR-SKIP RULE (E5):
    - MUST use "echo" mission only
    - Skip test if echo not available (no fallback to design/build)

    Must assert:
    - result.success is True
    - "mission_result" in final_state
    - "mission_results" in final_state and step.id in it
    """
    monkeypatch.chdir(temp_git_repo)

    # Check if echo mission is available (echo-or-skip rule)
    mission_available = False
    try:
        from runtime.orchestration import registry
        if hasattr(registry, 'MISSION_REGISTRY') and 'echo' in registry.MISSION_REGISTRY:
            mission_available = True
    except ImportError:
        try:
            from runtime.orchestration.missions import get_mission_class
            get_mission_class("echo")
            mission_available = True
        except:
            pass

    # ENFORCE: echo-or-skip (no fallback)
    if not mission_available:
        pytest.skip("Echo mission not available; test requires echo for determinism (echo-or-skip rule)")

    orchestrator = Orchestrator()

    # Workflow with echo mission step
    workflow = WorkflowDefinition(
        id="wf-mission-test",
        steps=[
            StepSpec(
                id="echo-step",
                kind="runtime",
                payload={
                    "operation": "mission",
                    "mission_type": "echo",
                    "inputs": {}
                }
            )
        ]
    )

    ctx = ExecutionContext(initial_state={})
    result = orchestrator.run_workflow(workflow, ctx)

    # REQUIRED ASSERTIONS (per instruction block E.P0.2)
    assert result.success is True, f"Expected success, got: {result.error_message}"
    assert "mission_result" in result.final_state, "mission_result not in final_state"
    assert "mission_results" in result.final_state, "mission_results not in final_state"
    assert "echo-step" in result.final_state["mission_results"], "echo-step not in mission_results"


def test_orchestrator_handles_unknown_mission_type():
    """
    Test unknown mission types are caught and reported.

    REQUIRED assertions (per instruction block E.P0.2):
    - result.success is False
    - result.failed_step_id == step.id
    - error_message contains mission_type (flexible matching)
    """
    orchestrator = Orchestrator()

    workflow = WorkflowDefinition(
        id="wf-unknown",
        steps=[
            StepSpec(
                id="unknown-step",
                kind="runtime",
                payload={
                    "operation": "mission",
                    "mission_type": "nonexistent_type_xyz",
                    "inputs": {}
                }
            )
        ]
    )

    result = orchestrator.run_workflow(workflow, ExecutionContext(initial_state={}))

    # REQUIRED ASSERTIONS (per instruction block E.P0.2)
    assert result.success is False, "Expected failure for unknown mission type"
    assert result.failed_step_id == "unknown-step", f"Expected failed_step_id='unknown-step', got {result.failed_step_id}"
    # Check error message contains mission type (flexible matching - avoid exact phrases)
    assert "nonexistent_type_xyz" in result.error_message, f"Error message should mention mission type: {result.error_message}"
