"""
Task Specification Dataclass for Autonomous Loop.

This module defines the canonical representation of a task passed between:
- Backlog parser -> Loop controller
- Loop controller -> Design phase
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List
from enum import Enum


class TaskPriority(str, Enum):
    """Valid task priority levels."""
    P0 = "P0"
    P1 = "P1"


@dataclass(frozen=True)
class TaskSpec:
    """
    Task specification for autonomous loop consumption.

    This is the canonical representation passed between:
    - Backlog parser -> Loop controller
    - Loop controller -> Design phase

    Attributes:
        item_key: SHA256-based deterministic key (truncated)
        title: Task title
        priority: P0 or P1
        dod: Definition of Done (acceptance criteria)
        owner: Task owner
        context: Additional context (default: empty)
        dependencies: List of dependency markers (default: empty)
        line_number: Line number in BACKLOG.md (default: 0)
        original_line: Original line text for mutation (default: empty)
    """
    item_key: str
    title: str
    priority: TaskPriority
    dod: str
    owner: str
    context: str = ""
    dependencies: List[str] = field(default_factory=list)
    line_number: int = 0
    original_line: str = ""

    def to_design_input(self) -> Dict[str, Any]:
        """
        Convert to design phase input format.

        Returns:
            Dict with task_description, acceptance_criteria, context, priority, item_key
        """
        return {
            "task_description": f"{self.title}\n\nAcceptance Criteria:\n{self.dod}",
            "acceptance_criteria": self.dod,
            "context": self.context,
            "priority": self.priority.value,
            "item_key": self.item_key,
        }

    def is_blocked(self) -> bool:
        """
        Check if task has unresolved dependencies.

        Returns:
            True if task has explicit dependencies or blocked markers in context
        """
        if self.dependencies:
            return True

        blocked_markers = ["blocked", "depends on", "waiting for"]
        return any(marker in self.context.lower() for marker in blocked_markers)

    def to_cli_summary(self) -> str:
        """
        One-line summary for CLI display.

        Returns:
            Formatted string like "[P0] Task title (abc12345)"
        """
        return f"[{self.priority.value}] {self.title} ({self.item_key[:8]})"
