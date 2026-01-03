"""
Mission Registry v0.1 — Interfaces

Pure data types and canonicalization functions for mission definitions.
No I/O, no side effects, deterministic.

**Scope**: Definition-only. Registry/Executor logic is separate.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from runtime.api import TIER3_MISSION_REGISTRY_VERSION


@dataclass(frozen=True)
class MissionId:
    """
    Immutable mission identifier.
    
    Must be non-empty and contain non-whitespace characters.
    """
    value: str
    
    def __lt__(self, other: "MissionId") -> bool:
        """Enable sorting by value."""
        if not isinstance(other, MissionId):
            return NotImplemented
        return self.value < other.value


@dataclass(frozen=True)
class MissionDefinition:
    """
    Immutable mission definition.
    
    Tags: Order-significant, case-sensitive, no deduplication.
    Metadata: Tuple of key-value pairs; canonicalized by key sort in to_dict().
    """
    id: MissionId
    name: str
    description: str = ""
    tags: Tuple[str, ...] = field(default_factory=tuple)
    metadata: Tuple[Tuple[str, str], ...] = field(default_factory=tuple)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to JSON-serializable dict.
        
        Metadata is sorted by key for canonical representation.
        Tags preserve their original order (order-significant policy).
        """
        return {
            "id": self.id.value,
            "name": self.name,
            "description": self.description,
            "tags": list(self.tags),
            "metadata": dict(sorted(self.metadata)),  # Sort by key
        }

    @classmethod
    def create(
        cls,
        id: str,
        name: str,
        goal: str,
        tags: list[str] = None,
        metadata: dict[str, Any] = None
    ) -> 'MissionDefinition':
        """
        Factory method to create a MissionDefinition.
        
        - Helper for tags/metadata conversion (list->tuple, dict->tuple)
        - Can include pre-validation or normalization logic
        """
        safe_tags = tuple(tags) if tags else ()
        
        safe_metadata = ()
        if metadata:
            # Validate JSON serializability (B2)
            try:
                json.dumps(metadata)
            except (TypeError, OverflowError) as e:
                raise ValueError(f"Metadata must be JSON serializable: {e}")

            sorted_items = sorted(metadata.items(), key=lambda x: x[0])
            safe_metadata = tuple(sorted_items)
            
        return cls(
            id=MissionId(id),
            name=name,
            description=goal,  # Map goal->description
            tags=safe_tags,
            metadata=safe_metadata
        )


@dataclass(frozen=True)
class MissionRegistryState:
    """
    Immutable snapshot of registry state.
    
    Missions are sorted by MissionId.value for canonical representation.
    """
    missions: Tuple[MissionDefinition, ...]
    version: str = TIER3_MISSION_REGISTRY_VERSION
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to JSON-serializable dict.
        
        Missions are already sorted by MissionId.value when constructing state.
        """
        return {
            "version": self.version,
            "missions": [m.to_dict() for m in self.missions],
        }


def canonical_json(state: MissionRegistryState) -> str:
    """
    Produce deterministic canonical JSON representation.
    
    Pinned settings:
    - sort_keys=True
    - separators=(",", ":")
    - ensure_ascii=False
    - allow_nan=False
    """
    return json.dumps(
        state.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def state_hash(state: MissionRegistryState) -> str:
    """
    Compute SHA256 hash of canonical JSON representation.
    
    Returns 64-char hex string.
    """
    return hashlib.sha256(canonical_json(state).encode("utf-8")).hexdigest()
