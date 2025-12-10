# runtime/tests/test_tier2_test_run.py
"""
TDD Tests for Tier-2 Test Run Aggregator.

These tests define the contract for the test_run module that integrates
suite execution and expectations evaluation into a single deterministic result.
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
    ScenarioSuiteResult,
)
from runtime.orchestration.expectations import (
    MissionExpectation,
    SuiteExpectationsDefinition,
    SuiteExpectationsResult,
)
from runtime.orchestration.test_run import (
    TestRunResult,
    run_test_run,
)


def _stable_hash(obj: Any) -> str:
    """
    Deterministic hash helper for asserting byte-identical behaviour.
    Uses JSON serialisation with sorted keys and stable separators.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _serialise_test_run(tr: TestRunResult) -> Dict[str, Any]:
    """Helper to serialise a TestRunResult for comparison."""
    # Build complete serialise structure as per spec
    # Suite result serialisation
    suite_res = {
        "suite_name": tr.suite_result.suite_name,
        "scenario_results": {
            name: {
                "scenario_name": sr.scenario_name,
                "mission_results": {
                    m_name: m_res.to_dict()
                    for m_name, m_res in sr.mission_results.items()
                },
                "metadata": sr.metadata,
            }
            for name, sr in tr.suite_result.scenario_results.items()
        },
        "metadata": tr.suite_result.metadata,
    }
    
    # Expectations result serialisation
    exp_res = {
        "passed": tr.expectations_result.passed,
        "expectation_results": {
            eid: {
                "passed": er.passed,
                "actual": er.actual,
                "expected": er.expected,
                "details": er.details,
            }
            for eid, er in tr.expectations_result.expectation_results.items()
        },
        "metadata": tr.expectations_result.metadata,
    }
    
    return {
        "suite_result": suite_res,
        "expectations_result": exp_res,
        "passed": tr.passed,
        "metadata": tr.metadata,
    }


@pytest.fixture
def sample_definitions():
    """
    Returns (suite_def, expectations_def) for testing.
    Uses 'daily_loop' mission.
    """
    scenario = ScenarioDefinition(
        scenario_name="test_scenario",
        initial_state={"counter": 0},
        missions=[MissionCall(name="daily_loop", params=None)],
    )
    
    suite_def = ScenarioSuiteDefinition(
        suite_name="test_run_suite",
        scenarios=[scenario],
    )
    
    expectations = [
        MissionExpectation(
            id="e1",
            scenario_name="test_scenario",
            mission_name="daily_loop",
            path="id",
            op="exists",
        )
    ]
    
    expectations_def = SuiteExpectationsDefinition(expectations=expectations)
    
    return suite_def, expectations_def


# =============================================================================
# Basic Integration Tests
# =============================================================================

def test_basic_integration_success(sample_definitions):
    """
    Verify run_test_run executes suite and expectations successfully.
    """
    suite_def, expectations_def = sample_definitions
    
    result = run_test_run(suite_def, expectations_def)
    
    assert isinstance(result, TestRunResult)
    assert result.passed is True
    
    # Verify components
    assert isinstance(result.suite_result, ScenarioSuiteResult)
    assert result.suite_result.suite_name == "test_run_suite"
    
    assert isinstance(result.expectations_result, SuiteExpectationsResult)
    assert result.expectations_result.passed is True
    assert "e1" in result.expectations_result.expectation_results
    assert result.expectations_result.passed is True
    assert "e1" in result.expectations_result.expectation_results
    assert result.expectations_result.expectation_results["e1"].passed is True
    
    # Verify to_dict() presence and structure
    d = result.to_dict()
    assert isinstance(d, dict)
    assert d["passed"] is True
    assert "suite_result" in d
    assert "expectations_result" in d
    assert "metadata" in d


# =============================================================================
# Failure Propagation Tests
# =============================================================================

def test_failure_propagation(sample_definitions):
    """
    Verify failing expectations result in failed TestRunResult.
    """
    suite_def, _ = sample_definitions
    
    # Define a failing expectation
    failing_expectations = [
        MissionExpectation(
            id="fail_1",
            scenario_name="test_scenario",
            mission_name="daily_loop",
            path="success",
            op="eq",
            expected=False,  # Should fail, as daily_loop typically succeeds
        )
    ]
    expectations_def = SuiteExpectationsDefinition(expectations=failing_expectations)
    
    result = run_test_run(suite_def, expectations_def)
    
    assert result.passed is False
    assert result.expectations_result.passed is False
    assert result.expectations_result.expectation_results["fail_1"].passed is False
    
    # Check details exist
    details = result.expectations_result.expectation_results["fail_1"].details
    assert "reason" in details


# =============================================================================
# Determinism Tests
# =============================================================================

def test_determinism(sample_definitions):
    """
    Verify run_test_run is deterministic for same inputs.
    """
    suite_def, expectations_def = sample_definitions
    
    result1 = run_test_run(suite_def, expectations_def)
    result2 = run_test_run(suite_def, expectations_def)
    
    # passed verdict must match
    assert result1.passed == result2.passed
    
    # Metadata must match
    assert result1.metadata == result2.metadata
    
    # Serialised structure must be identical
    serialised1 = _serialise_test_run(result1)
    serialised2 = _serialise_test_run(result2)
    
    hash1 = _stable_hash(serialised1)
    hash2 = _stable_hash(serialised2)
    
    assert hash1 == hash2
    assert len(hash1) == 64


# =============================================================================
# Metadata Tests
# =============================================================================

def test_metadata_structure(sample_definitions):
    """
    Verify metadata shape and hash presence.
    """
    suite_def, expectations_def = sample_definitions
    
    result = run_test_run(suite_def, expectations_def)
    
    assert isinstance(result.metadata, dict)
    
    # Must be JSON-serialisable
    json_payload = json.dumps(result.metadata, sort_keys=True)
    assert isinstance(json_payload, str)
    
    # Check for stable hash
    assert "test_run_hash" in result.metadata
    tr_hash = result.metadata["test_run_hash"]
    assert isinstance(tr_hash, str)
    assert len(tr_hash) == 64


def test_metadata_hash_stability(sample_definitions):
    """
    The test_run_hash is stable across runs.
    """
    suite_def, expectations_def = sample_definitions
    
    result1 = run_test_run(suite_def, expectations_def)
    result2 = run_test_run(suite_def, expectations_def)
    
    assert result1.metadata["test_run_hash"] == result2.metadata["test_run_hash"]
