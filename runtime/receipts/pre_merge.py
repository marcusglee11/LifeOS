"""
Phase B pre-merge enforcement check (§10.1).

Verifies a valid ACCEPTED acceptance receipt exists before merge.
Fail-closed: any unexpected exception → BLOCKED.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# ── Reason codes ──────────────────────────────────────────────────────────
RC_ACCEPTED = "ACCEPTED"
RC_NO_RECEIPT = "NO_RECEIPT"
RC_DECISION_NOT_ACCEPTED = "DECISION_NOT_ACCEPTED"
RC_MISSING_POLICY_VERSION = "MISSING_POLICY_VERSION"
RC_TREE_OID_MISMATCH = "TREE_OID_MISMATCH"
RC_STORE_ERROR = "STORE_ERROR"


@dataclass(frozen=True)
class PreMergeResult:
    """Result of the pre-merge enforcement check."""

    allowed: bool
    reason_code: str
    receipt: dict[str, Any] | None
    detail: str


from runtime.receipts import plan_core as _pc
from runtime.receipts.store import ReceiptStore


def run_pre_merge_check(
    workspace_sha: str,
    plan_core_sha256: str,
    store_root: Path | str,
    repo_root: Path | str | None = None,
) -> PreMergeResult:
    """
    Phase B pre-merge enforcement check (spec §10.1).

    Checks in order:
    1. Store root exists and is accessible
    2. Active receipt exists for (workspace_sha, plan_core_sha256)
    3. decision.status == ACCEPTED
    4. policy_pack.policy_version present (Phase B, §5.3)
    5. workspace_tree_oid recomputed from git matches receipt (§10.1 step 4)

    Fail-closed: any exception → BLOCKED with RC_STORE_ERROR.
    """
    store_root = Path(store_root)

    # Pre-check: store root must already exist (we don't create it on demand)
    if not store_root.exists():
        return PreMergeResult(
            allowed=False,
            reason_code=RC_STORE_ERROR,
            receipt=None,
            detail=f"Store root does not exist: {store_root!r}",
        )

    try:
        store = ReceiptStore(store_root)
    except Exception as exc:
        return PreMergeResult(
            allowed=False,
            reason_code=RC_STORE_ERROR,
            receipt=None,
            detail=f"Failed to open store at {store_root!r}: {exc}",
        )

    try:
        receipt = store.query_active_acceptance(workspace_sha, plan_core_sha256)
    except Exception as exc:
        return PreMergeResult(
            allowed=False,
            reason_code=RC_STORE_ERROR,
            receipt=None,
            detail=f"Store query error: {exc}",
        )

    # 1. Receipt must exist
    if receipt is None:
        return PreMergeResult(
            allowed=False,
            reason_code=RC_NO_RECEIPT,
            receipt=None,
            detail=f"No acceptance receipt for workspace_sha={workspace_sha!r}, plan_core_sha256={plan_core_sha256!r}",
        )

    # 2. Decision must be ACCEPTED
    decision_status = receipt.get("decision", {}).get("status")
    if decision_status != "ACCEPTED":
        return PreMergeResult(
            allowed=False,
            reason_code=RC_DECISION_NOT_ACCEPTED,
            receipt=receipt,
            detail=f"Receipt decision is {decision_status!r}, expected ACCEPTED",
        )

    # 3. policy_version must be present (Phase B enforcement, §5.3)
    policy_version = receipt.get("policy_pack", {}).get("policy_version")
    if not policy_version:
        return PreMergeResult(
            allowed=False,
            reason_code=RC_MISSING_POLICY_VERSION,
            receipt=receipt,
            detail="Receipt policy_pack missing policy_version (Phase B requires policy_version, §5.3)",
        )

    # 4. Tree OID anti-fabrication check (§10.1 step 4)
    try:
        actual_tree_oid = _pc.resolve_tree_oid(workspace_sha, repo_root=repo_root)
    except Exception as exc:
        return PreMergeResult(
            allowed=False,
            reason_code=RC_STORE_ERROR,
            receipt=receipt,
            detail=f"Failed to resolve tree OID for {workspace_sha!r}: {exc}",
        )

    receipt_tree_oid = receipt.get("workspace_tree_oid")
    if actual_tree_oid != receipt_tree_oid:
        return PreMergeResult(
            allowed=False,
            reason_code=RC_TREE_OID_MISMATCH,
            receipt=receipt,
            detail=(
                f"Tree OID mismatch: git resolves {workspace_sha!r} → {actual_tree_oid!r}, "
                f"receipt carries {receipt_tree_oid!r}"
            ),
        )

    policy_id = receipt.get("policy_pack", {}).get("policy_id", "unknown")
    return PreMergeResult(
        allowed=True,
        reason_code=RC_ACCEPTED,
        receipt=receipt,
        detail=f"Receipt {receipt.get('receipt_id')!r} accepted under policy {policy_id!r} v{policy_version}",
    )
