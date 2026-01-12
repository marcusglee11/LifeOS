"""
Tier-2 Orchestration Engine

Implements the Tier-2 orchestrator for multi-step workflows with:
- Anti-Failure constraints (max 5 steps, max 2 human steps)
- Execution envelope enforcement (only 'runtime' and 'human' step kinds)
- Deterministic execution and serialization
- Immutability guarantees for inputs
- LLM call operations via OpenCode HTTP REST API
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# =============================================================================
# Exceptions (imported from shared module to avoid cross-tier coupling)
# =============================================================================

from runtime.errors import AntiFailureViolation, EnvelopeViolation

# =============================================================================
# LLM Client (lazy import to avoid hard dependency)
# =============================================================================

# Import OpenCode client for LLM calls
try:
    from runtime.agents.opencode_client import (
        OpenCodeClient,
        LLMCall,
        OpenCodeError,
    )
    _HAS_OPENCODE_CLIENT = True
except ImportError:
    _HAS_OPENCODE_CLIENT = False
    OpenCodeClient = None
    LLMCall = None
    OpenCodeError = Exception  # Fallback for type hints

# Re-export for backwards compatibility
__all_exceptions__ = ["AntiFailureViolation", "EnvelopeViolation"]


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

    Supports operations:
    - noop: No operation (default)
    - fail: Halt execution with error
    - llm_call: Make LLM call via OpenCode HTTP REST API
    """

    # Anti-Failure limits
    MAX_TOTAL_STEPS = 5
    MAX_HUMAN_STEPS = 2

    # Allowed step kinds (execution envelope)
    ALLOWED_KINDS = frozenset({"runtime", "human"})

    def __init__(self):
        """Initialize orchestrator with no active LLM client."""
        self._llm_client: Optional[OpenCodeClient] = None

    def _get_llm_client(self) -> OpenCodeClient:
        """
        Get or create the LLM client (lazy initialization).

        Starts the server on first call, reuses for subsequent calls.

        Returns:
            OpenCodeClient instance with running server.

        Raises:
            RuntimeError: If OpenCode client is not available.
            OpenCodeError: If server fails to start.
        """
        if not _HAS_OPENCODE_CLIENT:
            raise RuntimeError(
                "OpenCode client not available. "
                "Install runtime.agents package or check imports."
            )

        if self._llm_client is None:
            self._llm_client = OpenCodeClient(log_calls=True)
            self._llm_client.start_server()

        return self._llm_client

    def _cleanup_llm_client(self) -> None:
        """Stop and cleanup the LLM client if running."""
        if self._llm_client is not None:
            try:
                self._llm_client.stop_server()
            except Exception:
                pass  # Best effort cleanup
            self._llm_client = None

    def _execute_llm_call(
        self,
        step: StepSpec,
        state: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
        """
        Execute an llm_call operation.

        Args:
            step: The step specification with llm_call payload.
            state: Current workflow state (will be modified).

        Returns:
            Tuple of (success, error_message).

        Payload fields:
            - prompt (required): The prompt to send to the LLM.
            - model (optional): Model identifier (default: claude-sonnet-4).
            - output_key (optional): Key to store result (default: "llm_response").
        """
        payload = step.payload

        # Validate required fields
        prompt = payload.get("prompt")
        if not prompt:
            return False, f"Step '{step.id}' llm_call missing required 'prompt' field"

        # Get optional fields
        model = payload.get("model", "openrouter/anthropic/claude-sonnet-4")
        output_key = payload.get("output_key", "llm_response")

        try:
            # Get or create client (lazy init)
            client = self._get_llm_client()

            # Make the LLM call
            request = LLMCall(prompt=prompt, model=model)
            response = client.call(request)

            # Store result in state
            state[output_key] = response.content

            # Also store metadata for audit
            state[f"{output_key}_metadata"] = {
                "call_id": response.call_id,
                "model_used": response.model_used,
                "latency_ms": response.latency_ms,
                "timestamp": response.timestamp,
            }

            return True, None

        except OpenCodeError as e:
            return False, f"Step '{step.id}' llm_call failed: {e}"
        except Exception as e:
            return False, f"Step '{step.id}' llm_call unexpected error: {e}"
    
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

        try:
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

                    elif operation == "llm_call":
                        # Execute LLM call operation
                        op_success, op_error = self._execute_llm_call(step, state)
                        if not op_success:
                            success = False
                            failed_step_id = step.id
                            error_message = op_error
                            break

                    # For "noop" or any other operation, continue without state change

                elif step.kind == "human":
                    # Human steps: record but don't modify state
                    # (In real implementation, would wait for human input)
                    pass

        finally:
            # =================================================================
            # Cleanup resources (always runs, even on exception)
            # =================================================================
            self._cleanup_llm_client()

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
