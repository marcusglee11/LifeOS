"""
Phase 3 Mission Types - Package

Implements mission types per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3:
- design: Transform task spec into BUILD_PACKET
- review: Run council review on a packet
- build: Invoke builder with approved BUILD_PACKET
- steward: Commit approved changes
- autonomous_build_cycle: Deprecated for new runs (kept for compatibility/testing)

All missions:
- Are deterministic (pure functions of inputs + state)
- Return MissionResult with structured outputs
- Support rollback via compensation actions
- Integrate with existing Tier-2 orchestration
"""

from __future__ import annotations

from runtime.orchestration.missions.autonomous_build_cycle import AutonomousBuildCycleMission
from runtime.orchestration.missions.base import (
    MissionContext,
    MissionError,
    MissionResult,
    MissionType,
    MissionValidationError,
)
from runtime.orchestration.missions.build import BuildMission
from runtime.orchestration.missions.build_with_validation import BuildWithValidationMission
from runtime.orchestration.missions.design import DesignMission
from runtime.orchestration.missions.echo import EchoMission
from runtime.orchestration.missions.noop import NoopMission
from runtime.orchestration.missions.review import ReviewMission
from runtime.orchestration.missions.schema import (
    MissionSchemaError,
    load_mission_schema,
    validate_mission_definition,
)
from runtime.orchestration.missions.steward import StewardMission

# Mission type registry - maps type string to implementation class
MISSION_TYPES = {
    MissionType.DESIGN: DesignMission,
    MissionType.REVIEW: ReviewMission,
    MissionType.BUILD: BuildMission,
    MissionType.BUILD_WITH_VALIDATION: BuildWithValidationMission,
    MissionType.STEWARD: StewardMission,
    MissionType.AUTONOMOUS_BUILD_CYCLE: AutonomousBuildCycleMission,
    MissionType.ECHO: EchoMission,
    MissionType.NOOP: NoopMission,
}


def get_mission_class(mission_type: str):
    """
    Get mission implementation class by type string.

    Fail-closed: Raises MissionError if type is unknown.
    """
    try:
        mt = MissionType(mission_type)
    except ValueError as exc:
        valid = sorted([t.value for t in MissionType])
        raise MissionError(f"Unknown mission type: '{mission_type}'. Valid types: {valid}") from exc
    return MISSION_TYPES[mt]


__all__ = [
    # Types
    "MissionType",
    "MissionResult",
    "MissionContext",
    # Exceptions
    "MissionError",
    "MissionValidationError",
    "MissionSchemaError",
    # Mission classes
    "DesignMission",
    "ReviewMission",
    "BuildMission",
    "BuildWithValidationMission",
    "StewardMission",
    "AutonomousBuildCycleMission",
    "EchoMission",
    "NoopMission",
    # Registry
    "MISSION_TYPES",
    "get_mission_class",
    # Schema
    "validate_mission_definition",
    "load_mission_schema",
]
