"""
Mission Registry v0.1 — Boundaries

Exceptions, validation, and configuration for mission registry.
All exceptions subclass AntiFailureViolation from runtime.errors.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from runtime.errors import AntiFailureViolation

if TYPE_CHECKING:
    from runtime.mission.interfaces import MissionId, MissionDefinition


# =============================================================================
# Exceptions
# =============================================================================

class MissionBoundaryViolation(AntiFailureViolation):
    """
    Raised when a mission definition or ID violates boundaries.
    
    Input validation failure for mission operations.
    """
    pass


class MissionNotFoundError(AntiFailureViolation):
    """
    Raised when a mission ID is not found in the registry.
    """
    pass


class MissionConflictError(AntiFailureViolation):
    """
    Raised when registering a mission with a duplicate ID.
    """
    pass


# =============================================================================
# Configuration
# =============================================================================

@dataclass(frozen=True)
class MissionBoundaryConfig:
    """
    Immutable configuration for mission boundaries.
    
    All defaults are deterministic.
    """
    max_id_chars: int = 12
    max_name_chars: int = 100
    max_description_chars: int = 1000  # Reduced from 4000 to be safe/strict
    max_tags: int = 10                 # Reduced from 25 to match Cycle 1-9 tests
    max_tag_chars: int = 64
    max_metadata_pairs: int = 50
    max_metadata_key_chars: int = 64
    max_metadata_value_chars: int = 1000
    max_missions: int = 1000


# =============================================================================
# Validation
# =============================================================================

def validate_mission_id(
    mid: "MissionId",
    config: MissionBoundaryConfig | None = None,
) -> None:
    """
    Validate a mission ID against boundary config.
    
    Raises MissionBoundaryViolation on violations.
    """
    if config is None:
        config = MissionBoundaryConfig()
    
    # ID value: must not be empty
    if not mid.value or len(mid.value.strip()) == 0:
        raise MissionBoundaryViolation("mission id must not be empty")
        
    # ID value: length check
    if len(mid.value) > config.max_id_chars:
        raise MissionBoundaryViolation(
            f"Mission ID exceeds max length of {config.max_id_chars}"
        )


def validate_mission_definition(
    defn: "MissionDefinition",
    config: MissionBoundaryConfig | None = None,
) -> None:
    """
    Validate a mission definition against boundary config.
    
    Raises MissionBoundaryViolation on violations.
    """
    if config is None:
        config = MissionBoundaryConfig()
    
    # Validate ID
    validate_mission_id(defn.id, config)
    
    # Name: must not be empty
    if not defn.name or len(defn.name.strip()) == 0:
        raise MissionBoundaryViolation("name must not be empty")
    
    # Name: length check
    if len(defn.name) > config.max_name_chars:
        raise MissionBoundaryViolation(
            f"name exceeds {config.max_name_chars} chars"
        )
    
    # Description: length check
    if len(defn.description) > config.max_description_chars:
        raise MissionBoundaryViolation(
            f"description exceeds {config.max_description_chars} chars"
        )
    
    # Tags: type check (must be tuple)
    if not isinstance(defn.tags, tuple):
        raise MissionBoundaryViolation(
            f"tags must be tuple, got {type(defn.tags).__name__}"
        )
    
    # Tags: count check
    if len(defn.tags) > config.max_tags:
        raise MissionBoundaryViolation(
            f"too many tags: {len(defn.tags)} > {config.max_tags}"
        )
    
    # Tags: individual type and length check
    for i, tag in enumerate(defn.tags):
        if not isinstance(tag, str):
            raise MissionBoundaryViolation(
                f"tag[{i}] must be str, got {type(tag).__name__}"
            )
        if len(tag) > config.max_tag_chars:
            raise MissionBoundaryViolation(
                f"tag[{i}] exceeds {config.max_tag_chars} chars"
            )
    
    # Metadata: type check (must be tuple of tuples)
    if not isinstance(defn.metadata, tuple):
        raise MissionBoundaryViolation(
            f"metadata must be tuple, got {type(defn.metadata).__name__}"
        )
    
    # Metadata: count check
    if len(defn.metadata) > config.max_metadata_pairs:
        raise MissionBoundaryViolation(
            f"too many metadata pairs: {len(defn.metadata)} > {config.max_metadata_pairs}"
        )
    
    # Metadata: individual validation
    for i, pair in enumerate(defn.metadata):
        if not isinstance(pair, tuple) or len(pair) != 2:
            raise MissionBoundaryViolation(
                f"metadata[{i}] must be (key, value) tuple"
            )
        key, value = pair
        if not isinstance(key, str):
            raise MissionBoundaryViolation(
                f"metadata[{i}] key must be str, got {type(key).__name__}"
            )
        if not isinstance(value, str):
            raise MissionBoundaryViolation(
                f"metadata[{i}] value must be str, got {type(value).__name__}"
            )
        if len(key) > config.max_metadata_key_chars:
            raise MissionBoundaryViolation(
                f"metadata[{i}] key exceeds {config.max_metadata_key_chars} chars"
            )
        if len(value) > config.max_metadata_value_chars:
            raise MissionBoundaryViolation(
                f"metadata[{i}] value exceeds {config.max_metadata_value_chars} chars"
            )
