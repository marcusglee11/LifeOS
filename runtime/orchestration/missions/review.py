"""
Phase 3 Mission Types - Review Mission

Runs council review on a packet (BUILD_PACKET or REVIEW_PACKET).
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3 - Mission: review
"""
from __future__ import annotations

from typing import Any, Dict, List

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
    MissionEscalationRequired,
)


# Valid review verdicts per Council Protocol
VALID_VERDICTS = frozenset({"approved", "rejected", "needs_revision", "escalate"})

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
            
            # Step 2: Call Agent API for 'reviewer_architect' seat
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
            
            # Step 3: Synthesize decision
            # For MVP, we treat the architect's verdict as the final verdict
            decision = response.packet or {
                "verdict": "needs_revision",
                "rationale": response.content,
                "concerns": [],
                "recommendations": []
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
            
            # Handle escalation
            if final_verdict == "escalate":
                return self._make_result(
                    success=True,
                    outputs={
                        "verdict": final_verdict,
                        "council_decision": council_decision,
                    },
                    executed_steps=executed_steps,
                    escalation_reason="Architect review requires CEO escalation",
                )
            
            return self._make_result(
                success=True,
                outputs={
                    "verdict": final_verdict,
                    "council_decision": council_decision,
                },
                executed_steps=executed_steps,
                evidence={
                    "call_id": response.call_id,
                    "model_used": response.model_used,
                },
            )
            
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
