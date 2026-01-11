"""
Backlog Package
===============

Provides backlog parsing, context resolution, and mission synthesis
for the Mission Synthesis Engine MVP.

Public API:
- parse_backlog(path) -> List[TaskSpec]
- resolve_context(task_id, hints, repo_root) -> ResolvedContext  
- synthesize_mission(task_id, backlog_path, repo_root) -> MissionPacket
"""
from runtime.backlog.parser import (
    parse_backlog,
    get_task_by_id,
    sort_tasks_by_priority,
    TaskSpec,
    BacklogParseError,
)
from runtime.backlog.context_resolver import (
    resolve_context,
    ResolvedContext,
    ContextResolutionError,
)
from runtime.backlog.synthesizer import (
    synthesize_mission,
    MissionPacket,
    SynthesisError,
)

__all__ = [
    # Parser
    "parse_backlog",
    "get_task_by_id", 
    "sort_tasks_by_priority",
    "TaskSpec",
    "BacklogParseError",
    # Context Resolver
    "resolve_context",
    "ResolvedContext",
    "ContextResolutionError",
    # Synthesizer
    "synthesize_mission",
    "MissionPacket",
    "SynthesisError",
]
