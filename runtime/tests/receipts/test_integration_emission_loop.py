"""
Integration tests: Full emission loop for LifeOS receipts (Phase A).

Tests the complete pipeline:
PlanCore → tree OID → RunLog → GateChecks → ReviewSummary → AcceptanceReceipt → Store → Query

Exit criteria coverage:
- EC1: Consecutive valid artefacts (test_five_consecutive_runs_all_valid)
- EC2: Determinism check (test_determinism_check)
- EC3: Store query correctness (test_store_query_round_trip, test_supersession_chain_resolution)
- EC4: Reconciliation smoke test (test_reconciliation_smoke_no_land_receipts)
- EC5: Tree OID binding (test_tree_oid_binding)
"""

from __future__ import annotations

from runtime.receipts.gate_check import (
    build_gate_results,
    compute_gate_rollup,
    make_artefact_ref,
)
from runtime.receipts.plan_core import compute_plan_core_sha256
from runtime.receipts.receipt_emitter import (
    build_acceptance_receipt,
    build_blocked_report,
    build_review_summary,
    compute_decision,
)
from runtime.receipts.runlog import RunLogEmitter
from runtime.receipts.store import ReceiptStore
from runtime.receipts.validator import validate_artefact

# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

SAMPLE_PLAN_CORE = {
    "plan_id": "integration-test-plan-001",
    "schema_version": "1.0",
    "phase_order": ["init", "build", "review"],
    "phases": {
        "init": {"steps": [{"step_id": "s-init", "name": "Initialize"}]},
        "build": {"steps": [{"step_id": "s-build", "name": "Build"}]},
        "review": {"steps": [{"step_id": "s-review", "name": "Review"}]},
    },
}

WORKSPACE_SHA = "cafebabe00cafebabe00cafebabe00cafebabe00"
WORKSPACE_TREE_OID = "deadbeef01deadbeef01deadbeef01deadbeef01"


def run_emission_loop(
    store: ReceiptStore,
    pass_gates: bool = True,
    supersedes: str | None = None,
    workspace_tree_oid: str = WORKSPACE_TREE_OID,
) -> dict:
    """
    Execute a complete emission loop and return the primary receipt.

    Returns dict with keys: receipt, report, review_summary, plan_core_sha256
    """
    plan_core_sha256 = compute_plan_core_sha256(SAMPLE_PLAN_CORE)

    # RunLog emission
    emitter = RunLogEmitter(phase_order=SAMPLE_PLAN_CORE["phase_order"])
    emitter.emit("init", "s-init", "start")
    emitter.emit("init", "s-init", "complete", data={"result": "ok"})
    emitter.emit("build", "s-build", "start")
    emitter.emit("build", "s-build", "complete")
    emitter.emit("review", "s-review", "start")
    emitter.emit("review", "s-review", "complete")

    # Gate checks
    if pass_gates:
        gates = [
            {"gate_id": "gate-lint", "status": "PASS", "blocking": True},
            {"gate_id": "gate-tests", "status": "PASS", "blocking": True},
            {"gate_id": "gate-coverage", "status": "WARN", "blocking": False},
        ]
    else:
        gates = [
            {"gate_id": "gate-lint", "status": "PASS", "blocking": True},
            {"gate_id": "gate-tests", "status": "FAIL", "blocking": True},
        ]

    gate_results = build_gate_results(gates)
    gate_rollup = compute_gate_rollup(list(gate_results.values()))

    # Evidence manifest
    evidence_manifest = [
        make_artefact_ref(
            "store", f"artefacts/{WORKSPACE_SHA}/{plan_core_sha256}/gate_results.json"
        ),
    ]

    # Review summary
    review_summary = build_review_summary(
        gate_rollup,
        evidence_manifest=evidence_manifest,
        runlog_stats={"event_count": len(emitter.events())},
    )

    # Decision
    decision = compute_decision(gate_rollup)

    if decision["status"] in ("REJECTED", "BLOCKED"):
        # Blocked path
        report = build_blocked_report(
            WORKSPACE_SHA,
            plan_core_sha256,
            reason_code=decision.get("reason_code", "GATE_FAIL"),
            gate_rollup=gate_rollup,
        )
        store.write_blocked_report(report)
        return {
            "receipt": None,
            "report": report,
            "review_summary": review_summary,
            "plan_core_sha256": plan_core_sha256,
            "gate_rollup": gate_rollup,
        }
    else:
        # Acceptance path
        receipt = build_acceptance_receipt(
            WORKSPACE_SHA,
            workspace_tree_oid,
            plan_core_sha256,
            emitter,
            decision,
            gate_rollup,
            refs=evidence_manifest,
            supersedes=supersedes,
        )
        store.write_acceptance_receipt(receipt)
        return {
            "receipt": receipt,
            "report": None,
            "review_summary": review_summary,
            "plan_core_sha256": plan_core_sha256,
            "gate_rollup": gate_rollup,
        }


# ─────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────


def test_full_emission_loop_acceptance_path(tmp_path):
    """Complete pipeline → valid v2.4 receipt in store."""
    store = ReceiptStore(tmp_path / "store")
    result = run_emission_loop(store, pass_gates=True)

    receipt = result["receipt"]
    assert receipt is not None
    assert receipt["schema_version"] == "2.4"
    assert receipt["decision"]["status"] == "ACCEPTED"

    # Schema validation
    errors = validate_artefact(receipt, "acceptance_receipt")
    assert errors == [], f"Receipt schema errors: {errors}"

    # Stored and queryable
    active = store.query_active_acceptance(WORKSPACE_SHA, result["plan_core_sha256"])
    assert active is not None
    assert active["receipt_id"] == receipt["receipt_id"]


def test_full_emission_loop_blocked_path(tmp_path):
    """Failing gate → blocked report in store."""
    store = ReceiptStore(tmp_path / "store")
    result = run_emission_loop(store, pass_gates=False)

    report = result["report"]
    assert report is not None
    assert report["schema_version"] == "2.4"
    assert "reason_code" in report

    errors = validate_artefact(report, "blocked_report")
    assert errors == [], f"Report schema errors: {errors}"

    # Appears in workspace query
    all_receipts = store.query_all_receipts_for_workspace(WORKSPACE_SHA)
    ids = {r.get("receipt_id") or r.get("report_id") for r in all_receipts}
    assert report["report_id"] in ids


def test_determinism_check(tmp_path):
    """Two runs from same PlanCore → identical deterministic content (timestamps/ULIDs/_ext excluded)."""  # noqa: E501
    # Run 1
    emitter1 = RunLogEmitter(phase_order=SAMPLE_PLAN_CORE["phase_order"])
    emitter1.emit("init", "s-init", "start")
    emitter1.emit("build", "s-build", "compile")
    emitter1.emit("review", "s-review", "check")

    # Run 2
    emitter2 = RunLogEmitter(phase_order=SAMPLE_PLAN_CORE["phase_order"])
    emitter2.emit("init", "s-init", "start")
    emitter2.emit("build", "s-build", "compile")
    emitter2.emit("review", "s-review", "check")

    # Deterministic content (no timestamps, no ULIDs)
    content1 = emitter1.deterministic_content()
    content2 = emitter2.deterministic_content()
    assert content1 == content2, f"Non-deterministic content:\n{content1}\nvs\n{content2}"

    # PlanCore hash is deterministic
    sha1 = compute_plan_core_sha256(SAMPLE_PLAN_CORE)
    sha2 = compute_plan_core_sha256(SAMPLE_PLAN_CORE)
    assert sha1 == sha2

    # Gate rollup is deterministic
    gates = [
        {"gate_id": "gate-lint", "status": "PASS", "blocking": True},
        {"gate_id": "gate-tests", "status": "PASS", "blocking": True},
    ]
    rollup1 = compute_gate_rollup(gates)
    rollup2 = compute_gate_rollup(gates)
    assert rollup1 == rollup2


def test_five_consecutive_runs_all_valid(tmp_path):
    """5 consecutive runs all produce schema-valid artefacts."""
    store = ReceiptStore(tmp_path / "store")
    for i in range(5):
        result = run_emission_loop(store, pass_gates=True)
        receipt = result["receipt"]
        assert receipt is not None, f"Run {i}: expected acceptance receipt"
        errors = validate_artefact(receipt, "acceptance_receipt")
        assert errors == [], f"Run {i}: schema errors: {errors}"

        review = result["review_summary"]
        errors = validate_artefact(review, "review_summary")
        assert errors == [], f"Run {i}: review summary errors: {errors}"


def test_store_query_round_trip(tmp_path):
    """Write → query → receipt matches."""
    store = ReceiptStore(tmp_path / "store")
    result = run_emission_loop(store, pass_gates=True)
    receipt = result["receipt"]
    assert receipt is not None

    # Query by workspace
    active = store.query_active_acceptance(WORKSPACE_SHA, result["plan_core_sha256"])
    assert active["receipt_id"] == receipt["receipt_id"]

    # Query by ID
    by_id = store.query_acceptance_by_id(receipt["receipt_id"])
    assert by_id["receipt_id"] == receipt["receipt_id"]


def test_supersession_chain_resolution(tmp_path):
    """A → B supersedes A → C supersedes B → query returns C."""
    store = ReceiptStore(tmp_path / "store")
    plan_core_sha256 = compute_plan_core_sha256(SAMPLE_PLAN_CORE)

    # Run A
    result_a = run_emission_loop(store, pass_gates=True)
    receipt_a = result_a["receipt"]

    # Run B supersedes A
    result_b = run_emission_loop(store, pass_gates=True, supersedes=receipt_a["receipt_id"])
    receipt_b = result_b["receipt"]
    assert receipt_b["supersedes"] == receipt_a["receipt_id"]

    # Run C supersedes B
    result_c = run_emission_loop(store, pass_gates=True, supersedes=receipt_b["receipt_id"])
    receipt_c = result_c["receipt"]
    assert receipt_c["supersedes"] == receipt_b["receipt_id"]

    # Active receipt should be C
    active = store.query_active_acceptance(WORKSPACE_SHA, plan_core_sha256)
    assert active is not None
    assert active["receipt_id"] == receipt_c["receipt_id"]


def test_reconciliation_smoke_no_land_receipts(tmp_path):
    """Phase A: store has no land receipts → reconciliation query returns empty."""
    store = ReceiptStore(tmp_path / "store")
    result = run_emission_loop(store, pass_gates=True)
    plan_core_sha256 = result["plan_core_sha256"]

    land_receipts = store.query_land_receipts_for_workspace(WORKSPACE_SHA, plan_core_sha256)
    assert land_receipts == [], f"Expected no land receipts in Phase A, got: {land_receipts}"


def test_tree_oid_binding(tmp_path):
    """Receipt workspace_tree_oid matches the PlanCore workspace."""
    store = ReceiptStore(tmp_path / "store")
    result = run_emission_loop(store, pass_gates=True, workspace_tree_oid=WORKSPACE_TREE_OID)
    receipt = result["receipt"]
    assert receipt is not None
    assert receipt["workspace_tree_oid"] == WORKSPACE_TREE_OID
