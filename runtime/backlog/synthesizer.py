"""
Backlog Synthesizer v1.0
========================

Synthesizes mission packets from backlog tasks.
Deterministic, fail-closed, wires to orchestrator registry.

Per Mission Synthesis Engine MVP.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import hashlib
import uuid

from runtime.backlog.parser import parse_backlog, get_task_by_id, TaskSpec
from runtime.backlog.context_resolver import resolve_context, ResolvedContext


class SynthesisError(Exception):
    """Raised when mission synthesis fails."""
    pass


@dataclass(frozen=True)
class MissionPacket:
    """Synthesized mission packet ready for orchestrator."""
    packet_id: str
    task_id: str
    task_description: str
    mission_type: str
    context_refs: tuple[str, ...]
    constraints: tuple[str, ...]
    priority: str


def _compute_packet_id(task: TaskSpec, context: ResolvedContext) -> str:
    """Compute deterministic packet ID."""
    h = hashlib.sha256()
    h.update(task.id.encode("utf-8"))
    h.update(task.description.encode("utf-8"))
    h.update(task.priority.encode("utf-8"))
    for path in sorted(context.resolved_paths + context.baseline_paths):
        h.update(path.encode("utf-8"))
    return f"MSE-{h.hexdigest()[:16]}"


def synthesize_mission(
    task_id: str,
    backlog_path: Path,
    repo_root: Path,
    mission_type: str = "steward",
) -> MissionPacket:
    """
    Synthesize a mission packet from a backlog task.
    
    Steps:
    1. Parse backlog, find task by ID
    2. Resolve context
    3. Generate mission packet
    4. Return packet ready for orchestrator
    
    Args:
        task_id: Task identifier from backlog
        backlog_path: Path to backlog YAML file
        repo_root: Repository root
        mission_type: Mission type (default: steward for doc updates)
        
    Returns:
        MissionPacket ready for orchestrator
        
    Raises:
        SynthesisError: If synthesis fails
    """
    # Step 1: Parse backlog
    try:
        tasks = parse_backlog(backlog_path)
    except Exception as e:
        raise SynthesisError(f"Failed to parse backlog: {e}")
    
    # Find task
    task = get_task_by_id(tasks, task_id)
    if task is None:
        raise SynthesisError(
            f"Task '{task_id}' not found in backlog. "
            f"Available: {[t.id for t in tasks]}"
        )
    
    # Step 2: Resolve context
    try:
        context = resolve_context(
            task_id=task.id,
            context_hints=list(task.context_hints),
            repo_root=repo_root,
        )
    except Exception as e:
        raise SynthesisError(f"Failed to resolve context: {e}")
    
    # Step 3: Generate packet
    all_context = context.resolved_paths + context.baseline_paths
    packet_id = _compute_packet_id(task, context)
    
    return MissionPacket(
        packet_id=packet_id,
        task_id=task.id,
        task_description=task.description,
        mission_type=mission_type,
        context_refs=all_context,
        constraints=task.constraints,
        priority=task.priority,
    )


def execute_mission(
    packet: MissionPacket,
    repo_root: Path,
) -> Dict[str, Any]:
    """
    Execute a synthesized mission via orchestrator registry.
    
    Args:
        packet: MissionPacket from synthesize_mission()
        repo_root: Repository root
        
    Returns:
        Dict with execution results including orchestrator output
        
    Raises:
        SynthesisError: If execution fails
    """
    from runtime.orchestration.registry import run_mission, UnknownMissionError
    from runtime.orchestration.engine import ExecutionContext
    
    # Create execution context per engine.py interface:
    # ExecutionContext(initial_state, metadata) - no run_id
    ctx = ExecutionContext(
        initial_state={
            "task_id": packet.task_id,
            "task_description": packet.task_description,
            "context_refs": list(packet.context_refs),
            "constraints": list(packet.constraints),
        },
        metadata={
            "packet_id": packet.packet_id,
            "mission_type": packet.mission_type,
            "priority": packet.priority,
        },
    )
    
    try:
        # Execute via registry
        result = run_mission(
            name=packet.mission_type,
            ctx=ctx,
            params={
                "task_spec": packet.task_description,
                "context_refs": list(packet.context_refs),
            },
        )
        
        return {
            "success": result.success if hasattr(result, "success") else True,
            "packet_id": packet.packet_id,
            "mission_type": packet.mission_type,
            "result": result,
        }
        
    except UnknownMissionError as e:
        raise SynthesisError(f"Unknown mission type '{packet.mission_type}': {e}")
    except Exception as e:
        raise SynthesisError(f"Mission execution failed: {e}")
