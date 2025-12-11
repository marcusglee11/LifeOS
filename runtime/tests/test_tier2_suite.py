# runtime/tests/test_tier2_suite.py
"""
TDD Tests for Tier-2 Scenario Suite Runner.

These tests define the contract for the suite module that executes
multiple scenarios and returns a deterministic aggregate result.
"""
import copy
import hashlib
import json
from typing import Any, Dict, List, Mapping

import pytest

from runtime.orchestration.harness import (
    MissionCall,
    ScenarioDefinition,
    ScenarioResult,
    run_scenario,
)
from runtime.orchestration.suite import (
    ScenarioSuiteDefinition,
    ScenarioSuiteResult,
    run_suite,
)
from runtime.orchestration.registry import UnknownMissionError


def _stable_hash(obj: Any) -> str:
    """
    Deterministic hash helper for asserting byte-identical behaviour.
    Uses JSON serialisation with sorted keys and stable separators.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _serialise_suite_result(sr: ScenarioSuiteResult) -> Dict[str, Any]:
    """Helper to serialise a ScenarioSuiteResult for comparison."""
    return {
        "suite_name": sr.suite_name,
        "scenario_results": {
            name: {
                "scenario_name": res.scenario_name,
                "mission_results": {
                    m_name: m_res.to_dict()
                    for m_name, m_res in res.mission_results.items()
                },
                "metadata": dict(res.metadata),
            }
            for name, res in sr.scenario_results.items()
        },
        "metadata": dict(sr.metadata),
    }


# =============================================================================
# Basic Suite Execution Tests
# =============================================================================

def test_suite_runs_single_scenario():
    """
    Suite with a single scenario returns valid ScenarioSuiteResult.
    """
    scenario = ScenarioDefinition(
        scenario_name="single_daily_loop",
        initial_state={"counter": 0},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="single_scenario_suite",
        scenarios=[scenario],
    )
    
    result = run_suite(suite_def)
    
    assert isinstance(result, ScenarioSuiteResult)
    assert result.suite_name == "single_scenario_suite"
    assert "single_daily_loop" in result.scenario_results
    assert isinstance(result.scenario_results["single_daily_loop"], ScenarioResult)


def test_suite_runs_multiple_scenarios():
    """
    Suite with multiple scenarios executes all and returns results.
    """
    scenario_a = ScenarioDefinition(
        scenario_name="scenario_a",
        initial_state={"counter": 0},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    scenario_b = ScenarioDefinition(
        scenario_name="scenario_b",
        initial_state={"message": "ping"},
        missions=[
            MissionCall(name="daily_loop", params=None),
            MissionCall(name="echo", params={"payload_key": "message"}),
        ],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="multi_scenario_suite",
        scenarios=[scenario_a, scenario_b],
    )
    
    result = run_suite(suite_def)
    
    assert isinstance(result, ScenarioSuiteResult)
    assert result.suite_name == "multi_scenario_suite"
    
    # Both scenarios should be present
    assert "scenario_a" in result.scenario_results
    assert "scenario_b" in result.scenario_results
    
    # Both values should be ScenarioResult instances
    assert isinstance(result.scenario_results["scenario_a"], ScenarioResult)
    assert isinstance(result.scenario_results["scenario_b"], ScenarioResult)


def test_suite_runs_empty_scenarios():
    """
    Suite with no scenarios returns empty results.
    """
    suite_def = ScenarioSuiteDefinition(
        suite_name="empty_suite",
        scenarios=[],
    )
    
    result = run_suite(suite_def)
    
    assert isinstance(result, ScenarioSuiteResult)
    assert result.suite_name == "empty_suite"
    assert result.suite_name == "empty_suite"
    assert result.scenario_results == {}


def test_suite_handles_duplicate_scenario_names():
    """
    If multiple scenarios share the same name, the last one wins (deterministic).
    This is implicit behaviour of the dict mapping but we enforce it here.
    """
    s1 = ScenarioDefinition(
        scenario_name="dupe",
        initial_state={"v": 1},
        missions=[MissionCall("daily_loop", None)]
    )
    s2 = ScenarioDefinition(
        scenario_name="dupe",
        initial_state={"v": 2},
        missions=[MissionCall("daily_loop", None)]
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="dupe_suite",
        scenarios=[s1, s2]
    )
    
    result = run_suite(suite_def)
    
    assert len(result.scenario_results) == 1
    assert "dupe" in result.scenario_results
    # Verify the last one won by checking a property of the result hash or internal state
    # (Since both run 'daily_loop' with no params, their results are identical except possibly for receipt timing?)
    # Wait, daily loop is deterministic. The results should be identical.
    # To differentiate, I need different params or initial state affecting the result.
    # But wait, daily_loop result doesn't expose initial_state in `to_dict()` directly unless we debug.
    # Oh, wait. `run_scenario` uses initial_state to create ExecutionContext.
    # Mission result doesn't capture initial state, but final_init_state does capture modifications.
    # Daily loop step count?
    # Actually, I can rely on just the fact that it completed without error for now.
    # OR better: Use 'echo' mission which is minimal and easier to control.
    # OR better: Use 'echo' mission which is minimal and easier to control.
    
    s_echo1 = ScenarioDefinition(
        scenario_name="echo_dupe",
        initial_state={},
        missions=[MissionCall("echo", {"id": "1"})]
    )
    s_echo2 = ScenarioDefinition(
        scenario_name="echo_dupe",
        initial_state={},
        missions=[MissionCall("echo", {"id": "2"})]
    )
    
    suite_def_echo = ScenarioSuiteDefinition(
        suite_name="echo_dupe_suite",
        scenarios=[s_echo1, s_echo2]
    )
    
    res = run_suite(suite_def_echo)
    # OrchestrationResult doesn't carry workflow metadata, but echo mission puts params in step payload.
    echo_res = res.scenario_results["echo_dupe"].mission_results["echo"].to_dict()
    assert echo_res["executed_steps"][0]["payload"]["params"]["id"] == "2"


# =============================================================================
# Determinism Tests
# =============================================================================

def test_suite_is_deterministic_for_same_definition():
    """
    Same ScenarioSuiteDefinition executed twice produces identical results.
    """
    scenario = ScenarioDefinition(
        scenario_name="determinism_test",
        initial_state={"seed": 42, "mode": "baseline"},
        missions=[
            MissionCall(name="daily_loop", params={"mode": "default"}),
            MissionCall(name="echo", params={"key": "value"}),
        ],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="determinism_suite",
        scenarios=[scenario],
    )
    
    result1 = run_suite(suite_def)
    result2 = run_suite(suite_def)
    
    # suite_name must match
    assert result1.suite_name == result2.suite_name
    
    # Serialised results must be identical
    serialised1 = _serialise_suite_result(result1)
    serialised2 = _serialise_suite_result(result2)
    
    h1 = _stable_hash(serialised1)
    h2 = _stable_hash(serialised2)
    
    assert h1 == h2, "Suite results must be deterministic"
    assert len(h1) == 64
    
    # Metadata must be identical
    assert result1.metadata == result2.metadata


def test_suite_determinism_across_multiple_runs():
    """
    Running the same suite multiple times produces stable hashes.
    """
    scenario = ScenarioDefinition(
        scenario_name="multi_run_test",
        initial_state={"counter": 0},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="multi_run_suite",
        scenarios=[scenario],
    )
    
    hashes = []
    for _ in range(5):
        result = run_suite(suite_def)
        serialised = _serialise_suite_result(result)
        hashes.append(_stable_hash(serialised))
    
    # All hashes must be identical
    assert len(set(hashes)) == 1, "All runs must produce identical result hashes"


# =============================================================================
# Immutability Tests
# =============================================================================

def test_suite_does_not_mutate_scenarios_or_initial_state():
    """
    Scenarios and their initial_state remain unchanged after run_suite.
    """
    initial_state_a = {"foo": "bar", "count": 42}
    initial_state_b = {"message": "hello"}
    
    scenario_a = ScenarioDefinition(
        scenario_name="scenario_a",
        initial_state=initial_state_a,
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    scenario_b = ScenarioDefinition(
        scenario_name="scenario_b",
        initial_state=initial_state_b,
        missions=[MissionCall(name="echo", params=None)],
    )
    
    # Keep deep copies for comparison
    initial_state_a_copy = copy.deepcopy(initial_state_a)
    initial_state_b_copy = copy.deepcopy(initial_state_b)
    scenarios_list = [scenario_a, scenario_b]
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="immutability_test",
        scenarios=scenarios_list,
    )
    
    _ = run_suite(suite_def)
    
    # initial_state must remain unchanged
    assert dict(scenario_a.initial_state) == initial_state_a_copy
    assert dict(scenario_b.initial_state) == initial_state_b_copy
    
    # Scenarios list must be unchanged
    assert len(scenarios_list) == 2


# =============================================================================
# Metadata Tests
# =============================================================================

def test_suite_metadata_is_json_serialisable():
    """
    ScenarioSuiteResult.metadata must be JSON-serialisable.
    """
    scenario = ScenarioDefinition(
        scenario_name="metadata_test",
        initial_state={"counter": 0},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="metadata_suite",
        scenarios=[scenario],
    )
    
    result = run_suite(suite_def)
    
    assert isinstance(result.metadata, Mapping)
    
    # Must be JSON-serialisable without error (after casting)
    json_payload = json.dumps(dict(result.metadata), sort_keys=True, separators=(",", ":"))
    assert isinstance(json_payload, str)


def test_suite_metadata_contains_suite_name():
    """
    Metadata must include suite_name.
    """
    scenario = ScenarioDefinition(
        scenario_name="name_test",
        initial_state={},
        missions=[MissionCall(name="echo", params=None)],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="name_test_suite",
        scenarios=[scenario],
    )
    
    result = run_suite(suite_def)
    
    assert "suite_name" in result.metadata
    assert result.metadata["suite_name"] == "name_test_suite"


def test_suite_metadata_contains_stable_hash():
    """
    Metadata must include a stable suite_hash (64-char hex SHA-256).
    """
    scenario = ScenarioDefinition(
        scenario_name="hash_test",
        initial_state={"seed": 123},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="hash_test_suite",
        scenarios=[scenario],
    )
    
    result = run_suite(suite_def)
    
    assert "suite_hash" in result.metadata
    suite_hash = result.metadata["suite_hash"]
    
    # Must be a 64-character hex string (SHA-256)
    assert isinstance(suite_hash, str)
    assert len(suite_hash) == 64
    assert all(c in "0123456789abcdef" for c in suite_hash)


def test_suite_hash_is_stable_across_runs():
    """
    The suite_hash is deterministic for identical inputs.
    """
    scenario = ScenarioDefinition(
        scenario_name="hash_stability_test",
        initial_state={"seed": 42},
        missions=[
            MissionCall(name="daily_loop", params={"mode": "default"}),
            MissionCall(name="echo", params={"key": "value"}),
        ],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="hash_stability_suite",
        scenarios=[scenario],
    )
    
    result1 = run_suite(suite_def)
    result2 = run_suite(suite_def)
    
    assert result1.metadata["suite_hash"] == result2.metadata["suite_hash"]


# =============================================================================
# Error Handling Tests
# =============================================================================

def test_unknown_mission_in_scenario_propagates_error():
    """
    Invalid mission name in a scenario raises UnknownMissionError (propagated).
    """
    scenario = ScenarioDefinition(
        scenario_name="error_scenario",
        initial_state={},
        missions=[MissionCall(name="not-a-real-mission", params=None)],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="error_suite",
        scenarios=[scenario],
    )
    
    with pytest.raises(UnknownMissionError):
        run_suite(suite_def)


def test_error_in_later_scenario_propagates():
    """
    If a later scenario fails, the error propagates (earlier results not returned).
    """
    valid_scenario = ScenarioDefinition(
        scenario_name="valid_scenario",
        initial_state={},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    invalid_scenario = ScenarioDefinition(
        scenario_name="invalid_scenario",
        initial_state={},
        missions=[MissionCall(name="invalid-mission", params=None)],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="partial_failure_suite",
        scenarios=[valid_scenario, invalid_scenario],
    )
    
    with pytest.raises(UnknownMissionError):
        run_suite(suite_def)


# =============================================================================
# Integration Tests
# =============================================================================

def test_suite_result_is_fully_serialisable():
    """
    The entire ScenarioSuiteResult can be converted to a JSON-serialisable dict.
    """
    scenario_a = ScenarioDefinition(
        scenario_name="scenario_a",
        initial_state={"counter": 0},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    scenario_b = ScenarioDefinition(
        scenario_name="scenario_b",
        initial_state={"message": "test"},
        missions=[MissionCall(name="echo", params={"key": "value"})],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="serialisation_suite",
        scenarios=[scenario_a, scenario_b],
    )
    
    result = run_suite(suite_def)
    
    # Build a serialisable representation
    serialised = _serialise_suite_result(result)
    
    # Must be JSON-serialisable
    json_payload = json.dumps(serialised, sort_keys=True, separators=(",", ":"))
    assert isinstance(json_payload, str)
    
    # And stable-hashable
    h = _stable_hash(serialised)
    assert isinstance(h, str)
    assert len(h) == 64
