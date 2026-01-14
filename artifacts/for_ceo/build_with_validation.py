"""
Build With Validation mission type.
Implements Worker -> Validator loop per LifeOS governance.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
)

class BuildWithValidationMission(BaseMission):
    """
    Build With Validation: Worker -> Validator loop.
    
    Inputs:
        - task_description (str): What to implement
        - max_iterations (int): Max retry attempts (default: 3)
        - worker_model (str): Model for builder (default: "auto")
        - validator_model (str): Model for reviewer (default: "auto")
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.BUILD_WITH_VALIDATION
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        if not inputs.get("task_description"):
            raise MissionValidationError("task_description is required")
            
    def run(self, context: MissionContext, inputs: Dict[str, Any]) -> MissionResult:
        task_description = inputs["task_description"]
        max_iterations = inputs.get("max_iterations", 3)
        worker_model = inputs.get("worker_model", "auto")
        validator_model = inputs.get("validator_model", "auto")
        
        executed_steps = []
        iteration = 0
        
        from runtime.agents.api import call_agent, AgentCall
        
        while iteration < max_iterations:
            iteration += 1
            
            # Step 1: Worker builds
            worker_call = AgentCall(
                role="builder",
                packet={"task": task_description, "iteration": iteration},
                model=worker_model
            )
            worker_response = call_agent(worker_call, run_id=context.run_id)
            executed_steps.append(f"worker_iter_{iteration}")
            
            # Step 2: Validator checks
            validator_call = AgentCall(
                role="reviewer",
                packet={
                    "implementation": worker_response.content,
                    "task": task_description
                },
                model=validator_model
            )
            validator_response = call_agent(validator_call, run_id=context.run_id)
            executed_steps.append(f"validator_iter_{iteration}")
            
            # Parse validation (assuming LLM returns structured JSON or we parse it)
            # For MVP, assuming the reviewer uses a specific output format
            approved = "APPROVED" in validator_response.content
            
            if approved:
                return self._make_result(
                    success=True,
                    outputs={"result": worker_response.content},
                    executed_steps=executed_steps,
                    evidence={
                        "iterations": iteration,
                        "worker_model": worker_response.model_used,
                        "validator_model": validator_response.model_used
                    }
                )
            
            # Feedback for next loop
            # We append the feedback to the task description to guide the next attempt
            task_description += f"\n\nValidator feedback (Iteration {iteration}):\n{validator_response.content}"
            
        return self._make_result(
            success=False,
            error=f"Validation failed after {max_iterations} iterations",
            executed_steps=executed_steps,
            escalation_reason=f"Multi-iteration validation failure for task: {inputs['task_description'][:100]}..."
        )
