"""
Tier-2 Config Adapter

Provides deterministic parsing of pure configuration mappings into Tier-2
dataclasses. Handles validation and type conversion safely without I/O.

Features:
- Generic Mapping -> Dataclass conversion
- Validates required fields and types
- Deterministic error messages via ConfigError
- No I/O, network, or subprocess access
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional, Set, cast

from runtime.orchestration.harness import (
    MissionCall,
    ScenarioDefinition,
)
from runtime.orchestration.suite import (
    ScenarioSuiteDefinition,
)
from runtime.orchestration.expectations import (
    MissionExpectation,
    SuiteExpectationsDefinition,
    ExpectationOp,
)


class ConfigError(ValueError):
    """
    Raised when a configuration mapping is missing required fields
    or has invalid types/values.
    """
    pass


# =============================================================================
# Helper Functions
# =============================================================================

def _require_field(cfg: Mapping[str, Any], field: str) -> Any:
    """Ensure a field exists in the mapping."""
    if field not in cfg:
        raise ConfigError(f"Missing required field '{field}'")
    return cfg[field]


def _require_str(cfg: Mapping[str, Any], field: str) -> str:
    """Ensure a field exists and is a string."""
    val = _require_field(cfg, field)
    if not isinstance(val, str):
        raise ConfigError(f"Field '{field}' must be a string, got {type(val).__name__}")
    return val


def _require_list(cfg: Mapping[str, Any], field: str) -> List[Any]:
    """Ensure a field exists and is a list."""
    val = _require_field(cfg, field)
    if not isinstance(val, list):
        raise ConfigError(f"Field '{field}' must be a list, got {type(val).__name__}")
    return val


def _require_mapping(cfg: Mapping[str, Any], field: str) -> Mapping[str, Any]:
    """Ensure a field exists and is a mapping."""
    val = _require_field(cfg, field)
    if not isinstance(val, (dict, Mapping)):
        raise ConfigError(f"Field '{field}' must be a mapping, got {type(val).__name__}")
    return val


def _optional_mapping(cfg: Mapping[str, Any], field: str) -> Optional[Mapping[str, Any]]:
    """Get an optional field that must be a mapping or None if present."""
    if field not in cfg:
        return None
    val = cfg[field]
    if val is None:
        return None
    if not isinstance(val, (dict, Mapping)):
        raise ConfigError(f"Field '{field}' must be a dict or None, got {type(val).__name__}")
    return cast(Mapping[str, Any], val)


def _require_op(cfg: Mapping[str, Any], field: str) -> ExpectationOp:
    """Ensure field is a valid ExpectationOp."""
    val = _require_str(cfg, field)
    valid_ops: Set[str] = {"eq", "ne", "gt", "lt", "exists"}
    if val not in valid_ops:
        raise ConfigError(f"Invalid value for '{field}': '{val}'. Must be one of {sorted(valid_ops)}")
    return cast(ExpectationOp, val)


# =============================================================================
# Suite Parsing
# =============================================================================

def _parse_mission_call(cfg: Mapping[str, Any]) -> MissionCall:
    """Parse a single mission call configuration."""
    name = _require_str(cfg, "name")
    params = _optional_mapping(cfg, "params")
    
    # params is Mapping, but MissionCall expects Dict | None explicitly in signature?
    # MissionCall: params: Dict[str, Any] | None
    # We convert Mapping to Dict safely if needed (dataclass usually handles it, but explicit is better)
    params_dict = dict(params) if params is not None else None
    
    return MissionCall(name=name, params=params_dict)


def _parse_scenario_def(cfg: Mapping[str, Any]) -> ScenarioDefinition:
    """Parse a single scenario configuration."""
    scenario_name = _require_str(cfg, "scenario_name")
    initial_state_map = _require_mapping(cfg, "initial_state")
    missions_list = _require_list(cfg, "missions")
    
    missions = tuple(_parse_mission_call(m_cfg) for m_cfg in missions_list)
    initial_state = dict(initial_state_map)
    
    return ScenarioDefinition(
        scenario_name=scenario_name,
        initial_state=initial_state,
        missions=missions
    )


def parse_suite_definition(cfg: Mapping[str, Any]) -> ScenarioSuiteDefinition:
    """
    Parse a Mapping into a ScenarioSuiteDefinition.
    
    Expected schema:
    {
        "suite_name": str,
        "scenarios": [
            { "scenario_name": str, "initial_state": dict, "missions": [...] }, 
            ...
        ]
    }
    """
    suite_name = _require_str(cfg, "suite_name")
    scenarios_list = _require_list(cfg, "scenarios")
    
    scenarios = tuple(_parse_scenario_def(s_cfg) for s_cfg in scenarios_list)
    
    return ScenarioSuiteDefinition(
        suite_name=suite_name,
        scenarios=scenarios
    )


# =============================================================================
# Expectations Parsing
# =============================================================================

def _parse_mission_expectation(cfg: Mapping[str, Any]) -> MissionExpectation:
    """Parse a single expectation configuration."""
    id_ = _require_str(cfg, "id")
    scenario_name = _require_str(cfg, "scenario_name")
    mission_name = _require_str(cfg, "mission_name")
    path = _require_str(cfg, "path")
    op = _require_op(cfg, "op")
    
    # expected is optional, defaults to None
    expected = cfg.get("expected")
    
    return MissionExpectation(
        id=id_,
        scenario_name=scenario_name,
        mission_name=mission_name,
        path=path,
        op=op,
        expected=expected
    )


def parse_expectations_definition(cfg: Mapping[str, Any]) -> SuiteExpectationsDefinition:
    """
    Parse a Mapping into a SuiteExpectationsDefinition.
    
    Expected schema:
    {
        "expectations": [
            { "id": str, "scenario_name": str, "mission_name": str, "path": str, "op": str, ... },
            ...
        ]
    }
    """
    expectations_list = _require_list(cfg, "expectations")
    
    expectations = [_parse_mission_expectation(e_cfg) for e_cfg in expectations_list]
    
    return SuiteExpectationsDefinition(expectations=expectations)
