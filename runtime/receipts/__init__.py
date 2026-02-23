"""
LifeOS Receipts — Emit and Validate layer for the receipts-first build pipeline.
"""

from .ulid import generate_ulid
from .plan_core import (
    assert_no_floats,
    canonicalize_plan_core,
    compute_plan_core_sha256,
    resolve_tree_oid,
)
from .schemas import (
    ACCEPTANCE_RECEIPT_SCHEMA,
    BLOCKED_REPORT_SCHEMA,
    LAND_RECEIPT_SCHEMA,
    GATE_RESULT_SCHEMA,
    RUNLOG_EVENT_SCHEMA,
    REVIEW_SUMMARY_SCHEMA,
)
from .validator import (
    validate_artefact,
    assert_valid,
    ReceiptValidationError,
)
from .pre_merge import (
    PreMergeResult,
    run_pre_merge_check,
    RC_ACCEPTED,
    RC_NO_RECEIPT,
    RC_DECISION_NOT_ACCEPTED,
    RC_MISSING_POLICY_VERSION,
    RC_TREE_OID_MISMATCH,
    RC_STORE_ERROR,
)
from .receipt_emitter import build_land_receipt
from .post_merge import PostMergeLandResult, run_post_merge_land_gate
from .reconciliation import ReconciliationReport, run_reconciliation

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
