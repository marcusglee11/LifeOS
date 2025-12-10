"""
Tier-2 Workflow Builder

Constructs Anti-Failure-compliant WorkflowDefinitions from high-level mission specs.

Features:
- Deterministic workflow generation (pure function)
- Anti-Failure constraints enforced by construction (max 5 steps, max 2 human)
- Only allowed step kinds: "runtime" and "human"
- No I/O, network, or subprocess work
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from runtime.orchestration.engine import (
    WorkflowDefinition,
    StepSpec,
)


# =============================================================================
# Exceptions
# =============================================================================

class AntiFailurePlanningError(Exception):
    """Raised when mission would violate Anti-Failure constraints."""
    pass


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class MissionSpec:
    """
    High-level mission specification.
    
    Attributes:
        type: Mission type identifier (e.g., "daily_loop", "run_tests").
        params: Mission-specific parameters.
    """
    type: str
    params: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Anti-Failure Limits
# =============================================================================

MAX_TOTAL_STEPS = 5
MAX_HUMAN_STEPS = 2


# =============================================================================
# Workflow Templates
# =============================================================================

def _build_daily_loop(params: Dict[str, Any]) -> WorkflowDefinition:
    """
    Build a daily loop workflow.
    
    Template:
    - Step 0: human — "Confirm today's priorities"
    - Step 1: runtime — "Summarise yesterday"
    - Step 2: runtime — "Generate today's priorities"
    - Step 3: runtime — "Log summary"
    
    Total: 4 steps, 1 human step (within limits)
    """
    # Check for excessive step requests
    requested_steps = params.get("requested_steps", 4)
    requested_human = params.get("requested_human_steps", 1)
    
    if requested_steps > MAX_TOTAL_STEPS or requested_human > MAX_HUMAN_STEPS:
        # Truncate to limits (deterministic behavior)
        requested_steps = min(requested_steps, MAX_TOTAL_STEPS)
        requested_human = min(requested_human, MAX_HUMAN_STEPS)
    
    steps: List[StepSpec] = []
    
    # Human step: confirm priorities (if requested)
    if requested_human >= 1:
        steps.append(StepSpec(
            id="daily-confirm-priorities",
            kind="human",
            payload={"description": "Confirm today's priorities"}
        ))
    
    # Runtime steps
    runtime_templates = [
        ("daily-summarise-yesterday", "Summarise yesterday's activities"),
        ("daily-generate-priorities", "Generate today's priorities"),
        ("daily-log-summary", "Log daily summary"),
        ("daily-archive", "Archive completed items"),
    ]
    
    # Calculate how many runtime steps we can add
    # (used to break loop early if we hit requested limit)
    # remaining_slots = requested_steps - len(steps)  <-- Unused variable removed for hygiene
    
    for i, (step_id, description) in enumerate(runtime_templates):
        if len(steps) >= requested_steps:
            break
        steps.append(StepSpec(
            id=step_id,
            kind="runtime",
            payload={"operation": "noop", "description": description}
        ))
    
    # Ensure we have at least one step
    if not steps:
        steps.append(StepSpec(
            id="daily-noop",
            kind="runtime",
            payload={"operation": "noop", "description": "Daily placeholder"}
        ))
    
    return WorkflowDefinition(
        id="wf-daily-loop",
        steps=steps,
        metadata={
            "mission_type": "daily_loop",
            "params": dict(sorted(params.items())) if params else {},
        }
    )


def _build_run_tests(params: Dict[str, Any]) -> WorkflowDefinition:
    """
    Build a test execution workflow.
    
    Template:
    - Step 0: runtime — "Discover tests"
    - Step 1: runtime — "Execute tests"
    - Step 2: runtime — "Report results"
    
    Total: 3 steps, 0 human steps (within limits)
    """
    target = params.get("target", "all")
    
    steps: List[StepSpec] = [
        StepSpec(
            id="tests-discover",
            kind="runtime",
            payload={"operation": "noop", "description": f"Discover tests in {target}"}
        ),
        StepSpec(
            id="tests-execute",
            kind="runtime",
            payload={"operation": "noop", "description": f"Execute tests for {target}"}
        ),
        StepSpec(
            id="tests-report",
            kind="runtime",
            payload={"operation": "noop", "description": "Generate test report"}
        ),
    ]
    
    return WorkflowDefinition(
        id="wf-run-tests",
        steps=steps,
        metadata={
            "mission_type": "run_tests",
            "type": "run_tests",
            "params": dict(sorted(params.items())) if params else {},
        }
    )


# =============================================================================
# Mission Type Registry
# =============================================================================

_MISSION_BUILDERS = {
    "daily_loop": _build_daily_loop,
    "run_tests": _build_run_tests,
}


# =============================================================================
# Public API
# =============================================================================

def build_workflow(mission: MissionSpec) -> WorkflowDefinition:
    """
    Build a WorkflowDefinition from a MissionSpec.
    
    This function is:
    - Deterministic (pure function of mission → workflow)
    - Anti-Failure compliant (max 5 steps, max 2 human by construction)
    - Uses only allowed step kinds ("runtime", "human")
    
    Args:
        mission: The mission specification.
        
    Returns:
        A valid WorkflowDefinition suitable for Orchestrator.run_workflow().
        
    Raises:
        ValueError: If mission type is unknown.
        AntiFailurePlanningError: If mission cannot be satisfied within limits.
    """
    if mission.type not in _MISSION_BUILDERS:
        raise ValueError(
            f"Unknown mission type: '{mission.type}'. "
            f"Supported types: {sorted(_MISSION_BUILDERS.keys())}"
        )
    
    builder = _MISSION_BUILDERS[mission.type]
    
    # Canonicalise params: Create a new sorted dict to ensure determinism
    # and prevent mutation of the caller's input object.
    canonical_params = dict(sorted(mission.params.items())) if mission.params else {}
    
    workflow = builder(canonical_params)
    
    # Final validation (belt and suspenders)
    _validate_anti_failure(workflow)
    
    return workflow


def _validate_anti_failure(workflow: WorkflowDefinition) -> None:
    """
    Validate that workflow respects Anti-Failure constraints.
    
    Raises:
        AntiFailurePlanningError: If constraints are violated.
    """
    if len(workflow.steps) > MAX_TOTAL_STEPS:
        raise AntiFailurePlanningError(
            f"Workflow has {len(workflow.steps)} steps, exceeds maximum of {MAX_TOTAL_STEPS}"
        )
    
    human_steps = sum(1 for s in workflow.steps if s.kind == "human")
    if human_steps > MAX_HUMAN_STEPS:
        raise AntiFailurePlanningError(
            f"Workflow has {human_steps} human steps, exceeds maximum of {MAX_HUMAN_STEPS}"
        )
    
    # Validate step kinds
    allowed_kinds = {"runtime", "human"}
    for step in workflow.steps:
        if step.kind not in allowed_kinds:
            raise AntiFailurePlanningError(
                f"Step '{step.id}' has invalid kind '{step.kind}'. "
                f"Allowed: {sorted(allowed_kinds)}"
            )
