"""CEO Approval Queue for exception-based human-in-the-loop governance.

This module provides a persistent queue for escalations that require
CEO approval before the autonomous loop can proceed.
"""

import json
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class EscalationStatus(str, Enum):
    """Status of an escalation entry."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


class EscalationType(str, Enum):
    """Type of escalation requiring CEO approval."""
    GOVERNANCE_SURFACE_TOUCH = "governance_surface_touch"
    BUDGET_ESCALATION = "budget_escalation"
    PROTECTED_PATH_MODIFICATION = "protected_path_modification"
    AMBIGUOUS_TASK = "ambiguous_task"
    POLICY_VIOLATION = "policy_violation"


@dataclass
class EscalationEntry:
    """An escalation entry in the CEO queue."""
    type: EscalationType
    context: Dict[str, Any]
    run_id: str
    id: Optional[str] = None
    status: EscalationStatus = EscalationStatus.PENDING
    created_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_note: Optional[str] = None
    resolver: Optional[str] = None


class CEOQueue:
    """Persistent queue for CEO approval escalations."""

    def __init__(self, db_path: Path):
        """Initialize the queue with a SQLite database.

        Args:
            db_path: Path to the SQLite database file
        """
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        """Create tables if they don't exist."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS escalations (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    context TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    resolution_note TEXT,
                    resolver TEXT
                )
            """)
            conn.commit()

    def _generate_id(self) -> str:
        """Generate a unique escalation ID in ESC-XXXX format.

        Returns:
            A unique escalation ID
        """
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM escalations"
            )
            count = cursor.fetchone()[0]
        return f"ESC-{count + 1:04d}"

    def add_escalation(self, entry: EscalationEntry) -> str:
        """Add a new escalation to the queue.

        Args:
            entry: The escalation entry to add

        Returns:
            The generated escalation ID
        """
        # Generate ID if not provided
        if entry.id is None:
            entry.id = self._generate_id()

        # Set created_at if not provided
        if entry.created_at is None:
            entry.created_at = datetime.utcnow()

        # Ensure status is PENDING for new entries
        if entry.status != EscalationStatus.PENDING:
            entry.status = EscalationStatus.PENDING

        # Serialize context to JSON
        context_json = json.dumps(entry.context)

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO escalations
                (id, type, status, context, run_id, created_at, resolved_at, resolution_note, resolver)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.id,
                    entry.type.value,
                    entry.status.value,
                    context_json,
                    entry.run_id,
                    entry.created_at.isoformat(),
                    None,
                    None,
                    None,
                ),
            )
            conn.commit()

        return entry.id

    def get_pending(self) -> List[EscalationEntry]:
        """Get all pending escalations.

        Returns:
            List of pending escalation entries, ordered by created_at ascending
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM escalations
                WHERE status = ?
                ORDER BY created_at ASC
                """,
                (EscalationStatus.PENDING.value,),
            )
            rows = cursor.fetchall()

        return [self._row_to_entry(row) for row in rows]

    def get_by_id(self, escalation_id: str) -> Optional[EscalationEntry]:
        """Get an escalation by ID.

        Args:
            escalation_id: The escalation ID to retrieve

        Returns:
            The escalation entry, or None if not found
        """
        with sqlite3.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM escalations WHERE id = ?",
                (escalation_id,),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return self._row_to_entry(row)

    def approve(
        self, escalation_id: str, note: str, resolver: str
    ) -> bool:
        """Approve an escalation.

        Args:
            escalation_id: The escalation ID to approve
            note: Approval note/context
            resolver: Who approved (e.g., "CEO")

        Returns:
            True if approved successfully, False if not found or not pending
        """
        # Check if entry exists and is pending
        entry = self.get_by_id(escalation_id)
        if entry is None or entry.status != EscalationStatus.PENDING:
            return False

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                UPDATE escalations
                SET status = ?, resolved_at = ?, resolution_note = ?, resolver = ?
                WHERE id = ?
                """,
                (
                    EscalationStatus.APPROVED.value,
                    datetime.utcnow().isoformat(),
                    note,
                    resolver,
                    escalation_id,
                ),
            )
            conn.commit()

        return True

    def reject(
        self, escalation_id: str, reason: str, resolver: str
    ) -> bool:
        """Reject an escalation.

        Args:
            escalation_id: The escalation ID to reject
            reason: Rejection reason
            resolver: Who rejected (e.g., "CEO")

        Returns:
            True if rejected successfully, False if not found or not pending
        """
        # Check if entry exists and is pending
        entry = self.get_by_id(escalation_id)
        if entry is None or entry.status != EscalationStatus.PENDING:
            return False

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                UPDATE escalations
                SET status = ?, resolved_at = ?, resolution_note = ?, resolver = ?
                WHERE id = ?
                """,
                (
                    EscalationStatus.REJECTED.value,
                    datetime.utcnow().isoformat(),
                    reason,
                    resolver,
                    escalation_id,
                ),
            )
            conn.commit()

        return True

    def mark_timeout(self, escalation_id: str) -> bool:
        """Mark an escalation as timed out.

        Args:
            escalation_id: The escalation ID to mark as timed out

        Returns:
            True if marked successfully, False if not found
        """
        # Check if entry exists
        entry = self.get_by_id(escalation_id)
        if entry is None:
            return False

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                UPDATE escalations
                SET status = ?, resolved_at = ?, resolution_note = ?
                WHERE id = ?
                """,
                (
                    EscalationStatus.TIMEOUT.value,
                    datetime.utcnow().isoformat(),
                    "TIMEOUT_24H",
                    escalation_id,
                ),
            )
            conn.commit()

        return True

    def _row_to_entry(self, row: sqlite3.Row) -> EscalationEntry:
        """Convert a database row to an EscalationEntry.

        Args:
            row: SQLite row object

        Returns:
            EscalationEntry instance
        """
        return EscalationEntry(
            id=row["id"],
            type=EscalationType(row["type"]),
            status=EscalationStatus(row["status"]),
            context=json.loads(row["context"]),
            run_id=row["run_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            resolved_at=(
                datetime.fromisoformat(row["resolved_at"])
                if row["resolved_at"]
                else None
            ),
            resolution_note=row["resolution_note"],
            resolver=row["resolver"],
        )
