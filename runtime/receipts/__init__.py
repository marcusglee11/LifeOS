"""
LifeOS Receipts — Emit and Validate layer for the receipts-first build pipeline.
"""

from .plan_core import (
    assert_no_floats,
    canonicalize_plan_core,
    compute_plan_core_sha256,
    resolve_tree_oid,
)
from .post_merge import PostMergeLandResult, run_post_merge_land_gate
from .pre_merge import (
    RC_ACCEPTED,
    RC_DECISION_NOT_ACCEPTED,
    RC_MISSING_POLICY_VERSION,
    RC_NO_RECEIPT,
    RC_STORE_ERROR,
    RC_TREE_OID_MISMATCH,
    PreMergeResult,
    run_pre_merge_check,
)
from .receipt_emitter import build_land_receipt
from .reconciliation import ReconciliationReport, run_reconciliation
from .schemas import (
    ACCEPTANCE_RECEIPT_SCHEMA,
    BLOCKED_REPORT_SCHEMA,
    GATE_RESULT_SCHEMA,
    LAND_RECEIPT_SCHEMA,
    REVIEW_SUMMARY_SCHEMA,
    RUNLOG_EVENT_SCHEMA,
)
from .ulid import generate_ulid
from .validator import (
    ReceiptValidationError,
    assert_valid,
    validate_artefact,
)

__all__ = [
    "generate_ulid",
    "assert_no_floats",
    "canonicalize_plan_core",
    "compute_plan_core_sha256",
    "resolve_tree_oid",
    "ACCEPTANCE_RECEIPT_SCHEMA",
    "BLOCKED_REPORT_SCHEMA",
    "LAND_RECEIPT_SCHEMA",
    "GATE_RESULT_SCHEMA",
    "RUNLOG_EVENT_SCHEMA",
    "REVIEW_SUMMARY_SCHEMA",
    "validate_artefact",
    "assert_valid",
    "ReceiptValidationError",
    "PreMergeResult",
    "run_pre_merge_check",
    "RC_ACCEPTED",
    "RC_NO_RECEIPT",
    "RC_DECISION_NOT_ACCEPTED",
    "RC_MISSING_POLICY_VERSION",
    "RC_TREE_OID_MISMATCH",
    "RC_STORE_ERROR",
    "build_land_receipt",
    "PostMergeLandResult",
    "run_post_merge_land_gate",
    "ReconciliationReport",
    "run_reconciliation",
]
