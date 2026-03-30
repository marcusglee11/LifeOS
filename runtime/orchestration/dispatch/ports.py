"""
SupervisorPort and CuratorPort — Protocol interfaces for COO Agent integration.

These are file-based communication interfaces. The COO Agent implements them
by reading/writing files in artifacts/supervision/ and artifacts/dispatch/.
Python Protocols are used for type-safety and documentation only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class SupervisorPort(Protocol):
    """
    What a supervisor must do. COO Agent implements via files.

    File-based communication:
    - Engine writes:  artifacts/terminal/TP_<run_id>.yaml
    - COO writes:     artifacts/supervision/cycle_check_<run_id>.yaml
    - COO writes:     artifacts/supervision/batch_report_<batch>.yaml
    """

    def on_cycle_complete(self, terminal_packet: Path) -> Path:
        """
        Called after each cycle completes.
        Returns path to cycle_check artifact.
        Checks: P0 failures, governance violations, unexpected outcomes.
        """
        ...

    def on_batch_complete(self, batch_id: str, terminal_packets: List[Path]) -> Path:
        """
        Called after a batch of N cycles.
        Returns path to batch_report artifact.
        Analyzes: cross-cycle patterns, failure modes, shadow deltas,
        V2 vs legacy verdict comparison, envelope observations.
        """
        ...

    def check_promotion_criteria(self, batch_id: str) -> Optional[Dict]:
        """
        Mechanical check: are Council V2 promotion criteria met?
        - N cycles with V2 verdict = legacy verdict
        - Challenger rework triggered at least once
        - No false-positive blocks
        Returns PromotionProposal dict if criteria met, else None.
        """
        ...


@runtime_checkable
class CuratorPort(Protocol):
    """Task selection interface. Manual CLI for now; COO Agent later."""

    def select_tasks(self, backlog: Path, batch_size: int) -> List[Dict]:
        """Select tasks from backlog for next batch."""
        ...

    def validate_selection(self, tasks: List[Dict]) -> Dict:
        """
        Check selection criteria: productive, coverage, complexity, breadth, safe scope.
        Returns ValidationResult dict with 'valid' bool and 'issues' list.
        """
        ...
