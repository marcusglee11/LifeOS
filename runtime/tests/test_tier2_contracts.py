# runtime/tests/test_tier2_contracts.py
from typing import Dict, Any

import pytest

from runtime.orchestration.engine import (
    Orchestrator,
    WorkflowDefinition,
    StepSpec,
    ExecutionContext,
    OrchestrationResult,
)


def _make_minimal_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        id="wf-contract-minimal",
        steps=[
            StepSpec(
                id="step-0",
                kind="runtime",
                payload={"operation": "noop"},
            )
        ],
        metadata={"purpose": "contract-test"},
    )


def test_run_workflow_contract_basic_shape():
    """
    Contract: run_workflow(workflow, context) returns an OrchestrationResult that:
    - Has .success (bool)
    - Has .executed_steps (list[StepSpec-like])
    - Has .final_state (dict-like)
    - Has .lineage (dict/list)
    - Has .receipt (dict/list)
    """
    orchestrator = Orchestrator()
    workflow = _make_minimal_workflow()
    ctx = ExecutionContext(initial_state={"foo": "bar"})

    result: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)

    assert isinstance(result.success, bool)
    assert isinstance(result.executed_steps, list)
    assert isinstance(result.final_state, dict)
    assert result.lineage is not None
    assert result.receipt is not None


def test_run_workflow_does_not_mutate_input_workflow():
    orchestrator = Orchestrator()
    workflow = _make_minimal_workflow()
    ctx = ExecutionContext(initial_state={})

    before = workflow.to_dict()
    _ = orchestrator.run_workflow(workflow, ctx)
    after = workflow.to_dict()

    assert before == after, "WorkflowDefinition must not be mutated by run_workflow."


def test_run_workflow_does_not_mutate_input_context_state():
    orchestrator = Orchestrator()
    workflow = _make_minimal_workflow()
    ctx = ExecutionContext(initial_state={"foo": "bar"})

    before = dict(ctx.initial_state)
    _ = orchestrator.run_workflow(workflow, ctx)
    after = dict(ctx.initial_state)

    assert before == after, "ExecutionContext.initial_state must remain immutable."


def test_run_workflow_records_human_steps_in_receipt():
    """
    Contract: any 'human' step must be represented explicitly in the receipt/lineage,
    so that attestation and audit are possible.
    """
    orchestrator = Orchestrator()

    workflow = WorkflowDefinition(
        id="wf-contract-human",
        steps=[
            StepSpec(
                id="human-0",
                kind="human",
                payload={"description": "User approval required"},
            ),
            StepSpec(
                id="runtime-1",
                kind="runtime",
                payload={"operation": "noop"},
            ),
        ],
        metadata={"purpose": "contract-human"},
    )
    ctx = ExecutionContext(initial_state={})

    result: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)

    assert result.success in (True, False)  # may require explicit approval handling
    # Receipt must mention the human step explicitly
    receipt_dict: Dict[str, Any] = result.receipt
    all_step_ids = receipt_dict.get("steps", [])
    assert "human-0" in all_step_ids


def test_orchestration_result_serialises_cleanly():
    """
    Contract: OrchestrationResult must expose a .to_dict() method that
    returns a pure-JSON-serialisable structure for logging and persistence.
    """
    orchestrator = Orchestrator()
    workflow = _make_minimal_workflow()
    ctx = ExecutionContext(initial_state={"foo": "bar"})

    result: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)
    as_dict = result.to_dict()

    assert isinstance(as_dict, dict)
    # All children should be natively serialisable: lists, dicts, strings, ints, bools, None.
    # We don't exhaustively check here, but spot-check a few fields:
    assert isinstance(as_dict.get("id"), str)
    assert isinstance(as_dict.get("success"), bool)
    assert isinstance(as_dict.get("executed_steps"), list)
