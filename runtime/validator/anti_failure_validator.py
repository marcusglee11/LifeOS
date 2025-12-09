"""
FP-4.x CND-4: Anti-Failure Validator (Hardened)
Enhanced workflow validator with attestation logging and adversarial detection.
"""
from typing import List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum, auto
import re


class StepActor(Enum):
    """Actor type for workflow steps."""
    HUMAN = auto()
    AGENT = auto()
    SYSTEM = auto()


class ValidatorError(Exception):
    """Raised when workflow validation fails."""
    pass


@dataclass
class HumanAttestation:
    """
    Attestation of human governance primitives used in a workflow.
    
    Only three primitives are allowed:
    - Intent: Human expresses what they want
    - Approve: Human approves proposed action
    - Veto: Human rejects proposed action
    """
    intent_used: bool = False
    approve_used: bool = False
    veto_used: bool = False
    
    @property
    def total_primitives(self) -> int:
        return sum([self.intent_used, self.approve_used, self.veto_used])
    
    def to_dict(self) -> dict:
        return {
            "intent_used": self.intent_used,
            "approve_used": self.approve_used,
            "veto_used": self.veto_used,
            "total_primitives": self.total_primitives
        }


@dataclass
class WorkflowStep:
    """A single step in a workflow."""
    name: str
    actor: StepActor
    description: str
    is_routine: bool = False
    human_primitive: Optional[str] = None  # "intent", "approve", "veto", or None


@dataclass
class ValidationResult:
    """Result of workflow validation."""
    is_valid: bool
    total_steps: int
    human_steps: int
    attestation: HumanAttestation
    violations: List[str]
    warnings: List[str]


class AntiFailureValidator:
    """
    Validates workflows against Anti-Failure constraints.
    
    Constraints:
    - MAX_STEPS: Maximum total steps (default: 5)
    - MAX_HUMAN_STEPS: Maximum human involvement (default: 2)
    - Human steps must use governance primitives (Intent/Approve/Veto)
    - No routine human operations allowed
    
    Adversarial Detection:
    - Smuggled human steps (hidden in agent descriptions)
    - Workflow chaining to exceed limits
    - Fake agent tasks that require human effort
    """
    
    MAX_STEPS = 5
    MAX_HUMAN_STEPS = 2
    VALID_PRIMITIVES = {"intent", "approve", "veto"}
    
    # Patterns indicating hidden human effort
    HIDDEN_HUMAN_PATTERNS = [
        r'\bmanual(ly)?\b',
        r'\bby hand\b',
        r'\bhuman review\b',
        r'\buser (must|should|needs to)\b',
        r'\bask (the )?user\b',
        r'\brequires? (human|user)\b',
        r'\b(copy|paste|type|enter|click)\b.*\buser\b',
    ]
    
    def __init__(
        self,
        max_steps: int = 5,
        max_human_steps: int = 2,
        detect_adversarial: bool = True
    ):
        """
        Initialize validator.
        
        Args:
            max_steps: Maximum total steps allowed.
            max_human_steps: Maximum human steps allowed.
            detect_adversarial: Enable adversarial pattern detection.
        """
        self.max_steps = max_steps
        self.max_human_steps = max_human_steps
        self.detect_adversarial = detect_adversarial
        self._compiled_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.HIDDEN_HUMAN_PATTERNS
        ]
    
    def validate(self, steps: List[WorkflowStep]) -> ValidationResult:
        """
        Validate a workflow against Anti-Failure constraints.
        
        Args:
            steps: List of workflow steps.
            
        Returns:
            ValidationResult with detailed findings.
        """
        violations = []
        warnings = []
        
        # Count steps
        total_steps = len(steps)
        human_steps = [s for s in steps if s.actor == StepActor.HUMAN]
        human_count = len(human_steps)
        
        # Build attestation
        attestation = HumanAttestation()
        for step in human_steps:
            if step.human_primitive == "intent":
                attestation.intent_used = True
            elif step.human_primitive == "approve":
                attestation.approve_used = True
            elif step.human_primitive == "veto":
                attestation.veto_used = True
        
        # Check total steps
        if total_steps > self.max_steps:
            violations.append(
                f"Workflow has {total_steps} steps, maximum is {self.max_steps}"
            )
        
        # Check human steps
        if human_count > self.max_human_steps:
            violations.append(
                f"Workflow has {human_count} human steps, maximum is {self.max_human_steps}"
            )
        
        # Check human primitives are valid
        for step in human_steps:
            if step.human_primitive and step.human_primitive not in self.VALID_PRIMITIVES:
                violations.append(
                    f"Invalid human primitive '{step.human_primitive}' in step '{step.name}'. "
                    f"Valid: {self.VALID_PRIMITIVES}"
                )
        
        # Check for routine human operations
        routine_human = [s for s in human_steps if s.is_routine]
        if routine_human:
            for step in routine_human:
                violations.append(
                    f"Routine human operation not allowed: '{step.name}'"
                )
        
        # Adversarial detection
        if self.detect_adversarial:
            smuggled = self._detect_smuggled_human_steps(steps)
            for step_name, pattern in smuggled:
                warnings.append(
                    f"Potential smuggled human effort in '{step_name}': "
                    f"matches pattern '{pattern}'"
                )
        
        return ValidationResult(
            is_valid=len(violations) == 0,
            total_steps=total_steps,
            human_steps=human_count,
            attestation=attestation,
            violations=violations,
            warnings=warnings
        )
    
    def validate_or_raise(self, steps: List[WorkflowStep]) -> ValidationResult:
        """
        Validate and raise if invalid.
        
        Args:
            steps: List of workflow steps.
            
        Returns:
            ValidationResult if valid.
            
        Raises:
            ValidatorError: If workflow is invalid.
        """
        result = self.validate(steps)
        if not result.is_valid:
            msg = "Workflow validation failed:\n"
            msg += "\n".join(f"  - {v}" for v in result.violations)
            raise ValidatorError(msg)
        return result
    
    def _detect_smuggled_human_steps(
        self,
        steps: List[WorkflowStep]
    ) -> List[tuple]:
        """
        Detect agent/system steps that may hide human effort.
        
        Returns:
            List of (step_name, matched_pattern) tuples.
        """
        findings = []
        
        for step in steps:
            if step.actor in (StepActor.AGENT, StepActor.SYSTEM):
                text = f"{step.name} {step.description}"
                for pattern in self._compiled_patterns:
                    if pattern.search(text):
                        findings.append((step.name, pattern.pattern))
                        break  # One match per step is enough
        
        return findings
    
    def check_workflow_chaining(
        self,
        workflows: List[List[WorkflowStep]]
    ) -> tuple[bool, List[str]]:
        """
        Check if multiple workflows chain to exceed limits.
        
        Args:
            workflows: List of workflow step lists.
            
        Returns:
            Tuple of (is_valid, violations).
        """
        violations = []
        
        total_steps = sum(len(wf) for wf in workflows)
        total_human = sum(
            sum(1 for s in wf if s.actor == StepActor.HUMAN)
            for wf in workflows
        )
        
        # Effective limits for chained workflows (same as single)
        if total_steps > self.max_steps:
            violations.append(
                f"Chained workflows have {total_steps} effective steps, "
                f"exceeds single-workflow limit of {self.max_steps}"
            )
        
        if total_human > self.max_human_steps:
            violations.append(
                f"Chained workflows have {total_human} human steps, "
                f"exceeds single-workflow limit of {self.max_human_steps}"
            )
        
        return (len(violations) == 0, violations)


# Convenience function
def create_attestation_from_result(result: ValidationResult) -> dict:
    """Convert validation result to attestation dict for AMU₀."""
    return {
        "human_attestation": result.attestation.to_dict(),
        "total_steps": result.total_steps,
        "human_steps": result.human_steps,
        "violations": result.violations,
        "warnings": result.warnings
    }
