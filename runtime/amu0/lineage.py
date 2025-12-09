"""
FP-4.x CND-2: Hash-Chained AMU₀ Lineage
Linear hash chain for AMU₀ entries with parent references.
"""
import json
import os
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from runtime.governance.HASH_POLICY_v1 import hash_json, hash_bytes
from runtime.util.atomic_write import atomic_write_json


class LineageError(Exception):
    """Raised when lineage operations fail."""
    pass


@dataclass
class LineageEntry:
    """A single entry in the AMU₀ lineage chain."""
    entry_id: str
    timestamp: str
    parent_hash: Optional[str]
    artefact_hash: str
    attestation: Dict[str, Any]
    state_delta: Dict[str, Any]
    entry_hash: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'LineageEntry':
        return cls(**data)


def compute_entry_hash(entry_data: dict, parent_hash: Optional[str]) -> str:
    """
    Compute deterministic hash for a lineage entry.
    
    Args:
        entry_data: Entry data (without entry_hash).
        parent_hash: Hash of parent entry (None for genesis).
        
    Returns:
        SHA-256 hash of the canonical entry representation.
    """
    # Canonical hash input includes parent_hash explicitly
    hash_input = {
        "parent_hash": parent_hash,
        "timestamp": entry_data.get("timestamp"),
        "artefact_hash": entry_data.get("artefact_hash"),
        "attestation": entry_data.get("attestation"),
        "state_delta": entry_data.get("state_delta"),
        "entry_id": entry_data.get("entry_id")
    }
    return hash_json(hash_input)


class AMU0Lineage:
    """
    Hash-chained AMU₀ lineage manager.
    
    Maintains a strictly linear hash chain where each entry
    references its parent via parent_hash.
    """
    
    def __init__(self, lineage_path: str):
        """
        Initialize lineage manager.
        
        Args:
            lineage_path: Path to the lineage JSON file.
        """
        self.lineage_path = Path(lineage_path)
        self._entries: List[LineageEntry] = []
        
        if self.lineage_path.exists():
            self._load()
    
    def _load(self) -> None:
        """Load existing lineage from file."""
        with open(self.lineage_path, 'r') as f:
            data = json.load(f)
        
        self._entries = [LineageEntry.from_dict(e) for e in data.get("entries", [])]
    
    def _save(self) -> None:
        """Save lineage to file atomically."""
        data = {
            "version": "1.0",
            "entries": [e.to_dict() for e in self._entries]
        }
        atomic_write_json(self.lineage_path, data)
    
    def get_last_entry(self) -> Optional[LineageEntry]:
        """Get the most recent entry in the chain."""
        return self._entries[-1] if self._entries else None
    
    def get_last_hash(self) -> Optional[str]:
        """Get the hash of the most recent entry."""
        last = self.get_last_entry()
        return last.entry_hash if last else None
    
    def append_entry(
        self,
        entry_id: str,
        timestamp: str,
        artefact_hash: str,
        attestation: Dict[str, Any],
        state_delta: Optional[Dict[str, Any]] = None
    ) -> LineageEntry:
        """
        Append a new entry to the lineage chain.
        
        Args:
            entry_id: Unique identifier for this entry.
            timestamp: ISO timestamp (must be explicit, not generated).
            artefact_hash: Hash of the artefact being recorded.
            attestation: Attestation data (e.g., HumanAttestation).
            state_delta: Optional state changes.
            
        Returns:
            The newly created LineageEntry.
        """
        parent_hash = self.get_last_hash()
        
        entry_data = {
            "entry_id": entry_id,
            "timestamp": timestamp,
            "artefact_hash": artefact_hash,
            "attestation": attestation,
            "state_delta": state_delta or {}
        }
        
        entry_hash = compute_entry_hash(entry_data, parent_hash)
        
        entry = LineageEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            parent_hash=parent_hash,
            artefact_hash=artefact_hash,
            attestation=attestation,
            state_delta=state_delta or {},
            entry_hash=entry_hash
        )
        
        self._entries.append(entry)
        self._save()
        
        return entry
    
    def verify_chain(self) -> tuple[bool, List[str]]:
        """
        Verify the entire lineage chain integrity.
        
        Returns:
            Tuple of (is_valid, list of error messages).
        """
        errors = []
        
        for i, entry in enumerate(self._entries):
            expected_parent = self._entries[i - 1].entry_hash if i > 0 else None
            
            # Verify parent_hash matches previous entry
            if entry.parent_hash != expected_parent:
                errors.append(
                    f"Entry {entry.entry_id}: parent_hash mismatch. "
                    f"Expected {expected_parent}, got {entry.parent_hash}"
                )
            
            # Recompute and verify entry_hash
            entry_data = {
                "entry_id": entry.entry_id,
                "timestamp": entry.timestamp,
                "artefact_hash": entry.artefact_hash,
                "attestation": entry.attestation,
                "state_delta": entry.state_delta
            }
            expected_hash = compute_entry_hash(entry_data, entry.parent_hash)
            
            if entry.entry_hash != expected_hash:
                errors.append(
                    f"Entry {entry.entry_id}: entry_hash mismatch. "
                    f"Expected {expected_hash}, got {entry.entry_hash}"
                )
        
        return (len(errors) == 0, errors)
    
    def get_entries(self) -> List[LineageEntry]:
        """Get all entries in the lineage."""
        return self._entries.copy()
    
    def get_entry_by_id(self, entry_id: str) -> Optional[LineageEntry]:
        """Find an entry by its ID."""
        for entry in self._entries:
            if entry.entry_id == entry_id:
                return entry
        return None
