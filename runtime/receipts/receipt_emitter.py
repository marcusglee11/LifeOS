"""
Acceptance receipt, blocked report, and review summary emitter.

Builds v2.4 schema-compliant receipts, validates before return.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .ulid import generate_ulid
from .validator import assert_valid

# Pilot policy (Phase A: only policy_id required)
PILOT_POLICY: dict = {"policy_id": "pilot-default", "policy_version": "1.0"}
PIPELINE_ID: str = "lifeos-receipts-pilot-b1"


def compute_decision(gate_rollup: dict) -> dict:
    """
    Compute decision dict from gate rollup.

    Rules (v2.4 allOf):
    - ACCEPTED: overall_status == PASS -> no reason_code
    - REJECTED: overall_status == FAIL -> reason_code = GATE_FAIL
    - BLOCKED: overall_status == BLOCKED -> reason_code = BLOCKED_GATES

    Args:
        gate_rollup: Dict with 'overall_status' key.

    Returns:
        Decision dict with 'status' and optional 'reason_code'.

    Raises:
        ValueError: If gate_rollup.overall_status is unknown.
    """
    status = gate_rollup.get("overall_status", "FAIL")
    if status == "PASS":
        return {"status": "ACCEPTED"}
    elif status == "FAIL":
        return {"status": "REJECTED", "reason_code": "GATE_FAIL"}
    elif status == "BLOCKED":
        return {"status": "BLOCKED", "reason_code": "BLOCKED_GATES"}
    elif status == "WARN":
        # WARN maps to ACCEPTED (warnings are non-blocking)
        return {"status": "ACCEPTED"}
    else:
        raise ValueError(f"Unknown gate_rollup overall_status: {status!r}")


def build_acceptance_receipt(
    workspace_sha: str,
    workspace_tree_oid: str,
    plan_core_sha256: str,
    emitter: Any,
    decision: dict,
    gate_rollup: dict,
    refs: list[dict] | None = None,
    supersedes: str | None = None,
    policy_pack: dict | None = None,
) -> dict:
    """
    Build a v2.4 acceptance receipt dict.

    Args:
        workspace_sha: Workspace commit SHA.
        workspace_tree_oid: Workspace tree OID (40-char hex).
        plan_core_sha256: Plan core SHA-256 (64-char hex).
        emitter: RunLogEmitter instance (unused directly; reserved for stats).
        decision: Decision dict (from compute_decision).
        gate_rollup: Gate rollup dict.
        refs: Optional list of artefact ref dicts.
        supersedes: Optional receipt_id of the receipt this supersedes.
        policy_pack: Optional policy pack dict (defaults to PILOT_POLICY).

    Returns:
        Schema-validated acceptance receipt dict.

    Raises:
        ReceiptValidationError: If the receipt fails v2.4 schema validation.
    """
    receipt: dict[str, Any] = {
        "receipt_id": generate_ulid(),
        "schema_version": "2.4",
        "workspace_sha": workspace_sha,
        "workspace_tree_oid": workspace_tree_oid,
        "plan_core_sha256": plan_core_sha256,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "policy_pack": policy_pack if policy_pack is not None else PILOT_POLICY,
        "decision": decision,
        "gate_rollup": gate_rollup,
    }
    if refs:
        receipt["artefact_refs"] = refs
    if supersedes is not None:
        receipt["supersedes"] = supersedes

    receipt["_ext"] = {"pipeline_id": PIPELINE_ID}

    assert_valid(receipt, "acceptance_receipt")
    return receipt


def build_blocked_report(
    workspace_sha: str,
    plan_core_sha256: str,
    reason_code: str,
    gate_rollup: dict | None = None,
    refs: list[dict] | None = None,
) -> dict:
    """
    Build a v2.4 blocked report dict.

    Args:
        workspace_sha: Workspace commit SHA.
        plan_core_sha256: Plan core SHA-256 (64-char hex).
        reason_code: Reason for blocking.
        gate_rollup: Optional gate rollup dict.
        refs: Optional list of artefact ref dicts.

    Returns:
        Schema-validated blocked report dict.

    Raises:
        ReceiptValidationError: If the report fails v2.4 schema validation.
    """
    report: dict[str, Any] = {
        "report_id": generate_ulid(),
        "schema_version": "2.4",
        "workspace_sha": workspace_sha,
        "plan_core_sha256": plan_core_sha256,
        "issued_at": datetime.now(timezone.utc).isoformat(),
        "reason_code": reason_code,
    }
    if gate_rollup:
        report["gate_rollup"] = gate_rollup
    if refs:
        report["artefact_refs"] = refs

    assert_valid(report, "blocked_report")
    return report


def build_land_receipt(
    landed_sha: str,
    landed_tree_oid: str,
    land_target: str,
    merge_method: str,
    acceptance_receipt_id: str,
    workspace_sha: str,
    workspace_tree_oid: str,
    plan_core_sha256: str,
    agent_id: str,
    run_id: str,
    landing_evidence: dict | None = None,
) -> dict:
    """
    Build a v2.4 land receipt dict.

    Computes tree_equivalence (workspace_tree_oid == landed_tree_oid).
    match=True means code identity is preserved through merge.

    Returns:
        Schema-validated land receipt dict.

    Raises:
        ReceiptValidationError: If the receipt fails v2.4 schema validation.
    """
    tree_match = workspace_tree_oid == landed_tree_oid
    receipt: dict[str, Any] = {
        "receipt_id": generate_ulid(),
        "schema_version": "land_receipt.v2.4",
        "receipt_type": "land",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "landed_sha": landed_sha,
        "landed_tree_oid": landed_tree_oid,
        "land_target": land_target,
        "merge_method": merge_method,
        "acceptance_lineage": {
            "acceptance_receipt_id": acceptance_receipt_id,
            "workspace_sha": workspace_sha,
            "workspace_tree_oid": workspace_tree_oid,
            "plan_core_sha256": plan_core_sha256,
        },
        "tree_equivalence": {
            "workspace_tree_oid": workspace_tree_oid,
            "landed_tree_oid": landed_tree_oid,
            "match": tree_match,
            "verified_by": "land_emitter",
        },
        "emitter": {
            "agent_id": agent_id,
            "run_id": run_id,
        },
    }
    if landing_evidence is not None:
        receipt["landing_evidence"] = landing_evidence

    assert_valid(receipt, "land_receipt")
    return receipt


def build_review_summary(
    gate_rollup: dict,
    evidence_manifest: list[dict] | None = None,
    runlog_stats: dict | None = None,
) -> dict:
    """
    Build a review summary dict.

    Args:
        gate_rollup: Gate rollup dict with overall_status.
        evidence_manifest: Optional list of artefact ref dicts.
        runlog_stats: Optional runlog statistics dict.

    Returns:
        Schema-validated review summary dict.
    """
    summary: dict[str, Any] = {
        "overall_status": gate_rollup.get("overall_status", "PASS"),
        "gate_count": 0,
        "pass_count": 0,
        "fail_count": 0,
    }
    if evidence_manifest:
        summary["evidence_manifest"] = evidence_manifest
    if runlog_stats:
        summary["runlog_stats"] = runlog_stats

    assert_valid(summary, "review_summary")
    return summary
