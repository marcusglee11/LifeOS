"""
Tier-2 Scenario Suite Runner

Runs multiple scenarios (each defined via the Scenario Harness) and aggregates
their ScenarioResults into a deterministic, JSON-serialisable suite-level result.

Features:
- Multi-scenario suite execution
- Deterministic, JSON-serialisable results
- Aggregated metadata with stable suite hashing
- No I/O, network, subprocess, or time/date access
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Tuple

from runtime.orchestration.harness import (
    ScenarioDefinition,
    ScenarioResult,
    run_scenario,
)


# =============================================================================
# Data Structures
# =============================================================================

@dataclass(frozen=True)
class ScenarioSuiteDefinition:
    """
    Declarative description of a Tier-2 scenario suite.
    
    Attributes:
        suite_name: Logical identifier for the suite.
        scenarios: Ordered list of ScenarioDefinition objects to run.
    """
    suite_name: str
    scenarios: Tuple[ScenarioDefinition, ...] = field(default_factory=tuple)
    
    def __init__(
        self,
        suite_name: str,
        scenarios: List[ScenarioDefinition] | Tuple[ScenarioDefinition, ...] = (),
    ):
        # Use object.__setattr__ because frozen=True
        object.__setattr__(self, "suite_name", suite_name)
        # Convert list to tuple for immutability
        if isinstance(scenarios, list):
            object.__setattr__(self, "scenarios", tuple(scenarios))
        else:
            object.__setattr__(self, "scenarios", scenarios)


@dataclass(frozen=True)
class ScenarioSuiteResult:
    """
    Aggregated result for a scenario suite.
    
    Attributes:
        suite_name: Echoed from definition.
        scenario_results: Mapping scenario_name -> ScenarioResult.
        metadata: Deterministic, JSON-serialisable metadata.
    """
    suite_name: str
    scenario_results: Mapping[str, ScenarioResult]
    metadata: Mapping[str, Any]


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

def run_suite(defn: ScenarioSuiteDefinition) -> ScenarioSuiteResult:
    """
    Execute a scenario suite by running all scenarios in order.
    
    This function:
    - Iterates over defn.scenarios in order
    - Calls run_scenario for each ScenarioDefinition
    - Aggregates results into a ScenarioSuiteResult
    - Does not mutate defn.scenarios or any scenario's initial_state
    
    Args:
        defn: The suite definition to execute.
        
    Returns:
        ScenarioSuiteResult with scenario results and deterministic metadata.
        
    Raises:
        UnknownMissionError: If any scenario contains an unknown mission.
        Any other exceptions from run_scenario propagate unchanged.
        
    Note:
        If multiple scenarios share the same scenario_name, the last result wins.
        This is deterministic but implicit; consider using unique names.
    """
    # Execute scenarios in order
    scenario_results: Dict[str, ScenarioResult] = {}
    
    for scenario_def in defn.scenarios:
        # run_scenario already handles immutability of initial_state
        result = run_scenario(scenario_def)
        
        # Store result (using scenario name as key)
        # If duplicate names exist, last-write wins (deterministic)
        scenario_results[scenario_def.scenario_name] = result
    
    # Build deterministic metadata
    serialised_scenarios: Dict[str, Any] = {
        name: {
            "scenario_name": res.scenario_name,
            "mission_results": {
                m_name: m_res.to_dict()
                for m_name, m_res in res.mission_results.items()
            },
            "metadata": res.metadata,
        }
        for name, res in scenario_results.items()
    }
    
    suite_hash = _stable_hash(serialised_scenarios)
    
    metadata: Dict[str, Any] = {
        "suite_name": defn.suite_name,
        "suite_hash": suite_hash,
    }
    
    return ScenarioSuiteResult(
        suite_name=defn.suite_name,
        scenario_results=scenario_results,
        metadata=metadata,
    )
