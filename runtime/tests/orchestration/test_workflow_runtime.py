from __future__ import annotations

from runtime.orchestration.coo.backlog import TaskEntry
from runtime.orchestration.dispatch.order import (
    ConstraintsSpec,
    ExecutionOrder,
    ShadowSpec,
    StepSpec,
    SupervisionSpec,
)
from runtime.orchestration.workflow_runtime import (
    REVIEW_DECISION_SCHEMA_VERSION,
    WorkflowRuntimeError,
    build_task_context,
    build_workflow_instance,
    record_invocation_finish,
    record_invocation_start,
    translate_order_to_workflow_instance,
    validate_resolution_packet,
)


def _task(*, task_type: str = "content") -> TaskEntry:
    return TaskEntry(
        id="T-123",
        title="Spec task",
        description="Write a typed workflow spec",
        dod="Spec exists and is reviewed",
        priority="P1",
        risk="med",
        scope_paths=["docs/specs/typed-workflow.md"],
        status="pending",
        requires_approval=True,
        owner="coo",
        evidence="",
        task_type=task_type,
        tags=["spec"],
        objective_ref="OBJ-1",
        created_at="2026-03-10T00:00:00Z",
    )


def _order(*, workflow_id: str | None = None, task_context: dict | None = None) -> ExecutionOrder:
    return ExecutionOrder(
        schema_version="execution_order.v1",
        order_id="ORD-T-123-20260310000000",
        task_ref="T-123",
        created_at="2026-03-10T00:00:00Z",
        steps=[
            StepSpec(name="draft", role="builder"),
            StepSpec(name="review", role="council_reviewer"),
        ],
        constraints=ConstraintsSpec(),
        shadow=ShadowSpec(),
        supervision=SupervisionSpec(),
        workflow_id=workflow_id,
        workflow_version=None,
        review_policy_id=None,
        mutation_policy_id=None,
        task_context=task_context,
    )


def test_build_task_context_for_content_task_is_structured() -> None:
    context = build_task_context(_task())

    payload = context["payload"]
    assert context["schema_version"] == "task_context.v1"
    assert payload["objective"] == "Write a typed workflow spec"
    assert payload["requested_artifact"]["artifact_type"] == "spec_markdown"
    assert payload["requested_artifact"]["format"] == "markdown"
    assert payload["scope"]["paths"] == ["docs/specs/typed-workflow.md"]
    assert payload["acceptance_criteria"] == ["Spec exists and is reviewed"]
    assert payload["approval_policy"]["requires_ceo_approval"] is True
    assert payload["priority_snapshot"]["priority"] == "P1"
    assert payload["workflow_selection_rationale"] == "task_type=content"


def test_translate_order_to_workflow_instance_uses_spec_creation_for_content() -> None:
    instance = translate_order_to_workflow_instance(_order(), task=_task())

    assert instance.workflow_id == "spec_creation.v1"
    assert instance.state == "READY"
    assert instance.current_step_id == "frame_request"
    assert instance.next_step_id == "draft_spec"
    assert "task_context.v1" in instance.artifact_refs
    assert instance.artifact_refs["task_context.v1"]["producer_role"] == "coo"
    assert instance.instance_state_hash
    assert instance.workflow_def_hash


def test_translate_order_to_workflow_instance_uses_legacy_adapter_for_build() -> None:
    instance = translate_order_to_workflow_instance(_order(), task=_task(task_type="build"))

    assert instance.workflow_id == "legacy_code_change.v1"
    assert instance.current_step_id == "hydrate"
    assert "legacy_build_packet.v1" in instance.artifact_refs


def test_invocation_records_return_recorded_terminal_result() -> None:
    instance = build_workflow_instance(
        workflow_id="spec_creation.v1",
        task_ref="T-123",
        order_id="ORD-T-123-20260310000000",
        task_context=build_task_context(_task()),
    )

    record = record_invocation_start(instance, step_id="frame_request", executor_identity="coo")
    record_invocation_finish(
        instance,
        record,
        result_ref="wf:ORD-T-123-20260310000000:task_context_v1:task-context",
        result_status="SUCCESS",
    )

    duplicate = record_invocation_start(instance, step_id="frame_request", executor_identity="coo")
    assert duplicate.invocation_key == record.invocation_key
    assert duplicate.lease_status == "COMPLETED"
    assert duplicate.result_status == "SUCCESS"


def test_validate_resolution_packet_accepts_resume_for_checkpointed_instance() -> None:
    instance = build_workflow_instance(
        workflow_id="spec_creation.v1",
        task_ref="T-123",
        order_id="ORD-T-123-20260310000000",
        task_context=build_task_context(_task()),
    )
    instance.state = "CHECKPOINTED"

    resolution = validate_resolution_packet(
        {
            "workflow_instance_ref": instance.instance_id,
            "expected_prior_state": "CHECKPOINTED",
            "expected_workflow_def_hash": instance.workflow_def_hash,
            "resolution_action": "RESUME_CURRENT_STEP",
            "actor": "ceo",
            "issued_at": "2026-03-10T00:10:00Z",
            "note": "resume",
        },
        instance,
    )

    assert resolution.resolution_action == "RESUME_CURRENT_STEP"


def test_validate_resolution_packet_fails_closed_on_hash_mismatch() -> None:
    instance = build_workflow_instance(
        workflow_id="spec_creation.v1",
        task_ref="T-123",
        order_id="ORD-T-123-20260310000000",
        task_context=build_task_context(_task()),
    )
    instance.state = "CHECKPOINTED"

    try:
        validate_resolution_packet(
            {
                "workflow_instance_ref": instance.instance_id,
                "expected_prior_state": "CHECKPOINTED",
                "expected_workflow_def_hash": "bad-hash",
                "resolution_action": "RESUME_CURRENT_STEP",
                "actor": "ceo",
                "issued_at": "2026-03-10T00:10:00Z",
                "note": "resume",
            },
            instance,
        )
    except WorkflowRuntimeError as exc:
        assert "workflow_def_hash mismatch" in str(exc)
    else:
        raise AssertionError("expected WorkflowRuntimeError")


def test_review_decision_key_is_reserved_for_typed_review_outputs() -> None:
    instance = translate_order_to_workflow_instance(_order(), task=_task(task_type="build"))

    assert REVIEW_DECISION_SCHEMA_VERSION not in instance.artifact_refs
