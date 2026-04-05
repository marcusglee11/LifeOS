"""
Phase C post-merge land gate (§10.2 land receipt emission).

After a successful merge, emit a land receipt binding landed_tree_oid
to workspace_tree_oid (tree equivalence proof). Fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from runtime.receipts import plan_core as _pc
from runtime.receipts.receipt_emitter import build_land_receipt
from runtime.receipts.store import ReceiptStore


@dataclass(frozen=True)
class PostMergeLandResult:
    """Result of the post-merge land gate."""

    emitted: bool
    land_receipt: dict[str, Any] | None
    error_code: str | None
    detail: str


def run_post_merge_land_gate(
    landed_sha: str,
    land_target: str,
    merge_method: str,
    acceptance_receipt_id: str,
    store_root: Path | str,
    agent_id: str,
    run_id: str,
    repo_root: Path | str | None = None,
    landing_evidence: dict | None = None,
) -> PostMergeLandResult:
    """
    Emit a land receipt post-merge (spec §10.2).

    Steps:
    1. Look up acceptance receipt (must exist)
    2. Resolve landed_tree_oid from git
    3. Build land receipt (tree_equivalence computed; match may be false)
    4. Write to store
    5. Return result

    Fail-closed: any exception → emitted=False with error_code=GATE_ERROR.
    Note: tree mismatch does NOT block emission — it records the violation.
    Reconciliation (not this function) flags match=false receipts.
    """
    try:
        store = ReceiptStore(store_root)
    except Exception as exc:
        return PostMergeLandResult(
            emitted=False,
            land_receipt=None,
            error_code="GATE_ERROR",
            detail=f"Failed to open store: {exc}",
        )

    # Step 1: Look up acceptance receipt
    try:
        acceptance = store.query_acceptance_by_id(acceptance_receipt_id)
    except Exception as exc:
        return PostMergeLandResult(
            emitted=False,
            land_receipt=None,
            error_code="GATE_ERROR",
            detail=f"Store query error: {exc}",
        )
    if acceptance is None:
        return PostMergeLandResult(
            emitted=False,
            land_receipt=None,
            error_code="ACCEPTANCE_RECEIPT_NOT_FOUND",
            detail=f"Acceptance receipt {acceptance_receipt_id!r} not found in store",
        )
    decision_status = str((acceptance.get("decision") or {}).get("status", ""))
    if decision_status != "ACCEPTED":
        return PostMergeLandResult(
            emitted=False,
            land_receipt=None,
            error_code="ACCEPTANCE_NOT_ACCEPTED",
            detail=(
                f"Acceptance receipt {acceptance_receipt_id!r} has decision "
                f"status={decision_status!r}; expected 'ACCEPTED'"
            ),
        )

    workspace_sha = acceptance["workspace_sha"]
    workspace_tree_oid = acceptance["workspace_tree_oid"]
    plan_core_sha256 = acceptance["plan_core_sha256"]

    # Step 2: Resolve landed tree OID from git
    try:
        landed_tree_oid = _pc.resolve_tree_oid(landed_sha, repo_root=repo_root)
    except Exception as exc:
        return PostMergeLandResult(
            emitted=False,
            land_receipt=None,
            error_code="GATE_ERROR",
            detail=f"Failed to resolve tree OID for landed_sha={landed_sha!r}: {exc}",
        )

    # Step 3: Build land receipt (records match=True or False)
    try:
        receipt = build_land_receipt(
            landed_sha=landed_sha,
            landed_tree_oid=landed_tree_oid,
            land_target=land_target,
            merge_method=merge_method,
            acceptance_receipt_id=acceptance_receipt_id,
            workspace_sha=workspace_sha,
            workspace_tree_oid=workspace_tree_oid,
            plan_core_sha256=plan_core_sha256,
            agent_id=agent_id,
            run_id=run_id,
            landing_evidence=landing_evidence,
        )
    except Exception as exc:
        return PostMergeLandResult(
            emitted=False,
            land_receipt=None,
            error_code="GATE_ERROR",
            detail=f"Failed to build land receipt: {exc}",
        )

    # Step 4: Write to store
    try:
        store.write_land_receipt(receipt)
    except Exception as exc:
        return PostMergeLandResult(
            emitted=False,
            land_receipt=receipt,
            error_code="GATE_ERROR",
            detail=f"Failed to write land receipt: {exc}",
        )

    return PostMergeLandResult(
        emitted=True,
        land_receipt=receipt,
        error_code=None,
        detail=f"Land receipt {receipt['receipt_id']!r} emitted; tree_match={receipt['tree_equivalence']['match']}",  # noqa: E501
    )
