"""
Live end-to-end dogfood tests for the council runtime.

These tests make real LLM API calls through the Zen endpoint.
Skipped automatically when ZEN_REVIEWER_KEY is not set.
"""

from __future__ import annotations

import os
import time

import pytest

from runtime.orchestration.council.fsm import CouncilFSM
from runtime.orchestration.council.policy import load_council_policy

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_LIVE_COUNCIL") == "1"
    or not os.environ.get("ZEN_REVIEWER_KEY"),
    reason="Live council tests require ZEN_REVIEWER_KEY",
)


def _coo_dispatcher_ccp_m2() -> dict:
    """M2_FULL CCP for COO Work Dispatcher with stable live seat_overrides."""
    return {
        "header": {
            "aur_id": "AUR-COO-DISPATCH-LIVE-1",
            "aur_type": "code",
            "change_class": "new",
            "blast_radius": "module",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["interfaces"],
            "safety_critical": False,
            "override": {
                "mode": "M2_FULL",
            },
            "model_plan_v1": {
                "seat_overrides": {
                    "Chair": "claude-sonnet-4-5",
                    "Architect": "claude-sonnet-4-5",
                    "StructuralOperational": "claude-sonnet-4-5",
                    "Testing": "claude-sonnet-4-5",
                    "Simplicity": "claude-sonnet-4-5",
                    "CoChair": "claude-sonnet-4-5",
                    "Alignment": "claude-sonnet-4-5",
                    "Technical": "claude-sonnet-4-5",
                    "RiskAdversarial": "claude-sonnet-4-5",
                    "Determinism": "claude-sonnet-4-5",
                    "Governance": "claude-sonnet-4-5",
                },
            },
        },
        "sections": {
            "objective": (
                "Review COO Work Dispatcher — orchestration engine routing task "
                "assignments from the COO to downstream agents. The dispatcher reads "
                "from a priority queue, resolves agent availability, and emits structured "
                "dispatch events with retry semantics."
            ),
            "scope": {
                "surface": "runtime/orchestration",
                "files": [
                    "runtime/orchestration/dispatcher.py",
                    "runtime/orchestration/dispatch_queue.py",
                ],
            },
            "constraints": [
                "Must not modify governance paths",
                "Must preserve deterministic dispatch ordering",
                "Must emit structured logs for every dispatch event",
                "Retry budget capped at 3 attempts per task",
            ],
            "artifacts": [
                {"id": "runtime/orchestration/dispatcher.py", "type": "code"},
                {"id": "runtime/tests/orchestration/test_dispatcher.py", "type": "test"},
            ],
        },
    }


def _coo_dispatcher_ccp_m0_paid() -> dict:
    """M0_FAST CCP with single L1UnifiedReviewer seat for paid model test."""
    return {
        "header": {
            "aur_id": "AUR-COO-DISPATCH-PAID-1",
            "aur_type": "code",
            "change_class": "amend",
            "blast_radius": "local",
            "reversibility": "easy",
            "uncertainty": "low",
            "touches": ["tests"],
            "safety_critical": False,
            "model_plan_v1": {
                "seat_overrides": {
                    "L1UnifiedReviewer": "gemini-3.1-pro",
                },
            },
        },
        "sections": {
            "objective": "Review minor dispatcher test addition.",
            "scope": {"surface": "runtime/tests"},
            "constraints": ["No production code changes"],
            "artifacts": [{"id": "runtime/tests/orchestration/test_dispatcher.py"}],
        },
    }


def _format_seat_report(seat_outputs: dict) -> str:
    """Format per-seat results into a readable report."""
    lines = []
    lines.append(f"{'Seat':<25} {'Model':<30} {'Status':<10} {'Retries':<8} {'Verdict':<18} {'Errors'}")
    lines.append("-" * 120)
    for seat, data in sorted(seat_outputs.items()):
        model = data.get("model", "unknown")
        status = data.get("status", "unknown")
        retries = data.get("retries_used", 0)
        norm = data.get("normalized_output") or {}
        verdict = norm.get("verdict", "N/A")
        errors = "; ".join(data.get("errors", [])) or "none"
        lines.append(f"{seat:<25} {model:<30} {status:<10} {retries:<8} {verdict:<18} {errors}")
    return "\n".join(lines)


def _format_model_comparison(seat_outputs: dict) -> str:
    """Compare pass rates by model family."""
    by_model: dict[str, dict[str, int]] = {}
    for data in seat_outputs.values():
        model = data.get("model", "unknown")
        family = model.split("/")[-1].rsplit("-", 1)[0] if "/" in model else model
        if family not in by_model:
            by_model[family] = {"total": 0, "passed": 0, "failed": 0}
        by_model[family]["total"] += 1
        if data.get("status") == "complete":
            by_model[family]["passed"] += 1
        else:
            by_model[family]["failed"] += 1

    lines = []
    lines.append(f"{'Model Family':<30} {'Total':<8} {'Passed':<8} {'Failed':<8} {'Rate'}")
    lines.append("-" * 70)
    for family, counts in sorted(by_model.items()):
        rate = f"{counts['passed'] / counts['total'] * 100:.0f}%" if counts["total"] else "N/A"
        lines.append(f"{family:<30} {counts['total']:<8} {counts['passed']:<8} {counts['failed']:<8} {rate}")
    return "\n".join(lines)


def test_live_m2_full_coo_dispatcher():
    """Live M2_FULL council run with 11 seats on a stable live model."""
    policy = load_council_policy()
    ccp = _coo_dispatcher_ccp_m2()

    # No seat_executor injected — uses _default_seat_executor with real LLM calls.
    fsm = CouncilFSM(policy=policy)

    start = time.monotonic()
    result = fsm.run(ccp)
    elapsed = time.monotonic() - start

    # -- Structured report --
    print("\n" + "=" * 80)
    print("COUNCIL DOGFOOD LIVE REPORT — COO Work Dispatcher (M2_FULL)")
    print("=" * 80)
    print(f"\nOverall Status: {result.status}")
    print(f"Elapsed: {elapsed:.1f}s")

    if result.status == "complete":
        print(f"Verdict: {result.decision_payload.get('verdict')}")
        print(f"Mode: {result.run_log['execution']['mode']}")
        print(f"Topology: {result.run_log['execution']['topology']}")

    print("\n--- Per-Seat Results ---")
    seat_outputs = result.run_log.get("seat_outputs", {})
    print(_format_seat_report(seat_outputs))

    if result.status == "complete":
        syn = result.run_log.get("synthesis", {})
        print("\n--- Synthesis ---")
        print(f"  Verdict: {syn.get('verdict')}")
        print(f"  Contradiction Ledger: {syn.get('contradiction_ledger', [])}")
        print(f"  Fix Plan: {syn.get('fix_plan', [])}")
        print(f"  Complexity Rollup: {syn.get('run_complexity_rollup', {})}")

    print("\n--- Model Comparison ---")
    print(_format_model_comparison(seat_outputs))
    print("=" * 80)

    # -- Assertions --
    assert result.status in ("complete", "blocked"), f"Unexpected status: {result.status}"

    if result.status == "complete":
        assert result.decision_payload["status"] == "COMPLETE"
        assert result.decision_payload["verdict"] in ("Accept", "Go with Fixes", "Reject")
        assert result.run_log["execution"]["mode"] == "M2_FULL"
        # At least some seats should have produced output.
        completed_seats = [
            s for s, d in seat_outputs.items() if d.get("status") == "complete"
        ]
        assert len(completed_seats) >= 2, f"Only {len(completed_seats)} seats completed"


def test_live_paid_fallback_single_seat():
    """Live M0_FAST with single L1UnifiedReviewer on gemini-3.1-pro (paid model)."""
    policy = load_council_policy()
    ccp = _coo_dispatcher_ccp_m0_paid()

    fsm = CouncilFSM(policy=policy)

    start = time.monotonic()
    result = fsm.run(ccp)
    elapsed = time.monotonic() - start

    print("\n" + "=" * 80)
    print("COUNCIL DOGFOOD LIVE REPORT — Paid Fallback (M0_FAST, gemini-3.1-pro)")
    print("=" * 80)
    print(f"Status: {result.status}")
    print(f"Elapsed: {elapsed:.1f}s")

    seat_outputs = result.run_log.get("seat_outputs", {})
    if seat_outputs:
        print("\n--- Per-Seat Results ---")
        print(_format_seat_report(seat_outputs))
    print("=" * 80)

    assert result.status in ("complete", "blocked"), f"Unexpected status: {result.status}"

    if result.status == "complete":
        assert result.decision_payload["status"] == "COMPLETE"
        assert result.run_log["execution"]["mode"] == "M0_FAST"
