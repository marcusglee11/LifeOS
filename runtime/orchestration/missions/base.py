"""
Phase 3 Mission Types - Base Classes

Defines the interface and common types for all mission implementations.
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class MissionType(str, Enum):
    """
    Enumeration of valid mission types.

    Per architecture §5.3, these are the only valid mission types.
    Fail-closed: unknown types must raise an error.
    """
    DESIGN = "design"
    REVIEW = "review"
    BUILD = "build"
    BUILD_WITH_VALIDATION = "build_with_validation"
    STEWARD = "steward"
    AUTONOMOUS_BUILD_CYCLE = "autonomous_build_cycle"
    ECHO = "echo"


class MissionError(Exception):
    """Base exception for mission errors."""
    pass


class MissionValidationError(MissionError):
    """Raised when mission input validation fails."""
    pass


class MissionExecutionError(MissionError):
    """Raised when mission execution fails."""
    pass


class MissionEscalationRequired(MissionError):
    """Raised when mission requires CEO escalation."""
    
    def __init__(self, reason: str, evidence: Dict[str, Any] = None):
        self.reason = reason
        self.evidence = evidence or {}
        super().__init__(f"Escalation required: {reason}")


@dataclass
class MissionContext:
    """
    Context for mission execution.
    
    Provides access to repo state, operation executor, and configuration
    without exposing internals that missions should not access.
    """
    # Repository root path
    repo_root: Path
    
    # Git baseline commit (HEAD at mission start)
    baseline_commit: str
    
    # Run ID for this mission execution
    run_id: str
    
    # Operation executor reference (optional, for missions that invoke operations)
    operation_executor: Optional[Any] = None
    
    # Mission journal for recording steps (optional)
    journal: Optional[Any] = None
    
    # Additional context data
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MissionResult:
    """
    Result of mission execution.
    
    All missions must return this structure for consistent handling.
    """
    # Whether mission succeeded
    success: bool
    
    # Mission type that was executed
    mission_type: MissionType
    
    # Output data (mission-specific)
    outputs: Dict[str, Any] = field(default_factory=dict)
    
    # Steps that were executed
    executed_steps: List[str] = field(default_factory=list)
    
    # Error message if failed
    error: Optional[str] = None
    
    # Escalation reason if escalation required
    escalation_reason: Optional[str] = None
    
    # Evidence for audit
    evidence: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict with deterministic ordering."""
        return {
            "error": self.error,
            "escalation_reason": self.escalation_reason,
            "evidence": dict(sorted(self.evidence.items())) if self.evidence else {},
            "executed_steps": self.executed_steps,
            "mission_type": self.mission_type.value,
            "outputs": dict(sorted(self.outputs.items())) if self.outputs else {},
            "success": self.success,
        }


class BaseMission(ABC):
    """
    Abstract base class for all mission implementations.
    
    Subclasses must implement:
    - run(context, inputs) -> MissionResult
    - validate_inputs(inputs) -> None (raises MissionValidationError)
    """
    
    @property
    @abstractmethod
    def mission_type(self) -> MissionType:
        """Return the mission type for this implementation."""
        pass
    
    @abstractmethod
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Validate mission inputs.
        
        Raises MissionValidationError if inputs are invalid.
        Must be deterministic and have no side effects.
        """
        pass
    
    @abstractmethod
    def run(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> MissionResult:
        """
        Execute the mission.
        
        Args:
            context: Execution context with repo state and services
            inputs: Mission-specific input data
            
        Returns:
            MissionResult with outputs or error
            
        The implementation must:
        - Be deterministic given the same inputs and context
        - Record all steps in executed_steps
        - Handle failures gracefully (return error, don't raise)
        - Support rollback via compensation actions
        """
        pass
    
    def _make_result(
        self,
        success: bool,
        outputs: Dict[str, Any] = None,
        executed_steps: List[str] = None,
        error: str = None,
        escalation_reason: str = None,
        evidence: Dict[str, Any] = None,
    ) -> MissionResult:
        """Helper to create MissionResult with this mission's type."""
        return MissionResult(
            success=success,
            mission_type=self.mission_type,
            outputs=outputs or {},
            executed_steps=executed_steps or [],
            error=error,
            escalation_reason=escalation_reason,
            evidence=evidence or {},
        )
