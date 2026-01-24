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

# Import model config for default model resolution
try:
    from runtime.agents.models import load_model_config, resolve_model_auto
    _HAS_MODEL_CONFIG = True
except ImportError:
    _HAS_MODEL_CONFIG = False

    def _get_default_model() -> str:
        """Fallback if models module unavailable."""
        return "openrouter/x-ai/grok-4.1-fast"
else:
    def _get_default_model() -> str:
        """Get default model from config/models.yaml."""
        try:
            config = load_model_config()
            if config.default_chain:
                return config.default_chain[0]
        except Exception:
            pass
        return "openrouter/x-ai/grok-4.1-fast"

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

        # Get optional fields - use config-driven default model
        model = payload.get("model") or _get_default_model()
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

    def _detect_git_context(self) -> tuple:
        """
        Detect git context using runtime detection (fail-soft).

        Detection strategy (Option 2):
        - repo_root: git rev-parse --show-toplevel, fallback to cwd
        - baseline_commit: git rev-parse HEAD, fallback to None
        - Use short timeout (2 seconds) and catch all errors

        Returns:
            Tuple of (repo_root: Path, baseline_commit: Optional[str])
        """
        import subprocess
        from pathlib import Path

        # Detect repo_root (fail-soft)
        repo_root = Path.cwd()
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                repo_root = Path(result.stdout.strip())
        except Exception:
            pass  # Fail-soft: use cwd

        # Detect baseline_commit (fail-soft)
        # P1.1 Fix: Use repo_root as cwd to ensure we get commit from correct repo
        baseline_commit = None
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=2,
                cwd=repo_root
            )
            if result.returncode == 0:
                baseline_commit = result.stdout.strip()
        except Exception:
            pass  # Fail-soft: leave as None

        return repo_root, baseline_commit

    def _execute_mission(
        self,
        step: StepSpec,
        state: Dict[str, Any],
        ctx: ExecutionContext
    ) -> tuple:
        """
        Execute a mission operation with tolerant interface.

        CRITICAL: Reuses ctx from orchestrator (does NOT construct new ExecutionContext).

        Payload fields:
            - mission_type (required): Type of mission to execute
            - inputs or params (optional): Mission input data (default: {})

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        # Local imports to avoid cycles
        from pathlib import Path

        payload = step.payload

        # Validate required fields
        mission_type = payload.get("mission_type")
        if not mission_type:
            return False, "mission_type not specified in step payload"

        # Get inputs (try both 'inputs' and 'params' keys)
        inputs = payload.get("inputs") or payload.get("params", {})
        if not isinstance(inputs, dict):
            inputs = {}

        # Get git context from ctx.metadata if available (preferred for CLI/External callers)
        metadata = getattr(ctx, 'metadata', {}) or {}
        repo_root_str = metadata.get("repo_root")
        baseline_commit = metadata.get("baseline_commit")
        
        if repo_root_str:
            repo_root = Path(repo_root_str)
        else:
            # Detect git context (fail-soft)
            repo_root, baseline_commit = self._detect_git_context()

        # Update metadata back if it was missing
        if hasattr(ctx, 'metadata'):
            if ctx.metadata is None:
                ctx.metadata = {}
            ctx.metadata["repo_root"] = str(repo_root)
            ctx.metadata["baseline_commit"] = baseline_commit

        # Always use direct path for operation="mission" to avoid recursion loops
        # (registry.run_mission builds workflows that call operation="mission", creating a cycle if we call registry again)
        use_direct_path = True

        # Execute mission (with selective exception handling)
        try:
            if use_direct_path:
                # Fallback path: Direct mission instantiation
                from runtime.orchestration.missions import get_mission_class, MissionContext
                import uuid

                mission_class = get_mission_class(mission_type)
                mission = mission_class()

                # Optional validation (tolerant interface)
                if hasattr(mission, 'validate_inputs'):
                    mission.validate_inputs(inputs)

                # CRITICAL: Missions may expect MissionContext, not ExecutionContext
                # Build MissionContext from git context
                mission_context = MissionContext(
                    repo_root=repo_root,
                    baseline_commit=baseline_commit,
                    run_id=str(uuid.uuid4()),
                    operation_executor=None,
                    journal=None,
                    metadata={"step_id": step.id}
                )

                # Execute mission with MissionContext
                result = mission.run(mission_context, inputs)
            else:
                # Preferred path: Use registry dispatch
                # AttributeError/TypeError here are programming bugs, not dispatch failures
                result = registry.run_mission(mission_type, ctx, inputs)

            # Normalize result to dict (uniform handling regardless of dispatch path)
            if hasattr(result, 'to_dict'):
                result_dict = result.to_dict()
            elif isinstance(result, dict):
                result_dict = result
            else:
                # Minimal dict from attributes
                result_dict = {
                    'success': bool(getattr(result, 'success', False)),
                    'status': getattr(result, 'status', None),
                    'output': getattr(result, 'output', None),
                    'error': getattr(result, 'error', None)
                }

            # Determine success (uniform logic)
            if 'success' in result_dict:
                success = bool(result_dict['success'])
            elif result_dict.get('status') is not None:
                success = (result_dict['status'] == 'success')
            else:
                success = False

            # Store result TWO ways (backward compat + correct)
            state["mission_result"] = result_dict  # Legacy: last result
            state.setdefault("mission_results", {})[step.id] = result_dict  # Correct: per-step

            # Check success
            if not success:
                error = result_dict.get('error') or "Mission failed without error message"
                return False, f"Mission '{mission_type}' failed: {error}"

            return True, None

        except (AttributeError, TypeError) as e:
            # CRITICAL: When using registry path, these are programming bugs - RE-RAISE
            if not use_direct_path:
                raise
            # For direct path, treat as mission error (may be mission implementation issue)
            return False, f"Mission execution error: {str(e)}"

        except Exception as e:
            # Catch mission-level errors (MissionError, ValidationError, etc.)
            return False, f"Mission execution error: {str(e)}"

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

                    elif operation == "mission":
                        # CRITICAL: Pass ctx to helper (reuse existing ExecutionContext)
                        op_success, op_error = self._execute_mission(step, state, ctx)
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
