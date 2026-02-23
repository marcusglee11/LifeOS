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
    CouncilRunPlanCore,
    CouncilRunMeta,
    VERDICT_ACCEPT,
    VERDICT_REVISE,
    VERDICT_REJECT,
    DECISION_STATUS_NORMAL,
    DECISION_STATUS_DEGRADED_COVERAGE,
    DECISION_STATUS_DEGRADED_CHALLENGER,
    generate_run_id,
)
from .policy import CouncilPolicy, resolve_model_family
from .schema_gate import (
    validate_seat_output,
    validate_lens_output,
    validate_synthesis_output,
    validate_challenger_output,
)


SeatExecutor = Callable[[str, Mapping[str, Any], CouncilRunPlan, int], dict[str, Any] | str]
ClosureCallable = Callable[[Mapping[str, Any], CouncilRunPlan], tuple[bool, dict[str, Any]]]

# v2.2.1 type aliases
LensExecutor = Callable[[str, Mapping[str, Any], CouncilRunPlanCore, int], dict[str, Any] | str]
SynthesisExecutor = Callable[
    [Mapping[str, Any], CouncilRunPlanCore, Mapping[str, Any]], dict[str, Any] | str
]
ChallengerExecutor = Callable[
    [Mapping[str, Any], Mapping[str, Any], CouncilRunPlanCore], dict[str, Any] | str
]
PlanFactory = Callable[
    [Mapping[str, Any], CouncilPolicy], tuple[CouncilRunPlanCore, CouncilRunMeta]
]

# v1.3 states (preserved)
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

# v2.2.1 additional states
STATE_S1_EXECUTE_LENSES = "S1_EXECUTE_LENSES"
STATE_S1_25_SCHEMA_GATE_LENSES = "S1_25_SCHEMA_GATE_LENSES"
STATE_S1_5_COVERAGE_COMPLETE = "S1_5_COVERAGE_COMPLETE"
STATE_S1_55_EXECUTION_FIDELITY = "S1_55_EXECUTION_FIDELITY"
STATE_S2_25_SCHEMA_GATE_SYNTHESIS = "S2_25_SCHEMA_GATE_SYNTHESIS"
STATE_S2_5_CHALLENGER_REVIEW = "S2_5_CHALLENGER_REVIEW"


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
            return "Revise"
        if "Revise" in verdicts:
            return "Revise"
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
                if plan.closure_gate_required and synthesis.get("verdict") in {"Accept", "Go with Fixes", "Revise"}
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


# ---------------------------------------------------------------------------
# v2.2.1 FSM
# ---------------------------------------------------------------------------

_LENS_MAX_RETRIES = 2
_CHALLENGER_MAX_REWORK = 1
_CLOSURE_MAX_CYCLES = 2


def _noop_synthesis_executor(
    lens_results: Mapping[str, Any],
    plan: CouncilRunPlanCore,
    ccp: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "run_type": plan.run_type,
        "tier": plan.tier,
        "verdict": VERDICT_ACCEPT,
        "fix_plan": [],
        "complexity_budget": {"net_human_steps": 0},
        "operator_view": ["noop synthesis"],
        "coverage_degraded": False,
        "waived_lenses": [],
        "evidence_summary": {"ref_count": 0, "assumption_count": 0},
    }


def _default_synthesis_executor(
    lens_results: Mapping[str, Any],
    plan: CouncilRunPlanCore,
    ccp: Mapping[str, Any],
) -> dict[str, Any]:
    """Build deterministic v2 synthesis output from executed lens packets."""
    lens_dict = dict(lens_results)
    waived_lenses = sorted(
        lens_name for lens_name, lens_output in lens_dict.items() if lens_output is None
    )
    return build_synthesis_output(
        lens_results=lens_dict,
        plan=plan,
        ccp=ccp,
        coverage_degraded=bool(waived_lenses),
        waived_lenses=waived_lenses,
    )


def _noop_challenger_executor(
    synthesis: Mapping[str, Any],
    lens_results: Mapping[str, Any],
    plan: CouncilRunPlanCore,
) -> dict[str, Any]:
    result = {
        "weakest_claim": "none",
        "stress_test": "none",
        "material_issue": False,
        "issue_class": "other",
        "severity": "p2",
        "required_action": "rework_synthesis",
        "notes": "noop challenger",
    }
    if plan.tier in {"T2", "T3"}:
        result["ledger_completeness_ok"] = True
        result["missing_disagreements"] = []
    return result


def _noop_closure(synthesis: Mapping[str, Any], plan: CouncilRunPlanCore) -> tuple[bool, dict]:
    return True, {}


def _vendor_family(model: str, model_families: Mapping[str, list[str]] | None = None) -> str:
    """Return a normalized vendor family string for a model identifier."""
    registry = model_families or {}
    resolved = resolve_model_family(model_name=model, registry=registry)
    if resolved != "unknown":
        return resolved
    lower = (model or "").strip().lower()
    if not lower:
        return "unknown"
    if "claude" in lower:
        return "anthropic"
    if "gpt" in lower or lower.startswith("o1") or lower.startswith("o3") or "/openai/" in lower:
        return "openai"
    if "gemini" in lower:
        return "google"
    if "glm" in lower:
        return "glm"
    if "kimi" in lower:
        return "kimi"
    if "/" in lower:
        return lower.split("/", 1)[0]
    return "unknown"


def _extract_verdict_from_lenses(lens_results: dict[str, Any]) -> str:
    """Aggregate verdict from lens verdict_recommendations (majority rule, Reject > Revise > Accept)."""
    verdicts = []
    for lr in lens_results.values():
        if isinstance(lr, dict):
            v = lr.get("verdict_recommendation")
            if v:
                verdicts.append(v)
    if not verdicts:
        return VERDICT_ACCEPT
    if VERDICT_REJECT in verdicts:
        return VERDICT_REJECT
    if VERDICT_REVISE in verdicts:
        return VERDICT_REVISE
    return VERDICT_ACCEPT


def _build_contradiction_ledger_from_lenses(lens_results: dict[str, Any]) -> list[dict]:
    """Return an empty ledger; the Challenger fills contradictions, not synthesis."""
    return []


def build_synthesis_output(
    lens_results: dict[str, Any],
    plan: CouncilRunPlanCore,
    ccp: Mapping[str, Any],
    coverage_degraded: bool = False,
    waived_lenses: list[str] | None = None,
) -> dict[str, Any]:
    """
    Build a v2.2.1-compliant synthesis dict from lens results and plan core.

    - All tiers: run_type, tier, verdict, fix_plan, complexity_budget,
                 operator_view, coverage_degraded, waived_lenses
    - review run_type: adds evidence_summary
    - T2/T3 (contradiction_ledger_required): adds contradiction_ledger
    """
    if waived_lenses is None:
        waived_lenses = []

    verdict = _extract_verdict_from_lenses(lens_results)

    operator_view: list[str] = []
    for lr in lens_results.values():
        if isinstance(lr, dict):
            raw_operator_view = lr.get("operator_view", [])
            if isinstance(raw_operator_view, list):
                for pt in raw_operator_view:
                    if isinstance(pt, str):
                        operator_view.append(pt)
    if not operator_view:
        operator_view = ["synthesis complete"]

    result: dict[str, Any] = {
        "run_type": plan.run_type,
        "tier": plan.tier,
        "verdict": verdict,
        "fix_plan": [],
        "complexity_budget": {"net_human_steps": 0},
        "operator_view": operator_view,
        "coverage_degraded": coverage_degraded,
        "waived_lenses": list(waived_lenses),
    }

    if plan.run_type == "review":
        ref_count = 0
        assumption_count = 0
        for lr in lens_results.values():
            if isinstance(lr, dict):
                raw_claims = lr.get("claims", [])
                if not isinstance(raw_claims, list):
                    continue
                for claim in raw_claims:
                    if not isinstance(claim, Mapping):
                        continue
                    raw_refs = claim.get("evidence_refs", [])
                    if isinstance(raw_refs, list):
                        ref_count += len(raw_refs)
        result["evidence_summary"] = {
            "ref_count": ref_count,
            "assumption_count": assumption_count,
        }

    if plan.contradiction_ledger_required:
        result["contradiction_ledger"] = _build_contradiction_ledger_from_lenses(lens_results)

    return result


class CouncilFSMv2:
    """
    v2.2.1 council review FSM with 12 states, lens dispatch, Challenger
    rework loop (max 1 cycle), coverage degradation floor, and bounded
    closure gate (max 2 cycles).
    """

    def __init__(
        self,
        policy: CouncilPolicy,
        plan_factory: PlanFactory | None = None,
        lens_executor: LensExecutor | None = None,
        synthesis_executor: SynthesisExecutor | None = None,
        challenger_executor: ChallengerExecutor | None = None,
        closure_builder: ClosureCallable | None = None,
        closure_validator: ClosureCallable | None = None,
    ):
        self.policy = policy
        self.plan_factory = plan_factory or self._default_plan_factory
        self.lens_executor = lens_executor or self._default_lens_executor
        self.synthesis_executor = synthesis_executor or _default_synthesis_executor
        self.challenger_executor = challenger_executor or _noop_challenger_executor
        self.closure_builder = closure_builder or _noop_closure
        self.closure_validator = closure_validator or _noop_closure

    def _default_plan_factory(
        self, ccp: Mapping[str, Any], policy: CouncilPolicy
    ) -> tuple[CouncilRunPlanCore, CouncilRunMeta]:
        from .compiler import compile_council_run_plan_v2
        from .models import compute_plan_core_hash
        from datetime import datetime, timezone

        result = compile_council_run_plan_v2(ccp=ccp, policy=policy)
        core_dict = result["core"]
        meta_dict = result["meta"]

        core = CouncilRunPlanCore(**core_dict)
        meta = CouncilRunMeta(**meta_dict)
        return core, meta

    def _default_lens_executor(
        self,
        lens_name: str,
        ccp: Mapping[str, Any],
        plan: CouncilRunPlanCore,
        retry_count: int,
    ) -> dict[str, Any] | str:
        """
        Deterministic fallback lens output for mission-mode execution.

        Produces schema-valid packets without external dependencies.
        """
        planned_model = str(plan.model_assignments.get(lens_name, "auto"))
        if plan.run_type == "advisory":
            return {
                "run_type": "advisory",
                "lens_name": lens_name,
                "operator_view": [f"{lens_name}: advisory no-op assessment"],
                "confidence": "medium",
                "notes": "Default deterministic advisory lens output.",
                "evidence_status": "mixed",
                "recommendations": [
                    {
                        "action": "review_context",
                        "rationale": "Default fallback recommendation.",
                        "expected_impact": "low",
                        "confidence": "medium",
                    }
                ],
                "_actual_model": planned_model,
            }
        return {
            "run_type": "review",
            "lens_name": lens_name,
            "operator_view": [f"{lens_name}: deterministic fallback assessment"],
            "confidence": "medium",
            "notes": "Default deterministic review lens output.",
            "claims": [
                {
                    "claim_id": f"{lens_name.lower()}-default-1",
                    "statement": "No blocking issue identified in default path.",
                    "evidence_refs": ["ASSUMPTION: deterministic fallback"],
                }
            ],
            "verdict_recommendation": VERDICT_ACCEPT,
            "_actual_model": planned_model,
        }

    @staticmethod
    def _transition(
        transitions: list[dict[str, Any]],
        from_state: str,
        to_state: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        transitions.append({
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "details": details or {},
        })

    def _execute_lenses(
        self,
        plan: CouncilRunPlanCore,
        ccp: Mapping[str, Any],
        transitions: list[dict[str, Any]],
    ) -> tuple[dict[str, Any], dict[str, str], bool, bool]:
        """
        Execute all required lenses with retry + waiver logic.

        Returns:
            (lens_results, actual_models, coverage_degraded, blocked)
        """
        lens_results: dict[str, Any] = {}
        actual_models: dict[str, str] = {}
        coverage_degraded = False
        waived: list[str] = []

        for lens_name in sorted(plan.required_lenses):
            retries = 0
            success = False
            last_output: dict[str, Any] | str = {}
            raw: dict[str, Any] | str = {}

            while retries <= _LENS_MAX_RETRIES:
                try:
                    raw = self.lens_executor(lens_name, ccp, plan, retries)
                except Exception as exc:
                    raw = {"_execution_error": f"{type(exc).__name__}: {exc}"}
                gate = validate_lens_output(raw, self.policy, plan.run_type, plan.tier)

                self._transition(
                    transitions,
                    STATE_S1_EXECUTE_LENSES,
                    STATE_S1_25_SCHEMA_GATE_LENSES,
                    "lens_output_received",
                    {"lens": lens_name, "retry": retries, "valid": gate.valid},
                )

                if gate.valid:
                    last_output = gate.normalized_output or {}
                    success = True
                    break
                last_output = raw
                retries += 1

            if success:
                lens_results[lens_name] = last_output
                # Track actual model used (lens executor may embed _actual_model)
                if isinstance(last_output, dict):
                    am = last_output.get("_actual_model") or (
                        isinstance(raw, dict) and raw.get("_actual_model")
                    )
                    if am:
                        actual_models[lens_name] = str(am)
            else:
                is_mandatory = lens_name in plan.mandatory_lenses
                is_waivable = lens_name in plan.waivable_lenses
                if is_mandatory:
                    return lens_results, actual_models, coverage_degraded, True  # BLOCK
                if is_waivable:
                    waived.append(lens_name)
                    coverage_degraded = True
                    lens_results[lens_name] = None
                else:
                    return lens_results, actual_models, coverage_degraded, True  # BLOCK (default)

        return lens_results, actual_models, coverage_degraded, False

    def _check_execution_fidelity(
        self,
        actual_models: dict[str, str],
        core: CouncilRunPlanCore,
    ) -> tuple[bool, str | None]:
        """
        Verify that independent lenses ran on the vendor family specified by the plan.

        Returns:
            (ok, reason)  — reason is None when ok=True
        """
        if core.independence_required == "none":
            return True, None

        for lens_name in core.independent_lenses:
            planned = core.model_assignments.get(lens_name)
            actual = actual_models.get(lens_name, planned)
            if not planned or not actual:
                continue
            planned_family = _vendor_family(str(planned), self.policy.model_families)
            actual_family = _vendor_family(str(actual), self.policy.model_families)
            if planned_family != actual_family:
                if core.independence_required == "must" and not core.override_active:
                    return False, f"independence_fidelity_violation:{lens_name}"

        return True, None

    def run(self, ccp: Mapping[str, Any]) -> CouncilRuntimeResult:
        """
        Execute the v2.2.1 council protocol for one CCP payload.
        """
        transitions: list[dict[str, Any]] = []

        # S0_ASSEMBLE: compile plan
        try:
            core, meta = self.plan_factory(ccp, self.policy)
        except CouncilBlockedError as err:
            self._transition(
                transitions, STATE_S0_ASSEMBLE, STATE_TERMINAL_BLOCKED,
                "plan_blocked", {"category": err.category, "detail": err.detail},
            )
            return CouncilRuntimeResult(
                status="blocked",
                run_log={"status": "blocked", "state_transitions": transitions},
                decision_payload={"status": "BLOCKED", "reason": err.category, "detail": err.detail},
                block_report={"category": err.category, "detail": err.detail},
            )

        has_lenses = len(core.required_lenses) > 0
        has_challenger = core.challenger_required
        closure_gate_active = core.closure_gate_required

        # --------------- S1: Lens execution (T2/T3) ---------------
        lens_results: dict[str, Any] = {}
        coverage_degraded = False

        if has_lenses:
            self._transition(
                transitions, STATE_S0_ASSEMBLE, STATE_S1_EXECUTE_LENSES, "lenses_required",
            )

            lens_results, actual_models, coverage_degraded, blocked = self._execute_lenses(
                plan=core, ccp=ccp, transitions=transitions,
            )

            if blocked:
                self._transition(
                    transitions, STATE_S1_25_SCHEMA_GATE_LENSES,
                    STATE_TERMINAL_BLOCKED, "mandatory_lens_failed",
                )
                return CouncilRuntimeResult(
                    status="blocked",
                    run_log={"status": "blocked", "state_transitions": transitions,
                             "lens_results": dict(sorted(lens_results.items()))},
                    decision_payload={"status": "BLOCKED", "reason": "mandatory_lens_failed"},
                    block_report={"category": "mandatory_lens_failed",
                                  "detail": "A mandatory lens failed all retries."},
                )

            # S1_5_COVERAGE_COMPLETE
            self._transition(
                transitions, STATE_S1_25_SCHEMA_GATE_LENSES,
                STATE_S1_5_COVERAGE_COMPLETE, "lens_gate_complete",
                {"coverage_degraded": coverage_degraded},
            )

            # S1_55_EXECUTION_FIDELITY
            self._transition(
                transitions, STATE_S1_5_COVERAGE_COMPLETE,
                STATE_S1_55_EXECUTION_FIDELITY, "coverage_check_ok",
            )
            fidelity_ok, fidelity_reason = self._check_execution_fidelity(actual_models, core)
            if not fidelity_ok:
                self._transition(
                    transitions, STATE_S1_55_EXECUTION_FIDELITY,
                    STATE_TERMINAL_BLOCKED, "execution_fidelity_violation",
                    {"reason": fidelity_reason},
                )
                return CouncilRuntimeResult(
                    status="blocked",
                    run_log={"status": "blocked", "state_transitions": transitions,
                             "lens_results": dict(sorted(lens_results.items()))},
                    decision_payload={"status": "BLOCKED",
                                      "reason": "execution_fidelity_violation",
                                      "detail": fidelity_reason},
                    block_report={"category": "execution_fidelity_violation",
                                  "detail": fidelity_reason or ""},
                )
            self._transition(
                transitions, STATE_S1_55_EXECUTION_FIDELITY,
                STATE_S2_SYNTHESIS, "fidelity_check_ok",
            )
        else:
            self._transition(
                transitions, STATE_S0_ASSEMBLE, STATE_S2_SYNTHESIS, "no_lenses",
            )

        # --------------- S2: Synthesis ---------------
        self._transition(
            transitions, STATE_S2_SYNTHESIS,
            STATE_S2_25_SCHEMA_GATE_SYNTHESIS, "synthesis_started",
        )

        synthesis_rework_count = 0
        synthesis: dict[str, Any] = {}
        decision_status = DECISION_STATUS_NORMAL

        # Execute synthesis (with possible Challenger rework loop)
        while True:
            raw_synthesis = self.synthesis_executor(lens_results, core, ccp)
            synth_gate = validate_synthesis_output(
                raw_synthesis, self.policy, core.tier, core.run_type
            )

            if not synth_gate.valid:
                # Synthesis schema gate failure — block
                self._transition(
                    transitions, STATE_S2_25_SCHEMA_GATE_SYNTHESIS,
                    STATE_TERMINAL_BLOCKED, "synthesis_schema_rejected",
                    {"errors": synth_gate.errors},
                )
                return CouncilRuntimeResult(
                    status="blocked",
                    run_log={"status": "blocked", "state_transitions": transitions},
                    decision_payload={"status": "BLOCKED", "reason": "synthesis_schema_rejected"},
                    block_report={"category": "synthesis_schema_rejected",
                                  "detail": str(synth_gate.errors)},
                )

            synthesis = synth_gate.normalized_output or {}

            # --------------- S2_5: Challenger ---------------
            if not has_challenger:
                break  # No challenger — exit loop

            self._transition(
                transitions, STATE_S2_25_SCHEMA_GATE_SYNTHESIS,
                STATE_S2_5_CHALLENGER_REVIEW, "synthesis_schema_ok",
            )

            raw_challenger = self.challenger_executor(synthesis, lens_results, core)
            challenger_gate = validate_challenger_output(raw_challenger, self.policy, core.tier)

            if not challenger_gate.valid:
                # Challenger schema invalid — treat as no material issue
                break

            challenger_result = challenger_gate.normalized_output or {}
            material_issue = bool(challenger_result.get("material_issue", False))

            if not material_issue:
                break  # Challenger satisfied

            if synthesis_rework_count < _CHALLENGER_MAX_REWORK:
                # Rework synthesis (back to S2)
                synthesis_rework_count += 1
                self._transition(
                    transitions, STATE_S2_5_CHALLENGER_REVIEW,
                    STATE_S2_SYNTHESIS, "challenger_rework_triggered",
                    {"rework_count": synthesis_rework_count},
                )
                self._transition(
                    transitions, STATE_S2_SYNTHESIS,
                    STATE_S2_25_SCHEMA_GATE_SYNTHESIS, "synthesis_restarted",
                )
                continue  # Loop back
            else:
                # Persistent issue — force Revise, DEGRADED_CHALLENGER
                decision_status = DECISION_STATUS_DEGRADED_CHALLENGER
                synthesis["verdict"] = VERDICT_REVISE
                synthesis["fix_plan"] = synthesis.get("fix_plan") or []
                break

        # Apply coverage degradation floor after synthesis
        if coverage_degraded:
            decision_status = DECISION_STATUS_DEGRADED_COVERAGE
            if synthesis.get("verdict") == VERDICT_ACCEPT:
                synthesis["verdict"] = VERDICT_REVISE

        # --------------- S3: Closure gate ---------------
        closure_events: list[dict[str, Any]] = []
        closure_ok = True

        verdict = synthesis.get("verdict", VERDICT_REJECT)
        enter_closure = (
            closure_gate_active
            and core.run_type == "review"
            and verdict == VERDICT_ACCEPT
            and decision_status == DECISION_STATUS_NORMAL
        )

        if enter_closure:
            self._transition(
                transitions, STATE_S2_5_CHALLENGER_REVIEW if has_challenger else STATE_S2_25_SCHEMA_GATE_SYNTHESIS,
                STATE_S3_CLOSURE_GATE, "entering_closure_gate",
            )
            closure_ok = False
            for cycle in range(_CLOSURE_MAX_CYCLES):
                build_ok, build_details = self.closure_builder(synthesis, core)
                validate_ok, validate_details = self.closure_validator(synthesis, core)
                closure_events.append({
                    "cycle": cycle,
                    "build_ok": build_ok,
                    "validate_ok": validate_ok,
                    "build_details": build_details,
                    "validate_details": validate_details,
                })
                if build_ok and validate_ok:
                    closure_ok = True
                    break

            if not closure_ok:
                synthesis["verdict"] = VERDICT_REVISE
                synthesis["fix_plan"] = synthesis.get("fix_plan") or []

            self._transition(
                transitions, STATE_S3_CLOSURE_GATE, STATE_S4_CLOSEOUT,
                "closure_gate_complete", {"closure_ok": closure_ok},
            )
        else:
            last_state = (
                STATE_S2_5_CHALLENGER_REVIEW if has_challenger
                else STATE_S2_25_SCHEMA_GATE_SYNTHESIS
            )
            self._transition(
                transitions, last_state, STATE_S4_CLOSEOUT, "no_closure_gate",
            )

        # --------------- S4_CLOSEOUT ---------------
        self._transition(
            transitions, STATE_S4_CLOSEOUT, STATE_TERMINAL_COMPLETE, "run_complete",
        )

        # Build run log
        final_verdict = synthesis.get("verdict", VERDICT_REJECT)
        lens_results_sorted = dict(sorted(lens_results.items()))

        run_log: dict[str, Any] = {
            "aur_id": core.aur_id,
            "plan_core_hash": meta.plan_core_hash,
            "run_id": meta.run_id,
            "tier": core.tier,
            "run_type": core.run_type,
            "state_transitions": transitions,
            "lens_results": lens_results_sorted,
            "synthesis": synthesis,
            "decision_status": decision_status,
            "status": "complete",
        }
        if closure_events:
            run_log["closure_gate"] = closure_events

        decision_payload: dict[str, Any] = {
            "status": "COMPLETE",
            "verdict": final_verdict,
            "decision_status": decision_status,
            "fix_plan": synthesis.get("fix_plan", []),
            "run_id": meta.run_id,
            "tier": core.tier,
        }

        return CouncilRuntimeResult(
            status="complete",
            run_log=run_log,
            decision_payload=decision_payload,
            block_report=None,
        )
