"""
Tier-2 Daily Loop Runner

Composes the Workflow Builder and Orchestrator into a single deterministic
entrypoint for running daily loop workflows.

Features:
- Single function API: run_daily_loop(ctx, params)
- Deterministic (pure function of ctx.initial_state + params)
- Anti-Failure compliant by composition
- No I/O, network, subprocess, or time/date access
"""
from __future__ import annotations

import copy
from typing import Any, Dict, Optional

from runtime.orchestration.engine import (
    Orchestrator,
    ExecutionContext,
    OrchestrationResult,
)
from runtime.orchestration.builder import MissionSpec, build_workflow


def run_daily_loop(
    ctx: ExecutionContext,
    params: Optional[Dict[str, Any]] = None,
) -> OrchestrationResult:
    """
    Run a daily loop workflow.
    
    This is the primary programmatic entrypoint for Tier-2 daily loop execution.
    It composes the Workflow Builder and Orchestrator into a single call.
    
    The daily loop workflow:
    - Confirms today's priorities (human step, if configured)
    - Summarises yesterday's activities
    - Generates today's priorities
    - Logs the daily summary
    
    Anti-Failure Compliance:
    - ≤ 5 total steps (enforced by builder)
    - ≤ 2 human steps (enforced by builder)
    - Only "runtime" and "human" step kinds
    
    Determinism:
    - Given identical ctx.initial_state and params, output is identical
    - No I/O, network, subprocess, or time access
    
    Args:
        ctx: Execution context with initial state.
        params: Optional mission parameters (e.g., {"mode": "default"}).
        
    Returns:
        OrchestrationResult with execution details, lineage, and receipt.
        
    Raises:
        AntiFailureViolation: If builder produces invalid workflow (shouldn't happen).
        EnvelopeViolation: If workflow uses disallowed step kinds (shouldn't happen).
    """
    # Defensive copy: Prevent aliasing with caller-owned mutable dicts
    params_snapshot = copy.deepcopy(params) if params is not None else {}
    
    # Construct mission spec for daily loop
    mission = MissionSpec(
        type="daily_loop",
        params=params_snapshot,
    )
    
    # Build workflow using the trusted builder
    workflow = build_workflow(mission)
    
    # Execute workflow using the trusted orchestrator
    orchestrator = Orchestrator()
    result = orchestrator.run_workflow(workflow, ctx)
    
    return result
