"""
Phase 3 Mission Types - Autonomous Build Cycle

Composes design → review → build → review → steward into end-to-end workflow.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3 - Mission: autonomous_build_cycle
"""
from __future__ import annotations

from typing import Any, Dict, List

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
)
from runtime.orchestration.missions.design import DesignMission
from runtime.orchestration.missions.review import ReviewMission
from runtime.orchestration.missions.build import BuildMission
from runtime.orchestration.missions.steward import StewardMission


class AutonomousBuildCycleMission(BaseMission):
    """
    Autonomous Build Cycle: End-to-end workflow composition.
    
    Inputs:
        - task_spec (str): Task description
        - context_refs (list[str], optional): Context file paths
        
    Outputs:
        - commit_hash (str): Final commit hash (if succeeded)
        - cycle_report (dict): Summary of the full cycle
        
    Workflow:
        1. design: Transform task_spec → BUILD_PACKET
        2. review_design: Council reviews BUILD_PACKET
        3. gate_design_approval: Escalate if not approved
        4. build: Execute build with approved packet
        5. review_output: Council reviews build output
        6. gate_output_approval: Escalate if not approved
        7. steward: Commit approved changes
        
    Escalation: Any gate failure escalates to CEO (does not auto-retry).
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.AUTONOMOUS_BUILD_CYCLE
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Validate autonomous build cycle inputs.
        
        Same as design mission (which is the entry point).
        """
        # Delegate to design mission validation
        design = DesignMission()
        design.validate_inputs(inputs)
    
    def run(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> MissionResult:
        """
        Execute the autonomous build cycle.
        
        Composes sub-missions in sequence:
        design → review → build → review → steward
        
        Escalates on any rejection (does not retry).
        """
        executed_steps: List[str] = []
        cycle_report: Dict[str, Any] = {
            "phases": [],
            "escalation": None,
        }
        
        try:
            # Step 0: Validate inputs
            self.validate_inputs(inputs)
            executed_steps.append("validate_inputs")
            
            # Step 1: Design
            design_mission = DesignMission()
            design_result = design_mission.run(context, inputs)
            cycle_report["phases"].append({
                "phase": "design",
                "success": design_result.success,
                "error": design_result.error,
            })
            executed_steps.append("design")
            
            if not design_result.success:
                return self._make_result(
                    success=False,
                    outputs={"cycle_report": cycle_report},
                    executed_steps=executed_steps,
                    error=f"Design phase failed: {design_result.error}",
                )
            
            build_packet = design_result.outputs.get("build_packet")
            
            # Step 2: Review design
            review_mission = ReviewMission()
            review_inputs = {
                "subject_packet": build_packet,
                "review_type": "build_review",
            }
            review_result = review_mission.run(context, review_inputs)
            cycle_report["phases"].append({
                "phase": "review_design",
                "success": review_result.success,
                "verdict": review_result.outputs.get("verdict"),
            })
            executed_steps.append("review_design")
            
            if not review_result.success:
                return self._make_result(
                    success=False,
                    outputs={"cycle_report": cycle_report},
                    executed_steps=executed_steps,
                    error=f"Design review failed: {review_result.error}",
                )
            
            # Step 3: Gate design approval
            design_verdict = review_result.outputs.get("verdict")
            if design_verdict != "approved":
                cycle_report["escalation"] = {
                    "phase": "gate_design_approval",
                    "reason": f"Design not approved: {design_verdict}",
                }
                executed_steps.append("gate_design_approval")
                return self._make_result(
                    success=True,  # Escalation is valid outcome
                    outputs={"cycle_report": cycle_report},
                    executed_steps=executed_steps,
                    escalation_reason=f"Design review verdict: {design_verdict}",
                )
            executed_steps.append("gate_design_approval")
            
            # Step 4: Build
            build_mission = BuildMission()
            build_inputs = {
                "build_packet": build_packet,
                "approval": review_result.outputs.get("council_decision"),
            }
            build_result = build_mission.run(context, build_inputs)
            cycle_report["phases"].append({
                "phase": "build",
                "success": build_result.success,
                "error": build_result.error,
            })
            executed_steps.append("build")
            
            if not build_result.success:
                return self._make_result(
                    success=False,
                    outputs={"cycle_report": cycle_report},
                    executed_steps=executed_steps,
                    error=f"Build phase failed: {build_result.error}",
                )
            
            review_packet = build_result.outputs.get("review_packet")
            
            # Step 5: Review output
            output_review_inputs = {
                "subject_packet": review_packet,
                "review_type": "output_review",
            }
            output_review_result = review_mission.run(context, output_review_inputs)
            cycle_report["phases"].append({
                "phase": "review_output",
                "success": output_review_result.success,
                "verdict": output_review_result.outputs.get("verdict"),
            })
            executed_steps.append("review_output")
            
            if not output_review_result.success:
                return self._make_result(
                    success=False,
                    outputs={"cycle_report": cycle_report},
                    executed_steps=executed_steps,
                    error=f"Output review failed: {output_review_result.error}",
                )
            
            # Step 6: Gate output approval
            output_verdict = output_review_result.outputs.get("verdict")
            if output_verdict != "approved":
                cycle_report["escalation"] = {
                    "phase": "gate_output_approval",
                    "reason": f"Output not approved: {output_verdict}",
                }
                executed_steps.append("gate_output_approval")
                return self._make_result(
                    success=True,  # Escalation is valid outcome
                    outputs={"cycle_report": cycle_report},
                    executed_steps=executed_steps,
                    escalation_reason=f"Output review verdict: {output_verdict}",
                )
            executed_steps.append("gate_output_approval")
            
            # Step 7: Steward
            steward_mission = StewardMission()
            steward_inputs = {
                "review_packet": review_packet,
                "approval": output_review_result.outputs.get("council_decision"),
            }
            steward_result = steward_mission.run(context, steward_inputs)
            cycle_report["phases"].append({
                "phase": "steward",
                "success": steward_result.success,
                "commit_hash": steward_result.outputs.get("commit_hash"),
            })
            executed_steps.append("steward")
            
            if not steward_result.success:
                return self._make_result(
                    success=False,
                    outputs={"cycle_report": cycle_report},
                    executed_steps=executed_steps,
                    error=f"Steward phase failed: {steward_result.error}",
                )
            
            commit_hash = steward_result.outputs.get("commit_hash")
            
            return self._make_result(
                success=True,
                outputs={
                    "commit_hash": commit_hash,
                    "cycle_report": cycle_report,
                },
                executed_steps=executed_steps,
                evidence={
                    "phases_completed": len(cycle_report["phases"]),
                    "commit_hash": commit_hash,
                },
            )
            
        except MissionValidationError as e:
            return self._make_result(
                success=False,
                outputs={"cycle_report": cycle_report},
                executed_steps=executed_steps,
                error=f"Input validation failed: {e}",
            )
        except Exception as e:
            return self._make_result(
                success=False,
                outputs={"cycle_report": cycle_report},
                executed_steps=executed_steps,
                error=f"Unexpected error: {e}",
            )
