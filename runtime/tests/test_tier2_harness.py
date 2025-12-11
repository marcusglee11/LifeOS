# runtime/tests/test_tier2_harness.py
"""
TDD Tests for Tier-2 Scenario Harness.

These tests define the contract for the harness module that executes
one or more named missions and returns a single deterministic result.
"""
import copy
import hashlib
import json
from typing import Any, Dict, Mapping

import pytest

from runtime.orchestration.engine import ExecutionContext, OrchestrationResult
from runtime.orchestration.registry import UnknownMissionError
from runtime.orchestration.harness import (
    MissionCall,
    ScenarioDefinition,
    ScenarioResult,
    run_scenario,
)


def _stable_hash(obj: Any) -> str:
    """
    Deterministic hash helper for asserting byte-identical behaviour.
    Uses JSON serialisation with sorted keys and stable separators.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# =============================================================================
# Basic Scenario Execution Tests
# =============================================================================

def test_single_mission_scenario():
    """
    Single-mission scenario with daily_loop returns valid ScenarioResult.
    """
    defn = ScenarioDefinition(
        scenario_name="test-single-mission",
        initial_state={"counter": 0},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    result = run_scenario(defn)
    
    assert isinstance(result, ScenarioResult)
    assert result.scenario_name == "test-single-mission"
    assert "daily_loop" in result.mission_results
    assert isinstance(result.mission_results["daily_loop"], OrchestrationResult)


def test_multi_mission_scenario():
    """
    Multi-mission scenario executes both missions in order.
    """
    defn = ScenarioDefinition(
        scenario_name="test-multi-mission",
        initial_state={"run_id": "multi-test"},
        missions=[
            MissionCall(name="daily_loop", params={"mode": "standard"}),
            MissionCall(name="echo", params={"message": "hello"}),
        ],
    )
    
    result = run_scenario(defn)
    
    assert isinstance(result, ScenarioResult)
    assert result.scenario_name == "test-multi-mission"
    
    # Both missions should be present
    assert "daily_loop" in result.mission_results
    assert "echo" in result.mission_results
    
    # Both values should be OrchestrationResult instances
    assert isinstance(result.mission_results["daily_loop"], OrchestrationResult)
    assert isinstance(result.mission_results["echo"], OrchestrationResult)


def test_empty_missions_scenario():
    """
    Scenario with no missions returns empty results.
    """
    defn = ScenarioDefinition(
        scenario_name="test-empty",
        initial_state={},
        missions=[],
    )
    
    result = run_scenario(defn)
    
    assert isinstance(result, ScenarioResult)
    assert result.scenario_name == "test-empty"
    assert result.mission_results == {}


# =============================================================================
# Determinism Tests
# =============================================================================

def test_scenario_determinism_for_same_inputs():
    """
    Same ScenarioDefinition executed twice produces identical results.
    """
    defn = ScenarioDefinition(
        scenario_name="test-determinism",
        initial_state={"seed": 42, "mode": "baseline"},
        missions=[
            MissionCall(name="daily_loop", params={"mode": "default"}),
            MissionCall(name="echo", params={"key": "value"}),
        ],
    )
    
    result1 = run_scenario(defn)
    result2 = run_scenario(defn)
    
    # scenario_name must match
    assert result1.scenario_name == result2.scenario_name
    
    # Serialised mission_results must be identical
    serialised1 = {name: r.to_dict() for name, r in result1.mission_results.items()}
    serialised2 = {name: r.to_dict() for name, r in result2.mission_results.items()}
    
    h1 = _stable_hash(serialised1)
    h2 = _stable_hash(serialised2)
    
    assert h1 == h2, "Mission results must be deterministic"
    
    # Metadata must be identical
    assert result1.metadata == result2.metadata


def test_scenario_determinism_across_multiple_runs():
    """
    Running the same scenario multiple times produces stable hashes.
    """
    defn = ScenarioDefinition(
        scenario_name="test-multi-run-determinism",
        initial_state={"counter": 0},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    hashes = []
    for _ in range(5):
        result = run_scenario(defn)
        serialised = {name: r.to_dict() for name, r in result.mission_results.items()}
        hashes.append(_stable_hash(serialised))
    
    # All hashes must be identical
    assert len(set(hashes)) == 1, "All runs must produce identical result hashes"


# =============================================================================
# Immutability Tests
# =============================================================================

def test_scenario_does_not_mutate_initial_state():
    """
    initial_state passed into ScenarioDefinition remains unchanged.
    """
    initial_state = {"foo": "bar", "count": 42}
    initial_state_copy = dict(initial_state)
    
    defn = ScenarioDefinition(
        scenario_name="test-immutability",
        initial_state=initial_state,
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    _ = run_scenario(defn)
    
    # initial_state must remain unchanged
    assert dict(defn.initial_state) == initial_state_copy


def test_scenario_does_not_mutate_mission_params():
    """
    Mission params passed into MissionCall remain unchanged.
    """
    params = {"key": "value", "nested": {"inner": 1}}
    params_copy = copy.deepcopy(params)
    
    defn = ScenarioDefinition(
        scenario_name="test-params-immutability",
        initial_state={},
        missions=[MissionCall(name="echo", params=params)],
    )
    
    _ = run_scenario(defn)
    
    # params must remain unchanged (checking the original dict)
    assert params == params_copy


# =============================================================================
# Metadata Tests
# =============================================================================

def test_scenario_result_metadata_is_json_serialisable():
    """
    ScenarioResult.metadata must be JSON-serialisable.
    """
    defn = ScenarioDefinition(
        scenario_name="test-metadata-json",
        initial_state={"counter": 0},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    result = run_scenario(defn)
    
    assert isinstance(result.metadata, Mapping)
    
    # Must be JSON-serialisable without error (after casting)
    json_payload = json.dumps(dict(result.metadata), sort_keys=True)
    assert isinstance(json_payload, str)


def test_scenario_result_metadata_contains_scenario_name():
    """
    Metadata must include scenario_name.
    """
    defn = ScenarioDefinition(
        scenario_name="test-metadata-name",
        initial_state={},
        missions=[MissionCall(name="echo", params=None)],
    )
    
    result = run_scenario(defn)
    
    assert "scenario_name" in result.metadata
    assert result.metadata["scenario_name"] == "test-metadata-name"


def test_scenario_result_metadata_contains_stable_hash():
    """
    Metadata must include a stable scenario_hash (64-char hex SHA-256).
    """
    defn = ScenarioDefinition(
        scenario_name="test-metadata-hash",
        initial_state={"seed": 123},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    result = run_scenario(defn)
    
    assert "scenario_hash" in result.metadata
    scenario_hash = result.metadata["scenario_hash"]
    
    # Must be a 64-character hex string (SHA-256)
    assert isinstance(scenario_hash, str)
    assert len(scenario_hash) == 64
    assert all(c in "0123456789abcdef" for c in scenario_hash)


def test_scenario_hash_is_stable_across_runs():
    """
    The scenario_hash is deterministic for identical inputs.
    """
    defn = ScenarioDefinition(
        scenario_name="test-hash-stability",
        initial_state={"seed": 42},
        missions=[
            MissionCall(name="daily_loop", params={"mode": "default"}),
            MissionCall(name="echo", params={"key": "value"}),
        ],
    )
    
    result1 = run_scenario(defn)
    result2 = run_scenario(defn)
    
    assert result1.metadata["scenario_hash"] == result2.metadata["scenario_hash"]


# =============================================================================
# Error Handling Tests
# =============================================================================

def test_unknown_mission_propagates_error():
    """
    Invalid mission name raises UnknownMissionError (propagated).
    """
    defn = ScenarioDefinition(
        scenario_name="test-unknown-mission",
        initial_state={},
        missions=[MissionCall(name="not-a-real-mission", params=None)],
    )
    
    with pytest.raises(UnknownMissionError):
        run_scenario(defn)


def test_error_after_successful_missions():
    """
    If a later mission fails, earlier results are not returned (exception propagates).
    """
    defn = ScenarioDefinition(
        scenario_name="test-partial-failure",
        initial_state={},
        missions=[
            MissionCall(name="daily_loop", params=None),
            MissionCall(name="invalid-mission", params=None),
        ],
    )
    
    with pytest.raises(UnknownMissionError):
        run_scenario(defn)


# =============================================================================
# Integration Tests
# =============================================================================

def test_scenario_result_is_fully_serialisable():
    """
    The entire ScenarioResult can be converted to a JSON-serialisable dict.
    """
    defn = ScenarioDefinition(
        scenario_name="test-full-serialisation",
        initial_state={"counter": 0, "mode": "test"},
        missions=[
            MissionCall(name="daily_loop", params=None),
            MissionCall(name="echo", params={"key": "value"}),
        ],
    )
    
    result = run_scenario(defn)
    
    result = run_scenario(defn)
    
    # Verify built-in to_dict() method
    serialised = result.to_dict()
    
    assert isinstance(serialised, dict)
    assert serialised["scenario_name"] == result.scenario_name
    assert "mission_results" in serialised
    assert "metadata" in serialised
    
    # Must be JSON-serialisable
    json_payload = json.dumps(serialised, sort_keys=True, separators=(",", ":"))
    assert isinstance(json_payload, str)
    
    # And stable-hashable
    h = _stable_hash(serialised)
    assert isinstance(h, str)
    assert len(h) == 64
    
    # Ensure mission results are serialised nicely
    assert isinstance(serialised["mission_results"]["daily_loop"], dict)
    assert isinstance(serialised["mission_results"]["echo"], dict)
