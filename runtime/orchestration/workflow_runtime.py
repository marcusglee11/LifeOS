"""Typed workflow runtime contracts and compatibility translation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional

import yaml

from runtime.orchestration.coo.backlog import TaskEntry

if TYPE_CHECKING:
    from runtime.orchestration.dispatch.order import ExecutionOrder


WORKFLOW_SCHEMA_VERSION = "workflow_runtime.v1"
TASK_CONTEXT_SCHEMA_VERSION = "task_context.v1"
REVIEW_DECISION_SCHEMA_VERSION = "review_decision.v1"
PACKAGED_SPEC_SCHEMA_VERSION = "packaged_spec.v1"
CEO_RESOLUTION_SCHEMA_VERSION = "ceo_resolution.v1"

WORKFLOW_STATES = frozenset(
    {
        "CREATED",
        "READY",
        "RUNNING",
        "AWAITING_REVIEW_DECISION",
        "REVISION_PENDING",
        "CHECKPOINTED",
        "COMPLETED",
        "BLOCKED",
        "REJECTED",
        "ABORTED",
    }
)
TERMINAL_WORKFLOW_STATES = frozenset({"COMPLETED", "BLOCKED", "REJECTED", "ABORTED"})
RESOLUTION_ACTIONS = frozenset({"RESUME_CURRENT_STEP", "FORCE_REJECT", "ABORT_WORKFLOW"})


class WorkflowRuntimeError(ValueError):
    """Raised when typed workflow contracts are invalid."""


def _canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _artifact_id(instance_id: str, artifact_type: str, suffix: str) -> str:
    slug = artifact_type.replace(".", "_")
    return f"{instance_id}:{slug}:{suffix}"


@dataclass(frozen=True)
class WorkflowArtifact:
    artifact_id: str
    artifact_type: str
    schema_version: str
    producer_role: str
    workflow_instance_id: str
    created_at: str
    payload: Dict[str, Any]
    sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "artifact_type": self.artifact_type,
            "schema_version": self.schema_version,
            "producer_role": self.producer_role,
            "workflow_instance_id": self.workflow_instance_id,
            "created_at": self.created_at,
            "payload": self.payload,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class WorkflowStepDefinition:
    step_id: str
    step_name: str
    step_kind: str
    role: str
    mission_type: Optional[str]
    consumes: tuple[str, ...] = field(default_factory=tuple)
    produces: Optional[str] = None
    mutation_class: str = "closure"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_name": self.step_name,
            "step_kind": self.step_kind,
            "role": self.role,
            "mission_type": self.mission_type,
            "consumes": list(self.consumes),
            "produces": self.produces,
            "mutation_class": self.mutation_class,
        }


@dataclass(frozen=True)
class WorkflowDefinition:
    workflow_id: str
    schema_version: str
    workflow_class: str
    review_policy_id: Optional[str]
    mutation_policy_id: str
    compat_mode: str
    steps: tuple[WorkflowStepDefinition, ...]
    max_revision_attempts: int = 2

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "schema_version": self.schema_version,
            "workflow_class": self.workflow_class,
            "review_policy_id": self.review_policy_id,
            "mutation_policy_id": self.mutation_policy_id,
            "compat_mode": self.compat_mode,
            "max_revision_attempts": self.max_revision_attempts,
            "steps": [step.to_dict() for step in self.steps],
        }

    @property
    def workflow_def_hash(self) -> str:
        return _sha256_text(_canonical_json(self.to_dict()))


@dataclass
class StepInvocationRecord:
    invocation_key: str
    workflow_instance_ref: str
    workflow_def_hash: str
    step_id: str
    attempt_index: int
    instance_state_hash_before: str
    executor_identity: str
    lease_status: str
    started_at: str
    completed_at: Optional[str] = None
    result_ref: Optional[str] = None
    result_status: Optional[str] = None
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "invocation_key": self.invocation_key,
            "workflow_instance_ref": self.workflow_instance_ref,
            "workflow_def_hash": self.workflow_def_hash,
            "step_id": self.step_id,
            "attempt_index": self.attempt_index,
            "instance_state_hash_before": self.instance_state_hash_before,
            "executor_identity": self.executor_identity,
            "lease_status": self.lease_status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result_ref": self.result_ref,
            "result_status": self.result_status,
            "error_code": self.error_code,
        }


@dataclass
class WorkflowInstance:
    instance_id: str
    workflow_id: str
    workflow_def_hash: str
    task_ref: str
    order_id: str
    state: str
    current_step_id: Optional[str]
    next_step_id: Optional[str]
    last_completed_step_id: Optional[str]
    attempt_index: int
    revision_count: int
    task_context: Dict[str, Any]
    artifact_refs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    review_history: list[Dict[str, Any]] = field(default_factory=list)
    approval_state: Dict[str, Any] = field(default_factory=dict)
    escalation_state: Dict[str, Any] = field(default_factory=dict)
    checkpoint_ref: Optional[str] = None
    policy_hash: Optional[str] = None
    baseline_commit: Optional[str] = None
    resume_token: Optional[str] = None
    invocation_records: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "workflow_id": self.workflow_id,
            "workflow_def_hash": self.workflow_def_hash,
            "task_ref": self.task_ref,
            "order_id": self.order_id,
            "state": self.state,
            "current_step_id": self.current_step_id,
            "next_step_id": self.next_step_id,
            "last_completed_step_id": self.last_completed_step_id,
            "attempt_index": self.attempt_index,
            "revision_count": self.revision_count,
            "task_context": self.task_context,
            "artifact_refs": self.artifact_refs,
            "review_history": self.review_history,
            "approval_state": self.approval_state,
            "escalation_state": self.escalation_state,
            "checkpoint_ref": self.checkpoint_ref,
            "policy_hash": self.policy_hash,
            "baseline_commit": self.baseline_commit,
            "resume_token": self.resume_token,
            "invocation_records": self.invocation_records,
        }

    @property
    def instance_state_hash(self) -> str:
        payload = {
            "state": self.state,
            "current_step_id": self.current_step_id,
            "next_step_id": self.next_step_id,
            "last_completed_step_id": self.last_completed_step_id,
            "attempt_index": self.attempt_index,
            "revision_count": self.revision_count,
            "artifact_refs": self.artifact_refs,
            "review_history": self.review_history,
            "approval_state": self.approval_state,
            "escalation_state": self.escalation_state,
            "checkpoint_ref": self.checkpoint_ref,
        }
        return _sha256_text(_canonical_json(payload))


@dataclass(frozen=True)
class CEOResolutionPacket:
    workflow_instance_ref: str
    expected_prior_state: str
    expected_workflow_def_hash: str
    resolution_action: str
    actor: str
    issued_at: str
    note: str
    override_metadata: Optional[Dict[str, Any]] = None

    def validate(self) -> None:
        if self.expected_prior_state not in WORKFLOW_STATES:
            raise WorkflowRuntimeError(f"Unsupported prior state {self.expected_prior_state!r}")
        if self.resolution_action not in RESOLUTION_ACTIONS:
            raise WorkflowRuntimeError(f"Unsupported resolution_action {self.resolution_action!r}")


def build_task_context(
    task: Optional[TaskEntry],
    *,
    order: Optional[ExecutionOrder] = None,
    objective: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the structured control-plane task context."""
    requested_type = "spec_markdown" if task and task.task_type == "content" else "code_change"
    destination = task.scope_paths[0] if task and task.scope_paths else None
    payload = {
        "objective": objective
        or (task.description if task and task.description else (order.task_ref if order else "")),
        "requested_artifact": {
            "artifact_type": requested_type,
            "format": "markdown" if task and task.task_type == "content" else "yaml",
            "destination": destination,
        },
        "scope": {
            "paths": list(
                task.scope_paths if task else (order.constraints.scope_paths if order else [])
            ),
            "in_scope": list(task.scope_paths if task else []),
            "out_of_scope": [],
        },
        "non_goals": [],
        "constraints": {
            "governance": [],
            "runtime": [],
            "delivery": [],
        },
        "dependencies": [],
        "authoritative_inputs": [
            {
                "kind": "backlog_task" if task else "order",
                "ref": task.id if task else (order.task_ref if order else ""),
                "description": task.title if task else "compat order translation",
            }
        ],
        "acceptance_criteria": [task.dod] if task and task.dod else [],
        "approval_policy": {
            "requires_ceo_approval": bool(task.requires_approval) if task else True,
            "approval_source": "coo_approve" if task else "compat",
            "checkpoint_on_reject": True,
        },
        "priority_snapshot": {
            "priority": task.priority if task else "P2",
            "urgency": None,
        },
        "workflow_selection_rationale": (
            f"task_type={task.task_type}" if task else "compat legacy routing"
        ),
    }
    return {
        "artifact_type": TASK_CONTEXT_SCHEMA_VERSION,
        "schema_version": TASK_CONTEXT_SCHEMA_VERSION,
        "payload": payload,
    }


def _make_artifact(
    *,
    instance_id: str,
    artifact_type: str,
    schema_version: str,
    producer_role: str,
    payload: Dict[str, Any],
    suffix: str,
) -> WorkflowArtifact:
    canonical = _canonical_json(payload)
    return WorkflowArtifact(
        artifact_id=_artifact_id(instance_id, artifact_type, suffix),
        artifact_type=artifact_type,
        schema_version=schema_version,
        producer_role=producer_role,
        workflow_instance_id=instance_id,
        created_at=_now_iso(),
        payload=payload,
        sha256=_sha256_text(canonical),
    )


def _spec_creation_definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="spec_creation.v1",
        schema_version=WORKFLOW_SCHEMA_VERSION,
        workflow_class="native",
        review_policy_id="spec_review.v1",
        mutation_policy_id="mutation_authority.v1",
        compat_mode="native",
        max_revision_attempts=2,
        steps=(
            WorkflowStepDefinition(
                "frame_request",
                "Frame Request",
                "metadata",
                "coo",
                None,
                (),
                TASK_CONTEXT_SCHEMA_VERSION,
                "framing",
            ),
            WorkflowStepDefinition(
                "draft_spec",
                "Draft Spec",
                "design",
                "designer",
                "design",
                (TASK_CONTEXT_SCHEMA_VERSION,),
                "design_spec.v1",
                "substantive",
            ),
            WorkflowStepDefinition(
                "architect_review",
                "Architect Review",
                "review",
                "reviewer_architect",
                "review",
                ("design_spec.v1",),
                REVIEW_DECISION_SCHEMA_VERSION,
                "review_control",
            ),
            WorkflowStepDefinition(
                "revise_spec",
                "Revise Spec",
                "revise",
                "designer",
                "design",
                (TASK_CONTEXT_SCHEMA_VERSION, "design_spec.v1", REVIEW_DECISION_SCHEMA_VERSION),
                "design_spec.v1",
                "substantive",
            ),
            WorkflowStepDefinition(
                "package_spec",
                "Package Spec",
                "package",
                "steward",
                None,
                ("design_spec.v1", REVIEW_DECISION_SCHEMA_VERSION),
                PACKAGED_SPEC_SCHEMA_VERSION,
                "packaging",
            ),
            WorkflowStepDefinition(
                "close_spec",
                "Close Spec",
                "steward",
                "steward",
                None,
                (PACKAGED_SPEC_SCHEMA_VERSION,),
                None,
                "closure",
            ),
        ),
    )


def _legacy_code_change_definition() -> WorkflowDefinition:
    return WorkflowDefinition(
        workflow_id="legacy_code_change.v1",
        schema_version=WORKFLOW_SCHEMA_VERSION,
        workflow_class="legacy_adapter",
        review_policy_id="legacy_build_review.v1",
        mutation_policy_id="mutation_authority.v1",
        compat_mode="legacy_adapter",
        max_revision_attempts=2,
        steps=(
            WorkflowStepDefinition(
                "hydrate", "Hydrate", "metadata", "coo", None, (), None, "framing"
            ),
            WorkflowStepDefinition(
                "policy", "Policy", "metadata", "coo", None, (), None, "framing"
            ),
            WorkflowStepDefinition(
                "design",
                "Design",
                "design",
                "designer",
                "design",
                (TASK_CONTEXT_SCHEMA_VERSION,),
                "legacy_build_packet.v1",
                "substantive",
            ),
            WorkflowStepDefinition(
                "build",
                "Build",
                "build",
                "builder",
                "build",
                ("legacy_build_packet.v1",),
                "legacy_review_packet.v1",
                "substantive",
            ),
            WorkflowStepDefinition(
                "review",
                "Review",
                "review",
                "reviewer_architect",
                "review",
                ("legacy_review_packet.v1",),
                REVIEW_DECISION_SCHEMA_VERSION,
                "review_control",
            ),
            WorkflowStepDefinition(
                "steward",
                "Steward",
                "steward",
                "steward",
                "steward",
                ("legacy_review_packet.v1", REVIEW_DECISION_SCHEMA_VERSION),
                None,
                "closure",
            ),
        ),
    )


WORKFLOW_REGISTRY: Dict[str, WorkflowDefinition] = {
    "spec_creation.v1": _spec_creation_definition(),
    "legacy_code_change.v1": _legacy_code_change_definition(),
}


def get_workflow_definition(workflow_id: str) -> WorkflowDefinition:
    try:
        return WORKFLOW_REGISTRY[workflow_id]
    except KeyError as exc:
        raise WorkflowRuntimeError(f"Unknown workflow_id {workflow_id!r}") from exc


def resolve_workflow_id_for_task_type(task_type: str) -> str:
    if task_type == "content":
        return "spec_creation.v1"
    return "legacy_code_change.v1"


def build_workflow_instance(
    *,
    workflow_id: str,
    task_ref: str,
    order_id: str,
    task_context: Dict[str, Any],
    approval_state: Optional[Dict[str, Any]] = None,
) -> WorkflowInstance:
    definition = get_workflow_definition(workflow_id)
    first_step = definition.steps[0].step_id if definition.steps else None
    second_step = definition.steps[1].step_id if len(definition.steps) > 1 else None
    instance_id = f"wf:{order_id}"
    return WorkflowInstance(
        instance_id=instance_id,
        workflow_id=workflow_id,
        workflow_def_hash=definition.workflow_def_hash,
        task_ref=task_ref,
        order_id=order_id,
        state="READY",
        current_step_id=first_step,
        next_step_id=second_step,
        last_completed_step_id=None,
        attempt_index=0,
        revision_count=0,
        task_context=task_context,
        approval_state=approval_state or {"status": "approved"},
    )


def translate_order_to_workflow_instance(
    order: ExecutionOrder,
    *,
    task: Optional[TaskEntry] = None,
) -> WorkflowInstance:
    workflow_id = order.workflow_id or resolve_workflow_id_for_task_type(
        task.task_type if task else "build"
    )
    task_context = order.task_context or build_task_context(task, order=order)
    instance = build_workflow_instance(
        workflow_id=workflow_id,
        task_ref=order.task_ref,
        order_id=order.order_id,
        task_context=task_context,
    )
    instance.artifact_refs[TASK_CONTEXT_SCHEMA_VERSION] = _make_artifact(
        instance_id=instance.instance_id,
        artifact_type=TASK_CONTEXT_SCHEMA_VERSION,
        schema_version=TASK_CONTEXT_SCHEMA_VERSION,
        producer_role="coo",
        payload=task_context["payload"],
        suffix="task-context",
    ).to_dict()

    if workflow_id == "legacy_code_change.v1":
        # Compatibility shim so direct design/build/review steps have a typed starting artefact.
        payload = {
            "goal": task_context["payload"]["objective"] or order.task_ref,
            "context_refs": [],
        }
        instance.artifact_refs["legacy_build_packet.v1"] = _make_artifact(
            instance_id=instance.instance_id,
            artifact_type="legacy_build_packet.v1",
            schema_version="legacy_build_packet.v1",
            producer_role="designer",
            payload=payload,
            suffix="legacy-build",
        ).to_dict()
    return instance


def translate_task_spec_to_workflow_instance(
    task_spec: Dict[str, Any], *, run_id: str
) -> WorkflowInstance:
    task_context = build_task_context(
        None,
        objective=str(task_spec.get("task", "")).strip(),
    )
    instance = build_workflow_instance(
        workflow_id="legacy_code_change.v1",
        task_ref=str(task_spec.get("task_ref", run_id)),
        order_id=str(task_spec.get("order_id", run_id)),
        task_context=task_context,
    )
    instance.artifact_refs[TASK_CONTEXT_SCHEMA_VERSION] = _make_artifact(
        instance_id=instance.instance_id,
        artifact_type=TASK_CONTEXT_SCHEMA_VERSION,
        schema_version=TASK_CONTEXT_SCHEMA_VERSION,
        producer_role="coo",
        payload=task_context["payload"],
        suffix="task-context",
    ).to_dict()
    return instance


def compute_invocation_key(
    instance: WorkflowInstance,
    step_id: str,
    executor_identity: str,
) -> str:
    payload = {
        "workflow_instance_ref": instance.instance_id,
        "step_id": step_id,
        "attempt_index": instance.attempt_index,
        "workflow_def_hash": instance.workflow_def_hash,
        "instance_state_hash_before": instance.instance_state_hash,
        "executor_identity": executor_identity,
    }
    return _sha256_text(_canonical_json(payload))


def record_invocation_start(
    instance: WorkflowInstance, *, step_id: str, executor_identity: str
) -> StepInvocationRecord:
    invocation_key = compute_invocation_key(instance, step_id, executor_identity)
    existing = instance.invocation_records.get(invocation_key)
    if existing:
        status = str(existing.get("lease_status", ""))
        if status in {"COMPLETED", "FAILED", "VOID"}:
            return StepInvocationRecord(**existing)
        raise WorkflowRuntimeError(f"Invocation already in progress for key {invocation_key}")

    record = StepInvocationRecord(
        invocation_key=invocation_key,
        workflow_instance_ref=instance.instance_id,
        workflow_def_hash=instance.workflow_def_hash,
        step_id=step_id,
        attempt_index=instance.attempt_index,
        instance_state_hash_before=instance.instance_state_hash,
        executor_identity=executor_identity,
        lease_status="RUNNING",
        started_at=_now_iso(),
    )
    instance.invocation_records[invocation_key] = record.to_dict()
    return record


def record_invocation_finish(
    instance: WorkflowInstance,
    record: StepInvocationRecord,
    *,
    result_ref: Optional[str],
    result_status: str,
    error_code: Optional[str] = None,
) -> None:
    record.lease_status = "COMPLETED"
    record.completed_at = _now_iso()
    record.result_ref = result_ref
    record.result_status = result_status
    record.error_code = error_code
    instance.invocation_records[record.invocation_key] = record.to_dict()


def get_step(
    definition: WorkflowDefinition, step_id: Optional[str]
) -> Optional[WorkflowStepDefinition]:
    if step_id is None:
        return None
    for step in definition.steps:
        if step.step_id == step_id:
            return step
    return None


def next_step_id(definition: WorkflowDefinition, step_id: str) -> Optional[str]:
    ids = [step.step_id for step in definition.steps]
    try:
        idx = ids.index(step_id)
    except ValueError:
        return None
    if idx + 1 >= len(ids):
        return None
    return ids[idx + 1]


def materialize_packaged_spec(
    instance: WorkflowInstance, *, producer_role: str = "steward"
) -> WorkflowArtifact:
    design = instance.artifact_refs.get("design_spec.v1")
    if not design:
        raise WorkflowRuntimeError("design_spec.v1 is required for package_spec")
    review = instance.artifact_refs.get(REVIEW_DECISION_SCHEMA_VERSION)
    if not review:
        raise WorkflowRuntimeError("review_decision.v1 is required for package_spec")

    body = yaml.dump(design["payload"], sort_keys=True, default_flow_style=False)
    body_sha = _sha256_text(body)
    payload = {
        "format": "markdown",
        "body": body,
        "body_sha256": body_sha,
        "review_ref": review["artifact_id"],
        "source_design_ref": design["artifact_id"],
    }
    return _make_artifact(
        instance_id=instance.instance_id,
        artifact_type=PACKAGED_SPEC_SCHEMA_VERSION,
        schema_version=PACKAGED_SPEC_SCHEMA_VERSION,
        producer_role=producer_role,
        payload=payload,
        suffix="packaged-spec",
    )


def validate_resolution_packet(
    packet: Dict[str, Any], instance: WorkflowInstance
) -> CEOResolutionPacket:
    required = {
        "workflow_instance_ref",
        "expected_prior_state",
        "expected_workflow_def_hash",
        "resolution_action",
        "actor",
        "issued_at",
        "note",
    }
    missing = sorted(required - set(packet))
    if missing:
        raise WorkflowRuntimeError(f"Resolution packet missing fields: {missing}")
    resolution = CEOResolutionPacket(
        workflow_instance_ref=str(packet["workflow_instance_ref"]),
        expected_prior_state=str(packet["expected_prior_state"]),
        expected_workflow_def_hash=str(packet["expected_workflow_def_hash"]),
        resolution_action=str(packet["resolution_action"]),
        actor=str(packet["actor"]),
        issued_at=str(packet["issued_at"]),
        note=str(packet["note"]),
        override_metadata=packet.get("override_metadata"),
    )
    resolution.validate()
    if resolution.workflow_instance_ref != instance.instance_id:
        raise WorkflowRuntimeError("Resolution packet workflow_instance_ref mismatch")
    if resolution.expected_prior_state != instance.state:
        raise WorkflowRuntimeError("Resolution packet expected_prior_state mismatch")
    if resolution.expected_workflow_def_hash != instance.workflow_def_hash:
        raise WorkflowRuntimeError("Resolution packet workflow_def_hash mismatch")
    return resolution
