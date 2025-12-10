"""
Tier-2 Mission Registry

Provides a unified interface for running named missions through the Tier-2
orchestration system. External callers (CLI, agents, future Tier-3) can
use run_mission() to execute any registered mission.

Features:
- Static, deterministic mission registry
- Single entry point: run_mission(name, ctx, params)
- Reuses trusted builder and orchestrator infrastructure
- No I/O, network, subprocess, or time/date access
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from runtime.orchestration.engine import (
    ExecutionContext,
    OrchestrationResult,
    WorkflowDefinition,
    StepSpec,
    Orchestrator,
)
from runtime.orchestration.builder import (
    MissionSpec,
    build_workflow,
)


# =============================================================================
# Exceptions
# =============================================================================

class UnknownMissionError(Exception):
    """Raised when a mission name is not found in the registry."""
    pass


# =============================================================================
# Workflow Builders
# =============================================================================

def _build_daily_loop_workflow(params: Optional[Dict[str, Any]] = None) -> WorkflowDefinition:
    """
    Build a daily loop workflow using the trusted builder.
    
    Reuses the existing daily_loop mission type from builder.py.
    """
    mission = MissionSpec(type="daily_loop", params=params or {})
    return build_workflow(mission)


def _build_echo_workflow(params: Optional[Dict[str, Any]] = None) -> WorkflowDefinition:
    """
    Build a minimal 'echo' workflow for testing and examples.
    
    This is a synthetic mission that:
    - Has a single runtime step
    - Is deterministic
    - Exercises the orchestrator with minimal complexity
    """
    params = params or {}
    
    steps = [
        StepSpec(
            id="echo-step",
            kind="runtime",
            payload={
                "operation": "noop",
                "description": "Echo workflow step",
                "params": dict(sorted(params.items())) if params else {},
            }
        ),
    ]
    
    return WorkflowDefinition(
        id="wf-echo",
        steps=steps,
        metadata={
            "mission_type": "echo",
            "params": dict(sorted(params.items())) if params else {},
        }
    )


# =============================================================================
# Mission Registry
# =============================================================================

# NOTE: This registry is read-only at runtime; missions are added only via code changes.

# Type: Dict[str, Callable[[Dict[str, Any] | None], WorkflowDefinition]]
MISSION_REGISTRY: Dict[str, Callable[[Optional[Dict[str, Any]]], WorkflowDefinition]] = {
    "daily_loop": _build_daily_loop_workflow,
    "echo": _build_echo_workflow,
}


# =============================================================================
# Public API
# =============================================================================

def run_mission(
    name: str,
    ctx: ExecutionContext,
    params: Optional[Dict[str, Any]] = None,
) -> OrchestrationResult:
    """
    Run a named mission through the Tier-2 orchestration system.
    
    This is the unified entry point for external callers (CLI, agents, Tier-3).
    
    Args:
        name: The mission name (must be registered in MISSION_REGISTRY).
        ctx: Execution context with initial state.
        params: Optional mission parameters.
        
    Returns:
        OrchestrationResult with execution details, lineage, and receipt.
        
    Raises:
        UnknownMissionError: If the mission name is not registered.
        AntiFailureViolation: If workflow exceeds step limits.
        EnvelopeViolation: If workflow uses disallowed step kinds.
    """
    # Look up the builder in the registry
    if name not in MISSION_REGISTRY:
        raise UnknownMissionError(
            f"Unknown mission: '{name}'. "
            f"Available missions: {sorted(MISSION_REGISTRY.keys())}"
        )
    
    # Get the builder and build the workflow
    builder = MISSION_REGISTRY[name]
    workflow = builder(params)
    
    # Run through the orchestrator
    orchestrator = Orchestrator()
    result = orchestrator.run_workflow(workflow, ctx)
    
    return result
