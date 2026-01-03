"""
Mission Registry v0.1 — Package

Tier-3 definition-only mission registry. No execution, I/O, or side effects.

Public API:
    - MissionId, MissionDefinition, MissionRegistryState (data types)
    - MissionRegistry (immutable registry class)
    - MissionBoundaryViolation, MissionNotFoundError, MissionConflictError (exceptions)
    - MissionBoundaryConfig (validation configuration)
    - canonical_json, state_hash (canonicalization functions)
"""
from runtime.api import TIER3_MISSION_REGISTRY_VERSION

from runtime.mission.interfaces import (
    MissionId,
    MissionDefinition,
    MissionRegistryState,
    canonical_json,
    state_hash,
)
from runtime.mission.boundaries import (
    MissionBoundaryViolation,
    MissionNotFoundError,
    MissionConflictError,
    MissionBoundaryConfig,
    validate_mission_id,
    validate_mission_definition,
)
from runtime.mission.registry import MissionRegistry

__version__ = TIER3_MISSION_REGISTRY_VERSION

__all__ = [
    # Version
    "__version__",
    "TIER3_MISSION_REGISTRY_VERSION",
    # Data types
    "MissionId",
    "MissionDefinition",
    "MissionRegistryState",
    # Registry
    "MissionRegistry",
    # Exceptions
    "MissionBoundaryViolation",
    "MissionNotFoundError",
    "MissionConflictError",
    # Configuration
    "MissionBoundaryConfig",
    # Validation
    "validate_mission_id",
    "validate_mission_definition",
    # Canonicalization
    "canonical_json",
    "state_hash",
]
