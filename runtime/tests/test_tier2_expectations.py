# runtime/tests/test_tier2_expectations.py
"""
TDD Tests for Tier-2 Expectations Engine.

These tests define the contract for the expectations module that evaluates
declarative expectations against a ScenarioSuiteResult.
"""
import copy
import hashlib
import json
from typing import Any, Dict

import pytest

from runtime.orchestration.harness import (
    MissionCall,
    ScenarioDefinition,
)
from runtime.orchestration.suite import (
    ScenarioSuiteDefinition,
    run_suite,
)
from runtime.orchestration.expectations import (
    ExpectationResult,
    MissionExpectation,
    SuiteExpectationsDefinition,
    SuiteExpectationsResult,
    evaluate_expectations,
)


def _stable_hash(obj: Any) -> str:
    """
    Deterministic hash helper for asserting byte-identical behaviour.
    Uses JSON serialisation with sorted keys and stable separators.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@pytest.fixture
def sample_suite_result():
    """
    Creates a real ScenarioSuiteResult using the Tier-2 stack.
    Includes a 'daily_loop' mission and an 'echo' mission.
    """
    # Daily loop scenario
    scenario_a = ScenarioDefinition(
        scenario_name="scenario_a",
        initial_state={"counter": 0},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    # Echo scenario
    scenario_b = ScenarioDefinition(
        scenario_name="scenario_b",
        initial_state={"message": "hello_world"},
        missions=[
            MissionCall(name="echo", params={"str_val": "test", "num_val": 42}),
        ],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="test_suite",
        scenarios=[scenario_a, scenario_b],
    )
    
    return run_suite(suite_def)


# =============================================================================
# Basic Success Cases
# =============================================================================

def test_basic_success(sample_suite_result):
    """
    Verify basic expectations (exists, eq) passing.
    """
    # Define expectations
    # 1. scenario_a/daily_loop id exists
    # 2. scenario_b/echo success is True
    # 3. scenario_b/echo param echo exists in executed_steps payload (checking structure)
    
    expectations = [
        MissionExpectation(
            id="exp_1",
            scenario_name="scenario_a",
            mission_name="daily_loop",
            path="id",
            op="exists",
        ),
        MissionExpectation(
            id="exp_2",
            scenario_name="scenario_b",
            mission_name="echo",
            path="success",
            op="eq",
            expected=True,
        ),
    ]
    
    defn = SuiteExpectationsDefinition(expectations=expectations)
    result = evaluate_expectations(sample_suite_result, defn)
    
    assert isinstance(result, SuiteExpectationsResult)
    assert result.passed is True
    assert len(result.expectation_results) == 2
    
    assert result.expectation_results["exp_1"].passed is True
    assert result.expectation_results["exp_2"].passed is True
    assert result.expectation_results["exp_2"].actual is True


# =============================================================================
# Hardening & Error Handling
# =============================================================================

def test_duplicate_expectation_ids_raise_error():
    """
    SuiteExpectationsDefinition must enforce unique expectation IDs.
    """
    e1 = MissionExpectation(id="dup", scenario_name="s", mission_name="m", path="p", op="exists")
    e2 = MissionExpectation(id="dup", scenario_name="s", mission_name="m", path="p", op="exists")
    
    with pytest.raises(ValueError, match="Duplicate expectation IDs"):
        SuiteExpectationsDefinition(expectations=[e1, e2])


def test_expectations_collection_is_immutable():
    """
    SuiteExpectationsDefinition stores expectations as a tuple.
    """
    e1 = MissionExpectation(id="e1", scenario_name="s", mission_name="m", path="p", op="exists")
    ls = [e1]
    
    defn = SuiteExpectationsDefinition(expectations=ls)
    assert isinstance(defn.expectations, tuple)
    
    # Mutating original list is safe
    ls.append(e1)
    assert len(defn.expectations) == 1


# =============================================================================
# Failure Cases
# =============================================================================

def test_failure_case(sample_suite_result):
    """
    Verify failing expectations and diagnostics.
    """
    # scenario_b/echo success is False (should be True)
    expectations = [
        MissionExpectation(
            id="fail_eq",
            scenario_name="scenario_b",
            mission_name="echo",
            path="success",
            op="eq",
            expected=False,
        ),
    ]
    
    defn = SuiteExpectationsDefinition(expectations=expectations)
    result = evaluate_expectations(sample_suite_result, defn)
    
    assert result.passed is False
    res = result.expectation_results["fail_eq"]
    assert res.passed is False
    assert res.actual is True
    assert res.expected is False
    assert "reason" in res.details
    assert res.details["reason"] == "eq_mismatch"


# =============================================================================
# Path Resolution
# =============================================================================

def test_path_resolution(sample_suite_result):
    """
    Test nested paths, list indices, and missing paths.
    """
    # The echo workflow has steps. The first step (index 0) is the echo runtime step.
    # It has a payload.
    
    expectations = [
        # Nested dict path
        MissionExpectation(
            id="nested_dict",
            scenario_name="scenario_b",
            mission_name="echo",
            path="final_state.message",
            op="eq",
            expected="hello_world",
        ),
        # List index path: steps[0].kind should be 'runtime'
        MissionExpectation(
            id="list_index",
            scenario_name="scenario_b",
            mission_name="echo",
            path="executed_steps.0.kind",
            op="eq",
            expected="runtime",
        ),
        # Missing path
        MissionExpectation(
            id="missing_path",
            scenario_name="scenario_b",
            mission_name="echo",
            path="non.existent.path",
            op="exists",
        )
    ]
    
    defn = SuiteExpectationsDefinition(expectations=expectations)
    result = evaluate_expectations(sample_suite_result, defn)
    
    # Nested dict should pass
    assert result.expectation_results["nested_dict"].passed is True
    
    # List index should pass
    assert result.expectation_results["list_index"].passed is True
    
    # Missing path should fail "exists"
    assert result.expectation_results["missing_path"].passed is False
    assert result.expectation_results["missing_path"].details["reason"] == "path_missing"


# =============================================================================
# Operator Behaviour
# =============================================================================

def test_operator_behavior(sample_suite_result):
    """
    Test comparators and type mismatches.
    """
    # Note: OrchestrationResult doesn't output params in to_dict() by default at top level?
    # Wait, the structure is:
    # id, success, executed_steps, final_state, failed_step_id, error_message, lineage, receipt
    # The echo step payload has params.
    # steps -> [0] -> payload -> params -> num_val (42)
    
    path_num = "executed_steps.0.payload.params.num_val"
    
    expectations = [
        # gt match
        MissionExpectation(id="gt_pass", scenario_name="scenario_b", mission_name="echo",
                           path=path_num, op="gt", expected=40),
        # lt fail
        MissionExpectation(id="lt_fail", scenario_name="scenario_b", mission_name="echo",
                           path=path_num, op="lt", expected=10),
        # ne pass
        MissionExpectation(id="ne_pass", scenario_name="scenario_b", mission_name="echo",
                           path=path_num, op="ne", expected=100),
        # type mismatch (gt with string)
        MissionExpectation(id="type_mismatch", scenario_name="scenario_b", mission_name="echo",
                           path=path_num, op="gt", expected="not_a_number"),
    ]
    
    defn = SuiteExpectationsDefinition(expectations=expectations)
    result = evaluate_expectations(sample_suite_result, defn)
    
    assert result.expectation_results["gt_pass"].passed is True
    assert result.expectation_results["lt_fail"].passed is False
    assert result.expectation_results["ne_pass"].passed is True
    
    # Type mismatch should fail safely
    tm = result.expectation_results["type_mismatch"]
    assert tm.passed is False
    assert tm.details["reason"] == "type_error"


# =============================================================================
# Determinism & Metadata
# =============================================================================

def test_determinism_and_metadata(sample_suite_result):
    """
    Verify determinism of results and stability of metadata hashes.
    """
    expectations = [
        MissionExpectation(id="e1", scenario_name="scenario_a", mission_name="daily_loop",
                           path="success", op="eq", expected=True),
    ]
    defn = SuiteExpectationsDefinition(expectations=expectations)
    
    result1 = evaluate_expectations(sample_suite_result, defn)
    result2 = evaluate_expectations(sample_suite_result, defn)
    
    # Compare structure
    def result_to_dict(r):
        return {
            "passed": r.passed,
            "expectation_results": {
                k: {
                    "passed": v.passed,
                    "actual": v.actual,
                    "expected": v.expected,
                    "details": v.details
                }
                for k, v in r.expectation_results.items()
            },
            "metadata": r.metadata
        }
        
    hash1 = _stable_hash(result_to_dict(result1))
    hash2 = _stable_hash(result_to_dict(result2))
    
    assert hash1 == hash2
    
    # Check metadata structure
    assert "expectations_hash" in result1.metadata
    assert len(result1.metadata["expectations_hash"]) == 64
