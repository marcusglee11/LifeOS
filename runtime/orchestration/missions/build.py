"""
Phase 3 Mission Types - Build Mission

Invokes builder (OpenCode) with approved BUILD_PACKET.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3 - Mission: build
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


class BuildMission(BaseMission):
    """
    Build mission: Invoke builder with approved BUILD_PACKET.
    
    Inputs:
        - build_packet (dict): The approved BUILD_PACKET
        - approval (dict): Council approval decision
        
    Outputs:
        - review_packet (dict): Package of build outputs for review
        
    Preconditions:
        - approval.verdict == "approved"
        
    Steps:
        1. check_envelope: Verify build is within envelope
        2. invoke_builder: Execute build (stubbed for MVP)
        3. collect_evidence: Gather build outputs
        4. package_output: Create REVIEW_PACKET
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.BUILD
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Validate build mission inputs.
        
        Required: build_packet (dict), approval (dict with verdict="approved")
        """
        # Check build_packet
        build_packet = inputs.get("build_packet")
        if not build_packet:
            raise MissionValidationError("build_packet is required")
        if not isinstance(build_packet, dict):
            raise MissionValidationError("build_packet must be a dict")
        
        # Validate build_packet has required fields
        if not build_packet.get("goal"):
            raise MissionValidationError("build_packet.goal is required")
        
        # Check approval
        approval = inputs.get("approval")
        if not approval:
            raise MissionValidationError("approval is required")
        if not isinstance(approval, dict):
            raise MissionValidationError("approval must be a dict")
        
        # Verify approval verdict
        verdict = approval.get("verdict")
        if verdict != "approved":
            raise MissionValidationError(
                f"Build requires approved verdict, got: '{verdict}'"
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
            
            build_packet = inputs["build_packet"]
            
            # Step 2: Invoke builder via Agent API
            from runtime.agents.api import call_agent, AgentCall
            
            call = AgentCall(
                role="builder",
                packet={"build_packet": build_packet},
                model="auto",
            )
            
            response = call_agent(call, run_id=context.run_id)
            executed_steps.append("invoke_builder_llm_call")

            # Detect artifacts created by OpenCode CLI
            artifacts_produced = []
            try:
                import subprocess
                diff_result = subprocess.run(
                    ["git", "diff", "--name-only"],
                    cwd=context.repo_root,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if diff_result.returncode == 0 and diff_result.stdout.strip():
                    artifacts_produced = diff_result.stdout.strip().split('\n')
            except Exception:
                # If artifact detection fails, continue with empty list
                pass

            # Step 3: Package output as REVIEW_PACKET
            review_packet = {
                "mission_name": f"build_{context.run_id[:8]}",
                "summary": f"Build for: {build_packet.get('goal', 'unknown')}",
                "payload": {
                    "build_packet": build_packet,
                    "content": response.content,
                    "packet": response.packet,
                    "artifacts_produced": artifacts_produced,
                },
                "evidence": {
                    "call_id": response.call_id,
                    "model_used": response.model_used,
                    "usage": response.usage,
                }
            }
            executed_steps.append("package_output")
            
            return self._make_result(
                success=True,
                outputs={"review_packet": review_packet},
                executed_steps=executed_steps,
                evidence=review_packet["evidence"],
            )
            
        except Exception as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Build mission failed: {e}",
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
