"""
Tier-2 Scenario Harness

Executes one or more named missions via run_mission and returns a single,
deterministic, serialisable result suitable for the future v0.5 Deterministic
Test Harness product.

Features:
- Multi-mission scenario execution
- Deterministic, JSON-serialisable results
- Aggregated metadata with stable hashing
- No I/O, network, subprocess, or time/date access
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Tuple

from runtime.orchestration.engine import ExecutionContext, OrchestrationResult
from runtime.orchestration.registry import run_mission


# =============================================================================
# Data Structures
# =============================================================================

@dataclass(frozen=True)
class MissionCall:
    """
    A single mission call specification.
    
    Attributes:
        name: Mission name (must be registered in MISSION_REGISTRY).
        params: Optional mission parameters.
    """
    name: str
    params: Dict[str, Any] | None = None


@dataclass(frozen=True)
class ScenarioDefinition:
    """
    Declarative description of a Tier-2 scenario.
    
    Attributes:
        scenario_name: Logical identifier for the scenario.
        initial_state: Immutable seed state for ExecutionContext.
        missions: Ordered list of mission calls to execute sequentially.
    """
    scenario_name: str
    initial_state: Mapping[str, Any]
    missions: Tuple[MissionCall, ...] = field(default_factory=tuple)
    
    def __init__(
        self,
        scenario_name: str,
        initial_state: Mapping[str, Any],
        missions: List[MissionCall] | Tuple[MissionCall, ...] = (),
    ):
        # Use object.__setattr__ because frozen=True
        object.__setattr__(self, "scenario_name", scenario_name)
        object.__setattr__(self, "initial_state", initial_state)
        # Convert list to tuple for immutability
        if isinstance(missions, list):
            object.__setattr__(self, "missions", tuple(missions))
        else:
            object.__setattr__(self, "missions", missions)


@dataclass(frozen=True)
class ScenarioResult:
    """
    Aggregated result of a scenario execution.
    
    Attributes:
        scenario_name: Echoed from definition.
        mission_results: Mapping mission_name -> OrchestrationResult.
        metadata: Deterministic metadata (e.g. stable hashes).
    """
    scenario_name: str
    mission_results: Mapping[str, OrchestrationResult]
    metadata: Mapping[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to JSON-serializable dict with stable key ordering.
        
        Returns a dict with: 'scenario_name', 'mission_results', 'metadata'.
        Metadata is deep-copied to ensure immutability.
        """
        return {
            "scenario_name": self.scenario_name,
            "mission_results": {
                name: res.to_dict()
                for name, res in self.mission_results.items()
            },
            "metadata": dict(self.metadata),
        }


# =============================================================================
# Helper Functions
# =============================================================================

def _stable_hash(obj: Any) -> str:
    """
    Compute a deterministic SHA-256 hash of a JSON-serialisable object.
    Uses sorted keys and stable separators.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# =============================================================================
# Public API
# =============================================================================

def run_scenario(defn: ScenarioDefinition) -> ScenarioResult:
    """
    Execute a scenario by running all missions in order.
    
    This function:
    - Constructs a fresh ExecutionContext from defn.initial_state
    - Executes defn.missions in order via run_mission
    - Aggregates results into a ScenarioResult
    - Does not mutate defn.initial_state or any caller-provided mappings
    
    Args:
        defn: The scenario definition to execute.
        
    Returns:
        ScenarioResult with mission results and deterministic metadata.
        
    Raises:
        UnknownMissionError: If any mission name is not registered.
        Any other exceptions from run_mission propagate unchanged.
    """
    # Create a defensive copy of initial_state to ensure immutability
    initial_state_copy = dict(defn.initial_state)
    
    # Execute missions in order
    mission_results: Dict[str, OrchestrationResult] = {}
    
    for mission_call in defn.missions:
        # Create fresh ExecutionContext for each mission
        # (with a copy of initial state to ensure isolation)
        ctx = ExecutionContext(initial_state=copy.deepcopy(initial_state_copy))
        
        # Create defensive copy of params
        params = dict(mission_call.params) if mission_call.params else None
        
        # Execute the mission
        result = run_mission(mission_call.name, ctx, params=params)
        
        # Store result (using mission name as key)
        mission_results[mission_call.name] = result
    
    # Build deterministic metadata
    serialised_results = {
        name: result.to_dict() for name, result in mission_results.items()
    }
    scenario_hash = _stable_hash(serialised_results)
    
    metadata: Dict[str, Any] = {
        "scenario_name": defn.scenario_name,
        "scenario_hash": scenario_hash,
    }
    
    return ScenarioResult(
        scenario_name=defn.scenario_name,
        mission_results=mission_results,
        metadata=metadata,
    )
