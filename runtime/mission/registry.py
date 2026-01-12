"""
Mission Registry v0.1 — Registry

Immutable, pure registry class for mission definitions.
No I/O, no side effects, deterministic.

Operations return new registry instances; original is unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple

from runtime.mission.interfaces import (
    MissionId,
    MissionDefinition,
    MissionRegistryState,
)
from runtime.mission.boundaries import (
    MissionBoundaryViolation,
    MissionNotFoundError,
    MissionConflictError,
    MissionBoundaryConfig,
    validate_mission_definition,
)


@dataclass(frozen=True)
class MissionRegistry:
    """
    Immutable registry for mission definitions.
    
    All operations return new registry instances; the original is never mutated.
    
    Ordering:
    - list() returns missions in insertion order
    - to_state() returns missions sorted by MissionId.value (canonical)
    """
    _missions: Tuple[MissionDefinition, ...] = field(default_factory=tuple)
    _config: MissionBoundaryConfig = field(default_factory=MissionBoundaryConfig)
    
    def register(self, defn: MissionDefinition) -> "MissionRegistry":
        """
        Register a new mission definition.
        
        Args:
            defn: The mission definition to register.
            
        Returns:
            New registry instance with the mission added.
            
        Raises:
            MissionBoundaryViolation: If definition fails validation.
            MissionConflictError: If a mission with the same ID already exists.
        """
        # Validate
        validate_mission_definition(defn, self._config)
        
        # Check for conflict
        for existing in self._missions:
            if existing.id.value == defn.id.value:
                raise MissionConflictError(
                    f"mission with id '{defn.id.value}' already exists"
                )
        
        # Check capacity
        if len(self._missions) >= self._config.max_missions:
            raise MissionBoundaryViolation(
                f"registry at capacity: {len(self._missions)} >= {self._config.max_missions}"
            )
        
        # Return new registry with mission appended (insertion order preserved)
        return MissionRegistry(
            _missions=self._missions + (defn,),
            _config=self._config,
        )
    
    def get(self, mid: MissionId) -> MissionDefinition:
        """
        Retrieve a mission definition by ID.
        
        Args:
            mid: The mission ID to look up.
            
        Returns:
            The mission definition.
            
        Raises:
            MissionNotFoundError: If no mission with the ID exists.
        """
        for mission in self._missions:
            if mission.id.value == mid.value:
                return mission
        raise MissionNotFoundError(f"mission with id '{mid.value}' not found")
    
    def list(self) -> Tuple[MissionDefinition, ...]:
        """
        List all missions in insertion order.
        
        Returns:
            Tuple of mission definitions in the order they were registered.
        """
        return self._missions
    
    def update(self, defn: MissionDefinition) -> "MissionRegistry":
        """
        Update an existing mission definition.
        
        Args:
            defn: The updated mission definition (must have existing ID).
            
        Returns:
            New registry instance with the mission updated.
            
        Raises:
            MissionBoundaryViolation: If definition fails validation.
            MissionNotFoundError: If no mission with the ID exists.
        """
        # Validate
        validate_mission_definition(defn, self._config)
        
        # Find and replace
        found = False
        new_missions = []
        for existing in self._missions:
            if existing.id.value == defn.id.value:
                new_missions.append(defn)
                found = True
            else:
                new_missions.append(existing)
        
        if not found:
            raise MissionNotFoundError(f"mission with id '{defn.id.value}' not found")
        
        return MissionRegistry(
            _missions=tuple(new_missions),
            _config=self._config,
        )
    
    def remove(self, mid: MissionId) -> "MissionRegistry":
        """
        Remove a mission by ID.
        
        Args:
            mid: The mission ID to remove.
            
        Returns:
            New registry instance without the mission.
            
        Raises:
            MissionNotFoundError: If no mission with the ID exists.
        """
        found = False
        new_missions = []
        for existing in self._missions:
            if existing.id.value == mid.value:
                found = True
            else:
                new_missions.append(existing)
        
        if not found:
            raise MissionNotFoundError(f"mission with id '{mid.value}' not found")
        
        return MissionRegistry(
            _missions=tuple(new_missions),
            _config=self._config,
        )
    
    def to_state(self) -> MissionRegistryState:
        """
        Convert to canonical registry state.
        
        Missions are sorted by MissionId.value for deterministic representation.
        
        Returns:
            MissionRegistryState with sorted missions.
        """
        sorted_missions = tuple(sorted(self._missions, key=lambda m: m.id.value))
        return MissionRegistryState(missions=sorted_missions)
    
    def __len__(self) -> int:
        """Return the number of missions in the registry."""
        return len(self._missions)
