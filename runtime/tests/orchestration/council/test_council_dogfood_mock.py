"""
Mock end-to-end dogfood tests for the council runtime.

Validates the full pipeline with canned seat outputs against the
COO Work Dispatcher CCP — no LLM calls required.
"""

from __future__ import annotations

from runtime.orchestration.council.fsm import CouncilFSM
from runtime.orchestration.council.policy import load_council_policy


def _coo_dispatcher_ccp() -> dict:
    """M1_STANDARD CCP for COO Work Dispatcher review."""
    return {
        "header": {
            "aur_id": "AUR-COO-DISPATCH-1",
            "aur_type": "code",
            "change_class": "new",
            "blast_radius": "module",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["interfaces"],
            "safety_critical": False,
        },
        "sections": {
            "objective": "Review COO Work Dispatcher — orchestration engine routing task assignments from COO to agents.",
            "scope": {"surface": "runtime/orchestration"},
            "constraints": [
                "Must not modify governance paths",
                "Must preserve deterministic dispatch ordering",
            ],
            "artifacts": [
                {"id": "runtime/orchestration/dispatcher.py"},
                {"id": "runtime/tests/orchestration/test_dispatcher.py"},
            ],
        },
    }


def _canned_seat_output(seat: str, *, verdict: str = "Go with Fixes") -> dict:
    """Schema-gate-compliant canned output for a council seat."""
    output = {
        "verdict": verdict,
        "key_findings": [
            "Dispatcher routing table uses static map REF: git:abc123:runtime/orchestration/dispatcher.py#L10-L30",
            "No dynamic agent discovery — acceptable for v1 [ASSUMPTION]",
        ],
        "risks": [
            "Single point of failure if dispatcher process crashes",
            "No backpressure mechanism for overloaded agents",
        ],
        "fixes": [
            "Add health-check ping before routing to agent",
            "Emit structured log on dispatch failure for observability",
        ],
        "confidence": "medium",
        "assumptions": [
            "Agent availability is guaranteed by the orchestration layer",
            "Task payloads are validated upstream before reaching dispatcher",
        ],
        "complexity_budget": {
            "net_human_steps": 1,
            "new_surfaces_introduced": 2,
            "surfaces_removed": 0,
            "mechanized": "no",
            "trade_statement": "Health-check adds one manual verification step but prevents silent dispatch failures.",
        },
        "operator_view": (
            "COO Work Dispatcher routes tasks to agents via a static map. "
            "Two fixes recommended: health-check pings and structured failure logging. "
            "Low risk, module-scoped changes only."
        ),
    }
    if seat == "CoChair":
        output["contradiction_ledger_verified"] = True
    return output


def test_council_dogfood_mock_m1_coo_dispatcher():
    """Full M1 pipeline: 2 seats, schema gate passes, synthesis produces verdict, terminal complete."""
    policy = load_council_policy()

    def seat_executor(seat, ccp, plan, retry_count):
        return _canned_seat_output(seat)

    fsm = CouncilFSM(policy=policy, seat_executor=seat_executor)
    result = fsm.run(_coo_dispatcher_ccp())

    assert result.status == "complete"
    assert result.decision_payload["status"] == "COMPLETE"
    assert result.decision_payload["verdict"] == "Go with Fixes"
    assert result.run_log["execution"]["mode"] == "M1_STANDARD"

    # Both seats should be present and complete.
    seat_outputs = result.run_log["seat_outputs"]
    assert "Chair" in seat_outputs
    assert "CoChair" in seat_outputs
    assert seat_outputs["Chair"]["status"] == "complete"
    assert seat_outputs["CoChair"]["status"] == "complete"

    # Schema gate should have passed on first try (0 retries).
    assert seat_outputs["Chair"]["retries_used"] == 0
    assert seat_outputs["CoChair"]["retries_used"] == 0

    # Synthesis should contain fix plan from chair output.
    assert len(result.run_log["synthesis"]["fix_plan"]) > 0

    # CoChair challenge should have passed (contradiction ledger verified).
    states_visited = [t["to_state"] for t in result.run_log["state_transitions"]]
    assert "S2_5_COCHAIR_CHALLENGE" in states_visited
    assert "TERMINAL_COMPLETE" in states_visited
    assert "TERMINAL_BLOCKED" not in states_visited


def test_council_dogfood_mock_schema_gate_retry():
    """Chair returns incomplete output on first attempt, schema gate rejects, retry succeeds."""
    policy = load_council_policy()

    def seat_executor(seat, ccp, plan, retry_count):
        if seat == "Chair" and retry_count == 0:
            # Missing required sections — schema gate will reject.
            return {
                "verdict": "Go with Fixes",
                "key_findings": ["Incomplete review — first pass"],
            }
        return _canned_seat_output(seat)

    fsm = CouncilFSM(policy=policy, seat_executor=seat_executor)
    result = fsm.run(_coo_dispatcher_ccp())

    assert result.status == "complete"
    assert result.decision_payload["verdict"] == "Go with Fixes"

    # Chair should have used 1 retry.
    chair_out = result.run_log["seat_outputs"]["Chair"]
    assert chair_out["retries_used"] == 1
    assert chair_out["status"] == "complete"

    # CoChair should have passed on first try.
    cochair_out = result.run_log["seat_outputs"]["CoChair"]
    assert cochair_out["retries_used"] == 0


def test_council_dogfood_mock_mixed_verdicts():
    """Chair says Accept, CoChair says Go with Fixes. Synthesis resolves to Go with Fixes (conservative wins)."""
    policy = load_council_policy()

    def seat_executor(seat, ccp, plan, retry_count):
        if seat == "Chair":
            return _canned_seat_output(seat, verdict="Accept")
        return _canned_seat_output(seat, verdict="Go with Fixes")

    fsm = CouncilFSM(policy=policy, seat_executor=seat_executor)
    result = fsm.run(_coo_dispatcher_ccp())

    assert result.status == "complete"
    # Conservative verdict wins: Go with Fixes > Accept.
    assert result.decision_payload["verdict"] == "Go with Fixes"

    # Contradiction ledger should record the disagreement.
    ledger = result.run_log["synthesis"]["contradiction_ledger"]
    assert len(ledger) > 0
    # Verify both verdicts appear in the ledger.
    ledger_verdicts = {entry["verdict"] for entry in ledger}
    assert "Accept" in ledger_verdicts
    assert "Go with Fixes" in ledger_verdicts
