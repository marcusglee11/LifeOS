# runtime/tests/test_tier2_config_adapter.py
"""
TDD Tests for Tier-2 Config Adapter.

These tests define the contract for parsing generic config mappings into
Tier-2 definitions (ScenarioSuiteDefinition, SuiteExpectationsDefinition).
"""
import copy
from typing import Any, Dict

import pytest

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
)
from runtime.orchestration.config_adapter import (
    ConfigError,
    parse_suite_definition,
    parse_expectations_definition,
)


@pytest.fixture
def valid_suite_config() -> Dict[str, Any]:
    return {
        "suite_name": "smoke_suite",
        "scenarios": [
            {
                "scenario_name": "basic_scenario",
                "initial_state": {"counter": 0},
                "missions": [
                    {
                        "name": "daily_loop",
                        "params": None
                    },
                    {
                        "name": "echo",
                        "params": {"message": "hello"}
                    }
                ]
            }
        ]
    }


@pytest.fixture
def valid_expectations_config() -> Dict[str, Any]:
    return {
        "expectations": [
            {
                "id": "e1",
                "scenario_name": "basic_scenario",
                "mission_name": "daily_loop",
                "path": "success",
                "op": "eq",
                "expected": True
            },
            {
                "id": "e2",
                "scenario_name": "basic_scenario",
                "mission_name": "echo",
                "path": "output.message",
                "op": "exists"
            }
        ]
    }


# =============================================================================
# Helper Functions
# =============================================================================

def _assert_dicts_equal(d1: Dict[str, Any], d2: Dict[str, Any]):
    """Helper to compare dicts for identity checks."""
    assert d1 == d2


# =============================================================================
# Suite Parsing Tests
# =============================================================================

def test_parse_suite_success(valid_suite_config):
    """
    Verify happy-path parsing of a suite definition.
    """
    result = parse_suite_definition(valid_suite_config)
    
    assert isinstance(result, ScenarioSuiteDefinition)
    assert result.suite_name == "smoke_suite"
    assert len(result.scenarios) == 1
    
    scenario = result.scenarios[0]
    assert isinstance(scenario, ScenarioDefinition)
    assert scenario.scenario_name == "basic_scenario"
    assert scenario.initial_state == {"counter": 0}
    
    assert len(scenario.missions) == 2
    m1 = scenario.missions[0]
    assert isinstance(m1, MissionCall)
    assert m1.name == "daily_loop"
    assert m1.params is None
    
    m2 = scenario.missions[1]
    assert m2.name == "echo"
    assert m2.params == {"message": "hello"}


def test_parse_suite_missing_fields(valid_suite_config):
    """
    Verify error raised when required fields are missing.
    """
    # Missing suite_name
    bad_cfg = copy.deepcopy(valid_suite_config)
    del bad_cfg["suite_name"]
    with pytest.raises(ConfigError, match="Missing required field 'suite_name'"):
        parse_suite_definition(bad_cfg)
        
    # Missing scenarios
    bad_cfg = copy.deepcopy(valid_suite_config)
    del bad_cfg["scenarios"]
    with pytest.raises(ConfigError, match="Missing required field 'scenarios'"):
        parse_suite_definition(bad_cfg)
        
    # Scenario missing fields
    bad_cfg = copy.deepcopy(valid_suite_config)
    del bad_cfg["scenarios"][0]["scenario_name"]
    with pytest.raises(ConfigError, match="Missing required field 'scenario_name'"):
        parse_suite_definition(bad_cfg)


def test_parse_suite_invalid_types(valid_suite_config):
    """
    Verify error raised when fields have wrong types.
    """
    # Scenarios not a list
    bad_cfg = copy.deepcopy(valid_suite_config)
    bad_cfg["scenarios"] = "not_a_list"
    with pytest.raises(ConfigError, match="Field 'scenarios' must be a list"):
        parse_suite_definition(bad_cfg)
        
    # Mission params not a dict/None
    bad_cfg = copy.deepcopy(valid_suite_config)
    bad_cfg["scenarios"][0]["missions"][0]["params"] = "invalid_params"
    with pytest.raises(ConfigError, match="Field 'params' must be a dict or None"):
        parse_suite_definition(bad_cfg)


# =============================================================================
# Expectations Parsing Tests
# =============================================================================

def test_parse_expectations_success(valid_expectations_config):
    """
    Verify happy-path parsing of expectations definition.
    """
    result = parse_expectations_definition(valid_expectations_config)
    
    assert isinstance(result, SuiteExpectationsDefinition)
    assert len(result.expectations) == 2
    
    e1 = result.expectations[0]
    assert isinstance(e1, MissionExpectation)
    assert e1.id == "e1"
    assert e1.op == "eq"
    assert e1.expected is True
    
    e2 = result.expectations[1]
    assert isinstance(e2, MissionExpectation)
    assert e2.op == "exists"
    # Expected is optional for exists, usually None unless specified
    assert e2.expected is None


def test_parse_expectations_invalid_op(valid_expectations_config):
    """
    Verify error when 'op' is not a valid enum value.
    """
    bad_cfg = copy.deepcopy(valid_expectations_config)
    bad_cfg["expectations"][0]["op"] = "magic_op"
    
    with pytest.raises(ConfigError, match="Invalid value for 'op'"):
        parse_expectations_definition(bad_cfg)


def test_parse_expectations_missing_fields(valid_expectations_config):
    """
    Verify error when expectations missing required fields.
    """
    bad_cfg = copy.deepcopy(valid_expectations_config)
    del bad_cfg["expectations"][0]["id"]
    
    with pytest.raises(ConfigError, match="Missing required field 'id'"):
        parse_expectations_definition(bad_cfg)


# =============================================================================
# Determinism and Non-Mutation Tests
# =============================================================================

def test_determinism_and_immutability(valid_suite_config):
    """
    Verify parsing is deterministic and does not mutate input config.
    """
    cfg_copy = copy.deepcopy(valid_suite_config)
    
    res1 = parse_suite_definition(valid_suite_config)
    res2 = parse_suite_definition(valid_suite_config)
    
    # Determinism check
    assert res1 == res2
    
    # Immutability check
    assert valid_suite_config == cfg_copy
    
    # Extra check for inner mutation (e.g. popping items)
    _assert_dicts_equal(valid_suite_config, cfg_copy)


def test_ignore_extra_fields(valid_suite_config):
    """
    Verify that extra fields are ignored for forward compatibility (v0.1 decision).
    """
    cfg_with_extra = copy.deepcopy(valid_suite_config)
    cfg_with_extra["extra_field"] = "ignore_me"
    cfg_with_extra["scenarios"][0]["extra_inner"] = "ignore_me_too"
    
    # Should parse without error
    result = parse_suite_definition(cfg_with_extra)
    assert isinstance(result, ScenarioSuiteDefinition)
    # Result structure should match parsing of clean config
    clean_result = parse_suite_definition(valid_suite_config)
    assert result == clean_result
