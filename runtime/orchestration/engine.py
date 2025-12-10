"""
Tier-2 Orchestration Engine

Implements the Tier-2 orchestrator for multi-step workflows with:
- Anti-Failure constraints (max 5 steps, max 2 human steps)
- Execution envelope enforcement (only 'runtime' and 'human' step kinds)
- Deterministic execution and serialization
- Immutability guarantees for inputs
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =============================================================================
# Exceptions
# =============================================================================

class AntiFailureViolation(Exception):
    """Raised when workflow violates Anti-Failure constraints."""
    pass


class EnvelopeViolation(Exception):
    """Raised when workflow violates execution envelope constraints."""
    pass


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class StepSpec:
    """
    Specification for a single workflow step.
    
    Attributes:
        id: Unique identifier for the step.
        kind: Type of step ('runtime' or 'human').
        payload: Step-specific configuration data.
    """
    id: str
    kind: str
    payload: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict with stable key ordering."""
        return {
            "id": self.id,
            "kind": self.kind,
            "payload": dict(sorted(self.payload.items())) if self.payload else {},
        }


@dataclass
class WorkflowDefinition:
    """
    Definition of a multi-step workflow.
    
    Attributes:
        id: Unique identifier for the workflow.
        steps: Ordered list of steps to execute.
        metadata: Additional workflow metadata.
        name: Alias for id (for compatibility).
    """
    id: str = ""
    steps: List[StepSpec] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    name: str = ""  # Alias for id
    
    def __post_init__(self):
        # Enforce consistency between 'id' and 'name'
        if self.id and not self.name:
            self.name = self.id
        elif self.name and not self.id:
            self.id = self.name
        elif self.id and self.name and self.id != self.name:
            raise ValueError(f"WorkflowDefinition id/name mismatch: '{self.id}' vs '{self.name}'")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict with stable key ordering."""
        return {
            "id": self.id,
            "metadata": dict(sorted(self.metadata.items())) if self.metadata else {},
            "steps": [s.to_dict() for s in self.steps],
        }



@dataclass
class ExecutionContext:
    """
    Context for workflow execution.
    
    Attributes:
        initial_state: Starting state for the workflow.
        metadata: Optional execution metadata.
    """
    initial_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class OrchestrationResult:
    """
    Result of a workflow execution.
    
    Attributes:
        id: Workflow ID.
        success: Whether execution succeeded.
        executed_steps: Steps that were executed (in order).
        final_state: State after execution.
        failed_step_id: ID of the step that failed (if any).
        error_message: Error message (if any).
        lineage: Lineage record for audit.
        receipt: Execution receipt for attestation.
    """
    id: str
    success: bool
    executed_steps: List[StepSpec]
    final_state: Dict[str, Any]
    failed_step_id: Optional[str] = None
    error_message: Optional[str] = None
    lineage: Dict[str, Any] = field(default_factory=dict)
    receipt: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to JSON-serializable dict with stable key ordering.
        
        Keys: "id", "success", "executed_steps", "final_state",
              "failed_step_id", "error_message", "lineage", "receipt"
        """
        return {
            "error_message": self.error_message,
            "executed_steps": [s.to_dict() for s in self.executed_steps],
            "failed_step_id": self.failed_step_id,
            "final_state": dict(sorted(self.final_state.items())) if self.final_state else {},
            "id": self.id,
            "lineage": dict(sorted(self.lineage.items())) if self.lineage else {},
            "receipt": dict(sorted(self.receipt.items())) if self.receipt else {},
            "success": self.success,
        }


# =============================================================================
# Orchestrator
# =============================================================================

class Orchestrator:
    """
    Tier-2 Orchestrator for executing multi-step workflows.
    
    Enforces:
    - Anti-Failure constraints (max 5 steps, max 2 human steps)
    - Execution envelope (only 'runtime' and 'human' step kinds allowed)
    - Deterministic execution
    - Input immutability
    """
    
    # Anti-Failure limits
    MAX_TOTAL_STEPS = 5
    MAX_HUMAN_STEPS = 2
    
    # Allowed step kinds (execution envelope)
    ALLOWED_KINDS = frozenset({"runtime", "human"})
    
    def run_workflow(
        self,
        workflow: WorkflowDefinition,
        ctx: ExecutionContext
    ) -> OrchestrationResult:
        """
        Execute a workflow within Tier-2 constraints.
        
        Args:
            workflow: The workflow definition to execute.
            ctx: Execution context with initial state.
            
        Returns:
            OrchestrationResult with execution details.
            
        Raises:
            AntiFailureViolation: If workflow exceeds step limits.
            EnvelopeViolation: If workflow uses disallowed step kinds.
        """
        # =================================================================
        # Pre-execution validation (before any step runs)
        # =================================================================
        
        # Check envelope constraints first
        for step in workflow.steps:
            if step.kind not in self.ALLOWED_KINDS:
                raise EnvelopeViolation(
                    f"Step '{step.id}' has disallowed kind '{step.kind}'. "
                    f"Allowed kinds: {sorted(self.ALLOWED_KINDS)}"
                )
        
        # Check Anti-Failure constraints
        total_steps = len(workflow.steps)
        if total_steps > self.MAX_TOTAL_STEPS:
            raise AntiFailureViolation(
                f"Workflow has {total_steps} steps, exceeds maximum of {self.MAX_TOTAL_STEPS}"
            )
        
        human_steps = sum(1 for s in workflow.steps if s.kind == "human")
        if human_steps > self.MAX_HUMAN_STEPS:
            raise AntiFailureViolation(
                f"Workflow has {human_steps} human steps, exceeds maximum of {self.MAX_HUMAN_STEPS}"
            )
        
        # =================================================================
        # Execution (immutable inputs)
        # =================================================================
        
        # Deep copy state to ensure immutability of ctx.initial_state
        state = copy.deepcopy(ctx.initial_state)
        
        executed_steps: List[StepSpec] = []
        failed_step_id: Optional[str] = None
        error_message: Optional[str] = None
        success = True
        
        for step in workflow.steps:
            # Record step as executed (including the failing one)
            # Store a frozen snapshot (deepcopy) to prevent post-execution mutation aliasing
            executed_steps.append(copy.deepcopy(step))
            
            if step.kind == "runtime":
                # Process runtime step
                operation = step.payload.get("operation", "noop")
                
                if operation == "fail":
                    # Halt execution with failure
                    success = False
                    failed_step_id = step.id
                    reason = step.payload.get("reason", "unspecified")
                    error_message = f"Step '{step.id}' failed: {reason}"
                    break
                
                # For "noop" or any other operation, continue without state change
                # (Future: could implement state mutations here)
                
            elif step.kind == "human":
                # Human steps: record but don't modify state
                # (In real implementation, would wait for human input)
                pass
        
        # =================================================================
        # Build result structures
        # =================================================================
        
        # Build lineage (deterministic)
        lineage = {
            "executed_step_ids": [s.id for s in executed_steps],
            "workflow_id": workflow.id,
        }
        
        # Build receipt (deterministic)
        receipt = {
            "id": workflow.id,
            "steps": [s.id for s in executed_steps],
        }
        
        return OrchestrationResult(
            id=workflow.id,
            success=success,
            executed_steps=executed_steps,
            final_state=state,
            failed_step_id=failed_step_id,
            error_message=error_message,
            lineage=lineage,
            receipt=receipt,
        )
