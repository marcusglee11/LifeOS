"""
Mission Registry v0.1/v0.2 — Package

Tier-3 definition-only mission registry. No execution, I/O, or side effects.

Public API:
    v0.1:
    - MissionId, MissionDefinition, MissionRegistryState (data types)
    - MissionRegistry (immutable registry class)
    - MissionBoundaryViolation, MissionNotFoundError, MissionConflictError (exceptions)
    - MissionBoundaryConfig (validation configuration)
    - canonical_json, state_hash (canonicalization functions)
    
    v0.2:
    - MissionSynthesisRequest (structured synthesis input)
    - synthesize_mission (synthesis entrypoint)
    - synthesize_mission (synthesis entrypoint)
    - validate_mission_definition_v0_2 (explicit validation entrypoint)
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

# v0.2 synthesis API
from runtime.mission.synthesis import (
    MissionSynthesisRequest,
    synthesize_mission,
    MissionSynthesisRequest,
    synthesize_mission,
    validate_mission_definition_v0_2,
)

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
    # Validation (v0.1)
    "validate_mission_id",
    "validate_mission_definition",
    # Canonicalization
    "canonical_json",
    "state_hash",
    # v0.2 Synthesis API
    "MissionSynthesisRequest",
    "synthesize_mission",
    "MissionSynthesisRequest",
    "synthesize_mission",
    "validate_mission_definition_v0_2",
]

