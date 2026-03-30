"""Helpers for COO mirror evaluation runs."""

from __future__ import annotations

from typing import Any

from runtime.orchestration.coo.claim_verifier import EvidenceSnapshot


def diff_evidence(before: EvidenceSnapshot, after: EvidenceSnapshot) -> dict[str, Any]:
    """Return a stable diff between two frozen evidence snapshots."""
    before_status = {task.id: task.status for task in before.tasks}
    after_status = {task.id: task.status for task in after.tasks}

    task_status_deltas = []
    for task_id in sorted(set(before_status) | set(after_status)):
        if before_status.get(task_id) != after_status.get(task_id):
            task_status_deltas.append(
                {
                    "task_id": task_id,
                    "before": before_status.get(task_id),
                    "after": after_status.get(task_id),
                }
            )

    return {
        "new_escalation_ids": sorted(set(after.escalation_ids) - set(before.escalation_ids)),
        "new_inbox_orders": sorted(set(after.inbox_orders) - set(before.inbox_orders)),
        "new_active_orders": sorted(set(after.active_orders) - set(before.active_orders)),
        "new_completed_orders": sorted(
            order_id
            for order_id in after.completed_orders
            if order_id not in before.completed_orders
        ),
        "task_status_deltas": task_status_deltas,
    }


def classify_side_effect(diff: dict[str, Any]) -> str:
    """Classify the observable external side effect produced by a run."""
    if diff["new_escalation_ids"]:
        return "queued_escalation"
    if diff["new_inbox_orders"] or diff["new_active_orders"] or diff["new_completed_orders"]:
        return "orders_created"
    if diff["task_status_deltas"]:
        return "backlog_status_change"
    return "none"


def assess_inside_outside_consistency(packet_family: str, diff: dict[str, Any]) -> bool:
    """Check whether the outside side effects match the inside packet family."""
    side_effect = classify_side_effect(diff)
    if packet_family == "escalation_packet":
        return side_effect == "queued_escalation"
    if packet_family in {"task_proposal", "nothing_to_propose"}:
        return side_effect in {"none", "backlog_status_change"}
    return False


def build_evaluation_row(
    *,
    scenario_id: str,
    mode: str,
    source_kind: str,
    input_ref: str,
    expected_packet_family: str,
    actual_packet_family: str,
    parse_status: str,
    parse_recovery_stage: str,
    claim_verifier_status: str,
    diff: dict[str, Any],
    invocation_receipt_ref: str | None,
    token_usage: dict[str, int] | None,
    notes: str = "",
    openclaw_runtime_observation: str = "unavailable",
) -> dict[str, Any]:
    """Build a stable evaluation row for fixture or live mirror runs."""
    return {
        "scenario_id": scenario_id,
        "mode": mode,
        "source_kind": source_kind,
        "input_ref": input_ref,
        "expected_packet_family": expected_packet_family,
        "actual_packet_family": actual_packet_family,
        "parse_status": parse_status,
        "parse_recovery_stage": parse_recovery_stage,
        "claim_verifier_status": claim_verifier_status,
        "inside_outside_consistent": assess_inside_outside_consistency(actual_packet_family, diff),
        "side_effect_class": classify_side_effect(diff),
        "new_escalation_ids": diff["new_escalation_ids"],
        "new_order_ids": diff["new_inbox_orders"]
        + diff["new_active_orders"]
        + diff["new_completed_orders"],
        "task_status_deltas": diff["task_status_deltas"],
        "invocation_receipt_ref": invocation_receipt_ref,
        "token_usage": token_usage,
        "openclaw_runtime_observation": openclaw_runtime_observation,
        "notes": notes,
    }
