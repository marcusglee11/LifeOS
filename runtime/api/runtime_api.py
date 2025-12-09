"""
FP-4.x CND-6: Runtime API
Operational API for runtime interactions.
"""
from typing import List, Dict, Any, Optional
from runtime.validator.anti_failure_validator import (
    AntiFailureValidator, WorkflowStep, ValidationResult
)


class RuntimeAPI:
    """
    Operational API for runtime layer.
    
    Provides workflow submission, validation, and DAP operations.
    """
    
    def __init__(self, validator: Optional[AntiFailureValidator] = None):
        self._validator = validator or AntiFailureValidator()
    
    def validate_workflow(self, steps: List[WorkflowStep]) -> ValidationResult:
        """Validate a workflow against Anti-Failure constraints."""
        return self._validator.validate(steps)
    
    def submit_workflow(self, steps: List[WorkflowStep]) -> Dict[str, Any]:
        """Submit a workflow for execution."""
        result = self._validator.validate_or_raise(steps)
        return {
            "submitted": True,
            "validation": {
                "total_steps": result.total_steps,
                "human_steps": result.human_steps,
                "attestation": result.attestation.to_dict()
            }
        }
