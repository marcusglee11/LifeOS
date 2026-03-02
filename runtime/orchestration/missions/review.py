"""
Phase 3 Mission Types - Review Mission

Runs council review on a packet (BUILD_PACKET or REVIEW_PACKET).
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3 - Mission: review
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
)
from runtime.orchestration.council import CouncilFSMv2, load_council_policy


# Valid review verdicts per Council Protocol
VALID_VERDICTS = frozenset({"approved", "rejected", "needs_revision", "escalate"})
PROTOCOL_TO_MISSION_VERDICT = {
    "Accept": "approved",
    "Go with Fixes": "needs_revision",
    "Revise": "needs_revision",
    "Reject": "rejected",
}

# Review seats per architecture
REVIEW_SEATS = ("architect", "alignment", "risk", "governance")


class ReviewMission(BaseMission):
    """
    Review mission: Run council review on a packet.

    Inputs:
        - subject_packet (dict): The packet to review
        - review_type (str): Type of review (build_review, output_review)

    Outputs:
        - verdict (str): Review verdict
        - council_decision (dict): Full council decision with seat outputs

    Steps:
        1. prepare_ccp: Transform packet to Council Context Pack
        2. run_seats: Run each review seat (stubbed for MVP)
        3. synthesize: Synthesize seat outputs into decision
        4. validate_decision: Validate output against schema
    """

    def __init__(self) -> None:
        super().__init__()
        from runtime.agents.models import load_model_config
        self._model_config = load_model_config()

    @property
    def mission_type(self) -> MissionType:
        return MissionType.REVIEW
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Validate review mission inputs.
        
        Required: subject_packet (dict), review_type (string)
        """
        # Check subject_packet
        subject_packet = inputs.get("subject_packet")
        if not subject_packet:
            raise MissionValidationError("subject_packet is required")
        if not isinstance(subject_packet, dict):
            raise MissionValidationError("subject_packet must be a dict")
        
        # Check review_type
        review_type = inputs.get("review_type")
        if not review_type:
            raise MissionValidationError("review_type is required")
        if not isinstance(review_type, str):
            raise MissionValidationError("review_type must be a string")
        
        valid_review_types = ("build_review", "output_review", "governance_review")
        if review_type not in valid_review_types:
            raise MissionValidationError(
                f"review_type must be one of {valid_review_types}, got '{review_type}'"
            )

        run_type = inputs.get("run_type", "review")
        if not isinstance(run_type, str):
            raise MissionValidationError("run_type must be a string when provided")
        if run_type not in {"review", "advisory"}:
            raise MissionValidationError("run_type must be 'review' or 'advisory'")
    
    def run(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> MissionResult:
        executed_steps: List[str] = []

        try:
            # Step 1: Validate inputs
            self.validate_inputs(inputs)
            executed_steps.append("validate_inputs")
            use_council_runtime = bool(inputs.get("use_council_runtime", False))
            if use_council_runtime:
                result = self._run_council_runtime(context, inputs, executed_steps)
            else:
                result = self._run_legacy_single_seat(context, inputs, executed_steps)

            # Shadow council V2 (non-gating, fire-and-forget)
            self._run_shadow_council(context, inputs)

            return result

        except MissionValidationError as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Input validation failed: {e}",
            )
        except Exception as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Unexpected error: {e}",
            )

    def _run_shadow_council(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> None:
        """Fire shadow council V2. Strictly non-gating — never raises."""
        try:
            from runtime.orchestration.council.shadow_runner import ShadowCouncilRunner
            runner = ShadowCouncilRunner(context.repo_root)
            ccp = self._build_ccp(context, inputs)
            runner.run_shadow(run_id=context.run_id, ccp=ccp)
        except Exception:
            pass  # Shadow is strictly non-gating

    def _run_legacy_single_seat(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
        executed_steps: List[str],
    ) -> MissionResult:
        """Preserve existing single-seat behavior for compatibility."""
        from runtime.agents.api import call_agent, AgentCall

        call = AgentCall(
            role="reviewer_architect",
            packet={
                "subject_packet": inputs["subject_packet"],
                "review_type": inputs["review_type"]
            },
            model="auto",
        )

        response = call_agent(call, run_id=context.run_id)
        executed_steps.append("architect_review_llm_call")

        reviewer_packet_parsed = response.packet is not None
        if response.packet is not None:
            decision = response.packet
        else:
            fallback_verdict = None
            verdict_match = re.search(
                r'(?m)^verdict:\s*["\']?(\w+)["\']?\s*$',
                response.content,
            )
            if verdict_match:
                candidate = verdict_match.group(1).lower()
                if candidate in VALID_VERDICTS:
                    fallback_verdict = candidate
            decision = {
                "verdict": fallback_verdict or "needs_revision",
                "rationale": response.content,
                "concerns": [],
                "recommendations": [],
            }

        final_verdict = decision.get("verdict", "needs_revision")
        if final_verdict not in VALID_VERDICTS:
            final_verdict = "needs_revision"

        council_decision = {
            "verdict": final_verdict,
            "seat_outputs": {"architect": decision},
            "synthesis": decision.get("rationale", response.content),
        }
        executed_steps.append("synthesize")

        if final_verdict == "escalate":
            return self._make_result(
                success=True,
                outputs={
                    "verdict": final_verdict,
                    "council_decision": council_decision,
                    "reviewer_packet_parsed": reviewer_packet_parsed,
                },
                executed_steps=executed_steps,
                escalation_reason="Architect review requires CEO escalation",
                evidence={
                    "call_id": response.call_id,
                    "model_used": response.model_used,
                    "usage": response.usage,
                },
            )

        return self._make_result(
            success=True,
            outputs={
                "verdict": final_verdict,
                "council_decision": council_decision,
                "reviewer_packet_parsed": reviewer_packet_parsed,
            },
            executed_steps=executed_steps,
            evidence={
                "call_id": response.call_id,
                "model_used": response.model_used,
                "usage": response.usage,
            },
        )

    @staticmethod
    def _default_touches(review_type: str) -> list[str]:
        if review_type == "governance_review":
            return ["governance_protocol"]
        if review_type == "build_review":
            return ["runtime_core"]
        return ["interfaces"]

    def _build_ccp(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        review_type = str(inputs["review_type"])
        run_type = str(inputs.get("run_type", "review"))
        subject_packet = inputs["subject_packet"]
        subject_hash = hashlib.sha256(
            json.dumps(subject_packet, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        header = {
            "aur_id": inputs.get("aur_id", f"{review_type}:{subject_hash[:12]}"),
            "aur_type": inputs.get("aur_type", "code"),
            "blast_radius": inputs.get("blast_radius", "module"),
            "change_class": inputs.get("change_class", "amend"),
            "closure_gate_required": bool(inputs.get("closure_gate_required", review_type == "output_review")),
            "model_plan_v1": inputs.get("model_plan_v1", {}),
            "override": inputs.get("override", {}),
            "reversibility": inputs.get("reversibility", "moderate"),
            "run_id": context.run_id,
            "run_type": run_type,
            "safety_critical": bool(inputs.get("safety_critical", False)),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "touches": inputs.get("touches", self._default_touches(review_type)),
            "uncertainty": inputs.get("uncertainty", "medium"),
        }

        sections = inputs.get("sections")
        if not isinstance(sections, dict):
            sections = {
                "objective": f"Run council review for {review_type}.",
                "scope": {
                    "review_type": review_type,
                    "subject_fields": sorted(subject_packet.keys()),
                },
                "constraints": inputs.get(
                    "constraints",
                    ["Fail closed on schema and protocol violations."],
                ),
                "artifacts": inputs.get(
                    "artifacts",
                    [{"kind": "subject_packet", "sha256": subject_hash}],
                ),
            }

        ccp = {
            "header": header,
            "review_type": review_type,
            "sections": sections,
            "subject_packet": subject_packet,
        }

        bootstrap = inputs.get("bootstrap")
        if isinstance(bootstrap, dict):
            ccp["header"]["bootstrap"] = bootstrap
        return ccp

    def _run_council_runtime(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
        executed_steps: List[str],
    ) -> MissionResult:
        ccp = self._build_ccp(context, inputs)
        executed_steps.append("prepare_ccp")

        policy_path = inputs.get("council_policy_path")
        policy = load_council_policy(policy_path)
        _lens_executor = None
        if self._model_config.council_provider_overrides:
            from runtime.orchestration.council.multi_provider import build_multi_provider_executor
            _lens_executor = build_multi_provider_executor(
                config=self._model_config,
                provider_overrides=self._model_config.council_provider_overrides,
            )
        fsm = CouncilFSMv2(policy=policy, lens_executor=_lens_executor)
        runtime_result = fsm.run(ccp)
        executed_steps.append("execute_council_fsm")

        if runtime_result.status == "blocked":
            detail = "blocked"
            if runtime_result.block_report:
                detail = runtime_result.block_report.get("detail", detail)
            council_decision = {
                "protocol_status": "BLOCKED",
                "run_log": runtime_result.run_log,
                "block_report": runtime_result.block_report,
                "synthesis": {"verdict": "Reject"},
                "verdict": "escalate",
            }
            return self._make_result(
                success=True,
                outputs={
                    "verdict": "escalate",
                    "council_decision": council_decision,
                    "reviewer_packet_parsed": True,
                },
                executed_steps=executed_steps,
                escalation_reason=f"Council runtime blocked: {detail}",
                evidence={
                    "council_runtime_status": runtime_result.status,
                    "usage": {"total": 0},
                },
            )

        protocol_verdict = str(runtime_result.decision_payload.get("verdict", "Reject"))
        mission_verdict = PROTOCOL_TO_MISSION_VERDICT.get(protocol_verdict, "needs_revision")
        council_decision = {
            "protocol_status": runtime_result.decision_payload.get("status", "COMPLETE"),
            "protocol_verdict": protocol_verdict,
            "run_log": runtime_result.run_log,
            "synthesis": runtime_result.run_log.get("synthesis", {}),
            "tier": runtime_result.decision_payload.get("tier"),
            "verdict": mission_verdict,
        }

        escalation_reason = None
        if mission_verdict == "escalate":
            escalation_reason = "Council runtime requested escalation."

        return self._make_result(
            success=True,
            outputs={
                "verdict": mission_verdict,
                "council_decision": council_decision,
                "reviewer_packet_parsed": True,
            },
            executed_steps=executed_steps,
            escalation_reason=escalation_reason,
            evidence={
                "council_runtime_status": runtime_result.status,
                "run_id": runtime_result.decision_payload.get("run_id"),
                "usage": {"total": 0},
            },
        )
