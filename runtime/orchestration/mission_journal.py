"""
Mission Journal - Hash-chained operation logging.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1.1 and §5.8
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .operations import OperationReceipt, canonical_bytes


# Genesis hash for new journals. Per spec §5.1.4
JOURNAL_GENESIS = hashlib.sha256(b"LIFEOS_JOURNAL_GENESIS_V1").hexdigest()


@dataclass
class StepRecord:
    """Record of a step execution. Per spec §5.1.1."""
    step_id: str
    operation_type: str
    status: str  # pending, running, completed, failed, compensated
    started_at: str
    completed_at: Optional[str]
    pre_state_hash: str
    post_state_hash: Optional[str]
    error_message: Optional[str]
    compensation_status: str  # not_needed, pending, completed, failed
    prev_entry_hash: str
    entry_hash: str = ""  # Computed after creation

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for serialization."""
        return asdict(self)


class MissionJournal:
    """
    Append-only hash-chained journal for mission execution.
    
    Per spec §5.1.1 and §5.8 (Evidence Integrity).
    """
    
    def __init__(self, mission_id: str, output_dir: Optional[Path] = None):
        self.mission_id = mission_id
        self.output_dir = output_dir
        self._prev_hash: str = JOURNAL_GENESIS
        self._entries: List[StepRecord] = []
        self._receipts: List[OperationReceipt] = []
    
    def _compute_entry_hash(self, record: StepRecord) -> str:
        """Compute SHA256 hash of entry including prev_entry_hash."""
        record_dict = record.to_dict()
        record_dict.pop("entry_hash", None)
        content = canonical_bytes(record_dict)
        return f"sha256:{hashlib.sha256(content).hexdigest()}"
    
    def record_step(
        self,
        step_id: str,
        operation_type: str,
        status: str = "running",
        pre_state_hash: str = "",
        error_message: Optional[str] = None,
        compensation_status: str = "not_needed",
    ) -> StepRecord:
        """
        Record a step execution in the journal.
        
        Returns the recorded entry with computed hash.
        """
        record = StepRecord(
            step_id=step_id,
            operation_type=operation_type,
            status=status,
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=None,
            pre_state_hash=pre_state_hash,
            post_state_hash=None,
            error_message=error_message,
            compensation_status=compensation_status,
            prev_entry_hash=self._prev_hash,
        )
        
        record.entry_hash = self._compute_entry_hash(record)
        self._prev_hash = record.entry_hash
        self._entries.append(record)
        
        return record
    
    def complete_step(
        self,
        step_id: str,
        status: str,
        post_state_hash: str = "",
        error_message: Optional[str] = None,
        compensation_status: str = "not_needed",
    ) -> Optional[StepRecord]:
        """Update a step to completed status."""
        for entry in reversed(self._entries):
            if entry.step_id == step_id:
                entry.status = status
                entry.completed_at = datetime.now(timezone.utc).isoformat()
                entry.post_state_hash = post_state_hash
                entry.error_message = error_message
                entry.compensation_status = compensation_status
                # Re-compute hash after modification
                entry.entry_hash = self._compute_entry_hash(entry)
                return entry
        return None
    
    def record_operation(self, receipt: OperationReceipt) -> None:
        """Record an operation receipt."""
        self._receipts.append(receipt)
    
    def get_chain_root(self) -> str:
        """Return current chain tip hash."""
        return self._prev_hash
    
    def verify_integrity(self) -> Tuple[bool, List[str]]:
        """
        Verify integrity of the journal chain.
        
        Returns:
            (is_valid, list_of_breaks)
        """
        breaks = []
        expected_prev = JOURNAL_GENESIS
        
        for i, entry in enumerate(self._entries):
            if entry.prev_entry_hash != expected_prev:
                breaks.append(
                    f"Entry {i} ({entry.step_id}): expected prev_entry_hash="
                    f"{expected_prev[:16]}..., got {entry.prev_entry_hash[:16]}..."
                )
            
            computed = self._compute_entry_hash(entry)
            if entry.entry_hash != computed:
                breaks.append(
                    f"Entry {i} ({entry.step_id}): entry_hash mismatch. "
                    f"Stored={entry.entry_hash[:16]}..., computed={computed[:16]}..."
                )
            
            expected_prev = entry.entry_hash
        
        return len(breaks) == 0, breaks
    
    @property
    def entries(self) -> List[StepRecord]:
        """Return all step entries."""
        return list(self._entries)
    
    @property
    def receipts(self) -> List[OperationReceipt]:
        """Return all operation receipts."""
        return list(self._receipts)
    
    def export_bundle(self) -> Dict[str, Any]:
        """
        Export journal as completion bundle. Per spec §5.8.
        
        Returns dict suitable for writing to JSON.
        """
        return {
            "mission_id": self.mission_id,
            "chain_root": self.get_chain_root(),
            "genesis": JOURNAL_GENESIS,
            "entries": [e.to_dict() for e in self._entries],
            "receipts": [r.to_dict() for r in self._receipts],
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
