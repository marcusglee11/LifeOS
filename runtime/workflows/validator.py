"""
FP-3.7: Anti-Failure Workflow Validator
Enforces Anti-Failure constraints on workflows:
- Maximum 5 steps total
- Maximum 2 human steps
- No routine human operations
"""
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum, auto


class StepActor(Enum):
    """Actor type for workflow steps."""
    HUMAN = auto()
    AGENT = auto()
    SYSTEM = auto()


class WorkflowValidationError(Exception):
    """Raised when a workflow violates Anti-Failure constraints."""
    pass


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    actor: StepActor
    description: str
    is_routine: bool = False  # True if this is a routine operation


@dataclass
class ValidationResult:
    """Result of workflow validation."""
    is_valid: bool
    total_steps: int
    human_steps: int
    routine_human_ops: int
    violations: List[str]
    suggestions: List[str]


class WorkflowValidator:
    """
    Validates workflows against Anti-Failure constraints.
    
    Constraints:
    - MAX_STEPS: Maximum total steps (default: 5)
    - MAX_HUMAN_STEPS: Maximum human involvement (default: 2)
    - NO_ROUTINE_HUMAN_OPS: Human should not do routine work
    """
    
    MAX_STEPS = 5
    MAX_HUMAN_STEPS = 2
    
    def __init__(
        self,
        max_steps: int = 5,
        max_human_steps: int = 2,
        allow_routine_human_ops: bool = False
    ):
        """
        Initialize Workflow Validator.
        
        Args:
            max_steps: Maximum total steps allowed.
            max_human_steps: Maximum human steps allowed.
            allow_routine_human_ops: Whether to allow routine human operations.
        """
        self.max_steps = max_steps
        self.max_human_steps = max_human_steps
        self.allow_routine_human_ops = allow_routine_human_ops
    
    def validate(self, steps: List[WorkflowStep]) -> ValidationResult:
        """
        Validate a workflow against Anti-Failure constraints.
        
        Args:
            steps: List of workflow steps.
        
        Returns:
            ValidationResult with detailed findings.
        """
        violations = []
        suggestions = []
        
        # Count steps
        total_steps = len(steps)
        human_steps = sum(1 for s in steps if s.actor == StepActor.HUMAN)
        routine_human_ops = sum(
            1 for s in steps 
            if s.actor == StepActor.HUMAN and s.is_routine
        )
        
        # Check total steps
        if total_steps > self.max_steps:
            violations.append(
                f"Workflow has {total_steps} steps, maximum is {self.max_steps}"
            )
            suggestions.append(
                "Consider combining steps or delegating to agents"
            )
        
        # Check human steps
        if human_steps > self.max_human_steps:
            violations.append(
                f"Workflow has {human_steps} human steps, maximum is {self.max_human_steps}"
            )
            suggestions.append(
                "Human involvement should be limited to: Intent/Approve/Veto/Governance"
            )
        
        # Check routine human operations
        if routine_human_ops > 0 and not self.allow_routine_human_ops:
            violations.append(
                f"Workflow has {routine_human_ops} routine human operations"
            )
            for step in steps:
                if step.actor == StepActor.HUMAN and step.is_routine:
                    suggestions.append(
                        f"Automate '{step.name}': {step.description}"
                    )
        
        return ValidationResult(
            is_valid=len(violations) == 0,
            total_steps=total_steps,
            human_steps=human_steps,
            routine_human_ops=routine_human_ops,
            violations=violations,
            suggestions=suggestions
        )
    
    def validate_or_raise(self, steps: List[WorkflowStep]) -> ValidationResult:
        """
        Validate a workflow and raise if invalid.
        
        Args:
            steps: List of workflow steps.
        
        Returns:
            ValidationResult if valid.
        
        Raises:
            WorkflowValidationError: If workflow is invalid.
        """
        result = self.validate(steps)
        if not result.is_valid:
            error_msg = "Workflow validation failed:\n"
            error_msg += "\n".join(f"  - {v}" for v in result.violations)
            if result.suggestions:
                error_msg += "\n\nSuggestions:\n"
                error_msg += "\n".join(f"  - {s}" for s in result.suggestions)
            raise WorkflowValidationError(error_msg)
        return result
    
    def validate_mission(self, mission: dict) -> ValidationResult:
        """
        Validate a mission definition.
        
        Args:
            mission: Mission dictionary with 'execution_flow' key.
        
        Returns:
            ValidationResult.
        """
        steps = []
        execution_flow = mission.get('execution_flow', [])
        
        for step_def in execution_flow:
            # Determine actor - default to AGENT
            actor = StepActor.AGENT
            step_name = step_def.get('step', 'unnamed')
            
            # Check if step requires human
            if 'human_' in step_name.lower() or 'approve' in step_name.lower():
                actor = StepActor.HUMAN
            
            steps.append(WorkflowStep(
                name=step_name,
                actor=actor,
                description=step_def.get('description', ''),
                is_routine=False
            ))
        
        return self.validate(steps)
    
    @staticmethod
    def create_human_step(name: str, description: str, is_routine: bool = False) -> WorkflowStep:
        """Create a human-actor step."""
        return WorkflowStep(
            name=name,
            actor=StepActor.HUMAN,
            description=description,
            is_routine=is_routine
        )
    
    @staticmethod
    def create_agent_step(name: str, description: str) -> WorkflowStep:
        """Create an agent-actor step."""
        return WorkflowStep(
            name=name,
            actor=StepActor.AGENT,
            description=description,
            is_routine=False
        )
    
    @staticmethod
    def create_system_step(name: str, description: str) -> WorkflowStep:
        """Create a system-actor step."""
        return WorkflowStep(
            name=name,
            actor=StepActor.SYSTEM,
            description=description,
            is_routine=False
        )
