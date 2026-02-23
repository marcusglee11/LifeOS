"""
Deterministic state machine for council review execution.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Mapping

from runtime.agents.api import AgentCall, call_agent

from .compiler import compile_council_run_plan
from .models import (
    CouncilBlockedError,
    CouncilRunPlan,
    CouncilRuntimeResult,
    CouncilSeatResult,
    CouncilTransition,
)
from .policy import CouncilPolicy
from .schema_gate import validate_seat_output


SeatExecutor = Callable[[str, Mapping[str, Any], CouncilRunPlan, int], dict[str, Any] | str]
ClosureCallable = Callable[[Mapping[str, Any], CouncilRunPlan], tuple[bool, dict[str, Any]]]


STATE_S0_ASSEMBLE = "S0_ASSEMBLE"
STATE_S0_5_COCHAIR_VALIDATE = "S0_5_COCHAIR_VALIDATE"
STATE_S1_EXECUTE_SEATS = "S1_EXECUTE_SEATS"
STATE_S1_25_SCHEMA_GATE = "S1_25_SCHEMA_GATE"
STATE_S1_5_SEAT_COMPLETION = "S1_5_SEAT_COMPLETION"
STATE_S2_SYNTHESIS = "S2_SYNTHESIS"
STATE_S2_5_COCHAIR_CHALLENGE = "S2_5_COCHAIR_CHALLENGE"
STATE_S3_CLOSURE_GATE = "S3_CLOSURE_GATE"
STATE_S4_CLOSEOUT = "S4_CLOSEOUT"
STATE_TERMINAL_BLOCKED = "TERMINAL_BLOCKED"
STATE_TERMINAL_COMPLETE = "TERMINAL_COMPLETE"


def _default_seat_executor(
    seat: str,
    ccp: Mapping[str, Any],
    plan: CouncilRunPlan,
    retry_count: int,
) -> dict[str, Any] | str:
    """
    Default seat executor using the Agent API.
    """
    role = plan.seat_role_map.get(seat, "reviewer_architect")
    model = plan.model_assignments.get(seat, "auto")
    packet = {
        "ccp": ccp,
        "seat": seat,
        "plan": {
            "mode": plan.mode,
            "topology": plan.topology,
            "required_sections": list(ccp.get("sections", {}).keys())
            if isinstance(ccp.get("sections"), Mapping)
            else [],
        },
        "retry_count": retry_count,
    }
    response = call_agent(
        AgentCall(
            role=role,
            packet=packet,
            model=model,
        ),
        run_id=plan.run_id,
    )
    if response.packet is not None:
        return response.packet
    return response.content


def _default_closure_builder(
    synthesis: Mapping[str, Any], plan: CouncilRunPlan
) -> tuple[bool, dict[str, Any]]:
    """
    Default closure-build hook. Side-effect free unless caller injects a real hook.
    """
    return True, {"builder": "noop", "run_id": plan.run_id, "synthesis_verdict": synthesis.get("verdict")}


def _default_closure_validator(
    synthesis: Mapping[str, Any], plan: CouncilRunPlan
) -> tuple[bool, dict[str, Any]]:
    """
    Default closure-validate hook. Side-effect free unless caller injects a real hook.
    """
    return True, {"validator": "noop", "run_id": plan.run_id, "synthesis_verdict": synthesis.get("verdict")}


class CouncilFSM:
    """
    Protocol-aligned council review runtime.
    """

    def __init__(
        self,
        policy: CouncilPolicy,
        seat_executor: SeatExecutor | None = None,
        closure_builder: ClosureCallable | None = None,
        closure_validator: ClosureCallable | None = None,
    ):
        self.policy = policy
        self.seat_executor = seat_executor or _default_seat_executor
        self.closure_builder = closure_builder or _default_closure_builder
        self.closure_validator = closure_validator or _default_closure_validator

    @staticmethod
    def _transition(
        transitions: list[CouncilTransition],
        from_state: str,
        to_state: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        transitions.append(
            CouncilTransition(
                from_state=from_state,
                to_state=to_state,
                reason=reason,
                details=details or {},
            )
        )

    @staticmethod
    def _waived_seats(ccp: Mapping[str, Any]) -> set[str]:
        waivers = ccp.get("waived_seats", [])
        if not isinstance(waivers, list):
            return set()
        return {str(item) for item in waivers}

    @staticmethod
    def _cochair_validate_ccp(ccp: Mapping[str, Any], plan: CouncilRunPlan) -> tuple[bool, str]:
        required_sections = {"objective", "scope", "constraints", "artifacts"}
        sections = ccp.get("sections", {})
        if not isinstance(sections, Mapping):
            return False, "CCP sections block missing."
        missing = [section for section in sorted(required_sections) if section not in sections]
        if missing:
            return False, f"Missing required sections: {', '.join(missing)}"
        if not plan.cochair_required:
            return True, "cochair_not_required"
        return True, "cochair_validation_passed"

    @staticmethod
    def _extract_verdict(seat_outputs: Mapping[str, CouncilSeatResult]) -> str:
        verdicts = []
        for result in seat_outputs.values():
            payload = result.normalized_output or {}
            verdict = payload.get("verdict")
            if isinstance(verdict, str):
                verdicts.append(verdict)
        if not verdicts:
            return "Reject"
        if "Reject" in verdicts:
            return "Reject"
        if "Go with Fixes" in verdicts:
            return "Go with Fixes"
        return "Accept"

    @staticmethod
    def _aggregate_complexity(seat_outputs: Mapping[str, CouncilSeatResult]) -> dict[str, Any]:
        total_net_human_steps = 0
        total_new_surfaces = 0
        total_surfaces_removed = 0
        unmechanized_additions = 0

        for result in seat_outputs.values():
            budget = (result.normalized_output or {}).get("complexity_budget", {})
            if not isinstance(budget, Mapping):
                continue
            net_raw = budget.get("net_human_steps", 0)
            if isinstance(net_raw, str):
                cleaned = net_raw.strip()
                net = int(cleaned) if cleaned.lstrip("+-").isdigit() else 0
            elif isinstance(net_raw, int):
                net = net_raw
            else:
                net = 0
            total_net_human_steps += net

            total_new_surfaces += int(budget.get("new_surfaces_introduced", 0) or 0)
            total_surfaces_removed += int(budget.get("surfaces_removed", 0) or 0)
            mechanized = str(budget.get("mechanized", "")).strip().lower()
            if net > 0 and mechanized == "no":
                unmechanized_additions += 1

        return {
            "governance_creep_flag": bool(total_net_human_steps > 0 and unmechanized_additions > 0),
            "total_net_human_steps": total_net_human_steps,
            "total_new_surfaces": total_new_surfaces,
            "total_surfaces_removed": total_surfaces_removed,
            "unmechanized_additions": unmechanized_additions,
        }

    def _build_contradiction_ledger(
        self, seat_outputs: Mapping[str, CouncilSeatResult], required: bool
    ) -> list[dict[str, Any]]:
        if not required:
            return []
        by_verdict: dict[str, list[str]] = {}
        for seat, result in seat_outputs.items():
            verdict = str((result.normalized_output or {}).get("verdict", "unknown"))
            by_verdict.setdefault(verdict, []).append(seat)
        if len(by_verdict) <= 1:
            return []
        ledger = []
        for verdict, seats in sorted(by_verdict.items()):
            ledger.append(
                {
                    "resolution": "requires synthesis reconciliation",
                    "seats": sorted(seats),
                    "verdict": verdict,
                }
            )
        return ledger

    def _synthesize(
        self,
        seat_outputs: Mapping[str, CouncilSeatResult],
        plan: CouncilRunPlan,
        ccp: Mapping[str, Any],
    ) -> dict[str, Any]:
        chair_output = (seat_outputs.get("Chair") or seat_outputs.get("L1UnifiedReviewer"))
        chair_payload = chair_output.normalized_output if chair_output else {}
        if not isinstance(chair_payload, Mapping):
            chair_payload = {}

        contradiction_ledger = self._build_contradiction_ledger(
            seat_outputs=seat_outputs,
            required=plan.contradiction_ledger_required,
        )
        rollup = self._aggregate_complexity(seat_outputs)

        synthesis = {
            "ceo_decisions": list(chair_payload.get("ceo_decisions", []))
            if isinstance(chair_payload.get("ceo_decisions"), list)
            else [],
            "change_list": list(chair_payload.get("fixes", []))
            if isinstance(chair_payload.get("fixes"), list)
            else [],
            "contradiction_ledger": contradiction_ledger,
            "deletion_line": str(
                chair_payload.get(
                    "deletion_line",
                    "Nothing — no deletion requested by synthesized council output.",
                )
            ),
            "fix_plan": list(chair_payload.get("fixes", []))
            if isinstance(chair_payload.get("fixes"), list)
            else [],
            "mechanization_plan": list(chair_payload.get("mechanization_plan", []))
            if isinstance(chair_payload.get("mechanization_plan"), list)
            else [],
            "run_complexity_rollup": rollup,
            "verdict": self._extract_verdict(seat_outputs),
        }

        if bool(plan.compliance_flags.get("bootstrap_used", False)):
            synthesis["fix_plan"].append(
                {
                    "owner": "operations",
                    "priority": "P0",
                    "text": "Restore canonical artifacts and re-run council validation.",
                }
            )
        return synthesis

    @staticmethod
    def _challenge_synthesis(
        synthesis: Mapping[str, Any],
        seat_outputs: Mapping[str, CouncilSeatResult],
        plan: CouncilRunPlan,
    ) -> tuple[bool, str]:
        if not plan.cochair_required:
            return True, "cochair_not_required"

        cochair = seat_outputs.get("CoChair")
        if cochair is None or cochair.normalized_output is None:
            return False, "CoChair output missing."

        if plan.contradiction_ledger_required:
            ledger = synthesis.get("contradiction_ledger")
            if not isinstance(ledger, list):
                return False, "Contradiction Ledger missing from synthesis."
            if plan.topology == "MONO":
                verified = bool(cochair.normalized_output.get("contradiction_ledger_verified", False))
                if not verified:
                    return False, "CoChair did not verify contradiction ledger completeness."
        return True, "cochair_challenge_passed"

    def run(self, ccp: Mapping[str, Any]) -> CouncilRuntimeResult:
        """
        Execute the council protocol runtime for one CCP payload.
        """
        transitions: list[CouncilTransition] = []
        state = STATE_S0_ASSEMBLE
        seat_results: dict[str, CouncilSeatResult] = {}
        synthesis: dict[str, Any] = {}
        closure_events: list[dict[str, Any]] = []
        compliance = {}

        try:
            plan = compile_council_run_plan(ccp=ccp, policy=self.policy)
            compliance = dict(plan.compliance_flags)
            self._transition(
                transitions,
                STATE_S0_ASSEMBLE,
                STATE_S0_5_COCHAIR_VALIDATE if plan.cochair_required else STATE_S1_EXECUTE_SEATS,
                "plan_compiled",
                {"mode": plan.mode, "topology": plan.topology},
            )
            state = STATE_S0_5_COCHAIR_VALIDATE if plan.cochair_required else STATE_S1_EXECUTE_SEATS
        except CouncilBlockedError as err:
            self._transition(
                transitions,
                STATE_S0_ASSEMBLE,
                STATE_TERMINAL_BLOCKED,
                "plan_blocked",
                {"category": err.category, "detail": err.detail},
            )
            block_report = {"category": err.category, "detail": err.detail}
            return CouncilRuntimeResult(
                status="blocked",
                run_log={
                    "status": "blocked",
                    "state_transitions": [event.to_dict() for event in transitions],
                },
                decision_payload={"status": "BLOCKED", "reason": err.category, "detail": err.detail},
                block_report=block_report,
            )

        if state == STATE_S0_5_COCHAIR_VALIDATE:
            ok, reason = self._cochair_validate_ccp(ccp, plan)
            if not ok:
                self._transition(
                    transitions,
                    STATE_S0_5_COCHAIR_VALIDATE,
                    STATE_TERMINAL_BLOCKED,
                    "cochair_validation_failed",
                    {"detail": reason},
                )
                return CouncilRuntimeResult(
                    status="blocked",
                    run_log={
                        "execution": plan.to_dict(),
                        "status": "blocked",
                        "state_transitions": [event.to_dict() for event in transitions],
                    },
                    decision_payload={"status": "BLOCKED", "reason": "ccp_validation_failed", "detail": reason},
                    block_report={"category": "ccp_validation_failed", "detail": reason},
                )
            self._transition(
                transitions,
                STATE_S0_5_COCHAIR_VALIDATE,
                STATE_S1_EXECUTE_SEATS,
                reason,
            )
            state = STATE_S1_EXECUTE_SEATS

        waived = self._waived_seats(ccp)
        if state == STATE_S1_EXECUTE_SEATS:
            for seat in plan.required_seats:
                retries_used = 0
                errors: list[str] = []
                warnings: list[str] = []
                normalized_output = None
                raw_output: dict[str, Any] | str = {}
                status = "failed"
                while retries_used <= self.policy.schema_gate_retry_cap:
                    raw_output = self.seat_executor(seat, ccp, plan, retries_used)
                    gate_result = validate_seat_output(raw_output=raw_output, policy=self.policy)
                    self._transition(
                        transitions,
                        STATE_S1_EXECUTE_SEATS,
                        STATE_S1_25_SCHEMA_GATE,
                        "seat_output_received",
                        {"retries": retries_used, "seat": seat},
                    )
                    errors = list(gate_result.errors)
                    warnings = list(gate_result.warnings)
                    if gate_result.valid:
                        status = "complete"
                        normalized_output = gate_result.normalized_output
                        break
                    if retries_used >= self.policy.schema_gate_retry_cap:
                        status = "failed"
                        normalized_output = gate_result.normalized_output
                        break
                    retries_used += 1
                waived_seat = seat in waived
                if status != "complete" and waived_seat:
                    status = "waived"
                seat_results[seat] = CouncilSeatResult(
                    seat=seat,
                    status=status,
                    model=plan.model_assignments.get(seat, "unknown"),
                    raw_output=raw_output,
                    normalized_output=normalized_output,
                    retries_used=retries_used,
                    errors=errors,
                    warnings=warnings,
                    waived=waived_seat,
                )
            self._transition(
                transitions,
                STATE_S1_25_SCHEMA_GATE,
                STATE_S1_5_SEAT_COMPLETION,
                "all_seats_processed",
                {
                    "seats_failed": sum(1 for item in seat_results.values() if item.status == "failed"),
                    "seats_total": len(seat_results),
                    "seats_waived": sum(1 for item in seat_results.values() if item.status == "waived"),
                },
            )
            state = STATE_S1_5_SEAT_COMPLETION

        if state == STATE_S1_5_SEAT_COMPLETION:
            blocking_gaps = [
                seat
                for seat in plan.required_seats
                if seat_results.get(seat) is None or seat_results[seat].status == "failed"
            ]
            if blocking_gaps:
                self._transition(
                    transitions,
                    STATE_S1_5_SEAT_COMPLETION,
                    STATE_TERMINAL_BLOCKED,
                    "required_seats_missing",
                    {"missing_or_failed_seats": blocking_gaps},
                )
                return CouncilRuntimeResult(
                    status="blocked",
                    run_log={
                        "execution": plan.to_dict(),
                        "seat_outputs": {seat: result.to_dict() for seat, result in seat_results.items()},
                        "status": "blocked",
                        "state_transitions": [event.to_dict() for event in transitions],
                    },
                    decision_payload={
                        "status": "BLOCKED",
                        "reason": "required_seats_missing",
                        "seats": blocking_gaps,
                    },
                    block_report={
                        "category": "required_seats_missing",
                        "detail": f"Blocking seat gaps: {', '.join(blocking_gaps)}",
                    },
                )
            self._transition(
                transitions,
                STATE_S1_5_SEAT_COMPLETION,
                STATE_S2_SYNTHESIS,
                "seat_completion_ok",
            )
            state = STATE_S2_SYNTHESIS

        if state == STATE_S2_SYNTHESIS:
            synthesis = self._synthesize(seat_outputs=seat_results, plan=plan, ccp=ccp)
            self._transition(
                transitions,
                STATE_S2_SYNTHESIS,
                STATE_S2_5_COCHAIR_CHALLENGE,
                "synthesis_complete",
                {"verdict": synthesis.get("verdict")},
            )
            state = STATE_S2_5_COCHAIR_CHALLENGE

        if state == STATE_S2_5_COCHAIR_CHALLENGE:
            passed, reason = self._challenge_synthesis(
                synthesis=synthesis, seat_outputs=seat_results, plan=plan
            )
            if not passed:
                # One synthesis rework cycle only.
                synthesis = self._synthesize(seat_outputs=seat_results, plan=plan, ccp=ccp)
                passed_after_rework, reason_after_rework = self._challenge_synthesis(
                    synthesis=synthesis, seat_outputs=seat_results, plan=plan
                )
                if not passed_after_rework:
                    self._transition(
                        transitions,
                        STATE_S2_5_COCHAIR_CHALLENGE,
                        STATE_TERMINAL_BLOCKED,
                        "cochair_challenge_failed",
                        {"detail": reason_after_rework},
                    )
                    return CouncilRuntimeResult(
                        status="blocked",
                        run_log={
                            "execution": plan.to_dict(),
                            "seat_outputs": {seat: result.to_dict() for seat, result in seat_results.items()},
                            "status": "blocked",
                            "state_transitions": [event.to_dict() for event in transitions],
                            "synthesis": synthesis,
                        },
                        decision_payload={
                            "status": "BLOCKED",
                            "reason": "cochair_challenge_failed",
                            "detail": reason_after_rework,
                        },
                        block_report={
                            "category": "cochair_challenge_failed",
                            "detail": reason_after_rework,
                        },
                    )
                reason = reason_after_rework
            next_state = (
                STATE_S3_CLOSURE_GATE
                if plan.closure_gate_required and synthesis.get("verdict") in {"Accept", "Go with Fixes"}
                else STATE_S4_CLOSEOUT
            )
            self._transition(
                transitions,
                STATE_S2_5_COCHAIR_CHALLENGE,
                next_state,
                "cochair_challenge_passed",
                {"detail": reason},
            )
            state = next_state

        if state == STATE_S3_CLOSURE_GATE:
            cycles = 0
            closure_ok = False
            while cycles <= self.policy.closure_retry_cap:
                build_ok, build_details = self.closure_builder(synthesis, plan)
                validate_ok, validate_details = self.closure_validator(synthesis, plan)
                closure_events.append(
                    {
                        "build_details": build_details,
                        "build_ok": build_ok,
                        "cycle": cycles,
                        "validate_details": validate_details,
                        "validate_ok": validate_ok,
                    }
                )
                if build_ok and validate_ok:
                    closure_ok = True
                    break
                cycles += 1
            if not closure_ok:
                waivers = compliance.get("waivers", [])
                if not isinstance(waivers, list):
                    waivers = []
                waivers.append("closure_gate_residual_issues")
                compliance["waivers"] = waivers
            self._transition(
                transitions,
                STATE_S3_CLOSURE_GATE,
                STATE_S4_CLOSEOUT,
                "closure_gate_complete",
                {"closure_ok": closure_ok, "cycles": len(closure_events)},
            )
            state = STATE_S4_CLOSEOUT

        if state == STATE_S4_CLOSEOUT:
            self._transition(
                transitions,
                STATE_S4_CLOSEOUT,
                STATE_TERMINAL_COMPLETE,
                "run_complete",
            )

        seat_outputs_dict = {
            seat: seat_results[seat].to_dict()
            for seat in plan.required_seats
            if seat in seat_results
        }
        transition_dicts = [event.to_dict() for event in transitions]
        model_counter = Counter(plan.model_assignments.values())
        model_plan = {
            "by_model": dict(sorted(model_counter.items())),
            "seat_assignments": [
                {"model": plan.model_assignments.get(seat, "unknown"), "seat": seat}
                for seat in plan.required_seats
            ],
        }

        run_log = {
            "aur_id": plan.aur_id,
            "compliance": {
                "bootstrap_used": bool(compliance.get("bootstrap_used", False)),
                "ceo_override": bool(compliance.get("ceo_override", False)),
                "independence_required": plan.independence_required,
                "independence_satisfied": plan.independence_satisfied,
                "waivers": list(compliance.get("waivers", []))
                if isinstance(compliance.get("waivers"), list)
                else [],
            },
            "execution": {
                "mode": plan.mode,
                "model_plan": model_plan,
                "protocol_version": self.policy.protocol_version,
                "run_id": plan.run_id,
                "timestamp": plan.timestamp,
                "topology": plan.topology,
            },
            "seat_outputs": seat_outputs_dict,
            "state_transitions": transition_dicts,
            "status": "complete",
            "synthesis": synthesis,
        }
        if closure_events:
            run_log["closure_gate"] = closure_events

        decision_payload = {
            "compliance": run_log["compliance"],
            "status": "COMPLETE",
            "verdict": synthesis.get("verdict", "Reject"),
            "fix_plan": synthesis.get("fix_plan", []),
            "ceo_decisions": synthesis.get("ceo_decisions", []),
            "deletion_line": synthesis.get("deletion_line", ""),
            "run_id": plan.run_id,
        }
        return CouncilRuntimeResult(
            status="complete",
            run_log=run_log,
            decision_payload=decision_payload,
            block_report=None,
        )
