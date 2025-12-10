# runtime/tests/test_tier2_config_test_run.py
"""
TDD Tests for Tier-2 Config-Driven Test Run Entrypoint.

These tests define the contract for the high-level entrypoint that
processes config dicts into a full test run.
"""
import copy
import hashlib
import json
from typing import Any, Dict

import pytest

from runtime.orchestration.config_adapter import ConfigError
from runtime.orchestration.test_run import TestRunResult
from runtime.orchestration.config_test_run import run_test_run_from_config


def _stable_hash(obj: Any) -> str:
    """Deterministic hash helper."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _serialise_test_run(tr: TestRunResult) -> Dict[str, Any]:
    """Helper to serialise a TestRunResult for comparison."""
    # Simplified serialisation sufficient for equality check
    return {
        "suite_name": tr.suite_result.suite_name,
        "expectations_passed": tr.expectations_result.passed,
        "run_passed": tr.passed,
        "metadata": tr.metadata,
        # We could go deeper but metadata hash covers deep content equality
    }


@pytest.fixture
def valid_suite_cfg() -> Dict[str, Any]:
    return {
        "suite_name": "basic_suite",
        "scenarios": [
            {
                "scenario_name": "s1",
                "initial_state": {"count": 10},
                "missions": [
                    {
                        "name": "daily_loop",
                        "params": None
                    }
                ]
            }
        ]
    }


@pytest.fixture
def valid_expectations_cfg() -> Dict[str, Any]:
    return {
        "expectations": [
            {
                "id": "e1",
                "scenario_name": "s1",
                "mission_name": "daily_loop",
                "path": "success",
                "op": "eq",
                "expected": True
            }
        ]
    }


# =============================================================================
# Happy Path
# =============================================================================

def test_happy_path(valid_suite_cfg, valid_expectations_cfg):
    """
    Verify successful execution from valid config.
    """
    result = run_test_run_from_config(valid_suite_cfg, valid_expectations_cfg)
    
    assert isinstance(result, TestRunResult)
    assert result.passed is True
    assert result.suite_result.suite_name == "basic_suite"
    assert result.expectations_result.passed is True


# =============================================================================
# Failing Expectations
# =============================================================================

def test_failing_expectations(valid_suite_cfg):
    """
    Verify test run fail verdict on failed expectations.
    """
    failing_exp_cfg = {
        "expectations": [
            {
                "id": "must_fail",
                "scenario_name": "s1",
                "mission_name": "daily_loop",
                "path": "success",
                "op": "eq",
                "expected": False  # daily_loop succeeds by default
            }
        ]
    }
    
    result = run_test_run_from_config(valid_suite_cfg, failing_exp_cfg)
    
    assert result.passed is False
    assert result.expectations_result.passed is False
    assert result.expectations_result.expectation_results["must_fail"].passed is False


# =============================================================================
# Determinism & Non-Mutation
# =============================================================================

def test_determinism_and_immutability(valid_suite_cfg, valid_expectations_cfg):
    """
    Verify results are deterministic and inputs unmutated.
    """
    suite_copy = copy.deepcopy(valid_suite_cfg)
    exp_copy = copy.deepcopy(valid_expectations_cfg)
    
    res1 = run_test_run_from_config(valid_suite_cfg, valid_expectations_cfg)
    res2 = run_test_run_from_config(valid_suite_cfg, valid_expectations_cfg)
    
    # Check identity
    assert _stable_hash(_serialise_test_run(res1)) == _stable_hash(_serialise_test_run(res2))
    assert res1.metadata["test_run_hash"] == res2.metadata["test_run_hash"]
    
    # Check immutability
    assert valid_suite_cfg == suite_copy
    assert valid_expectations_cfg == exp_copy


# =============================================================================
# Error Behaviour
# =============================================================================

def test_config_errors(valid_suite_cfg, valid_expectations_cfg):
    """
    Verify ConfigError is raised on invalid inputs.
    """
    # Invalid suite config (missing field)
    bad_suite = copy.deepcopy(valid_suite_cfg)
    del bad_suite["suite_name"]
    
    with pytest.raises(ConfigError):
        run_test_run_from_config(bad_suite, valid_expectations_cfg)
        
    # Invalid expectations config (invalid op)
    bad_exp = copy.deepcopy(valid_expectations_cfg)
    bad_exp["expectations"][0]["op"] = "invalid_op"
    
    with pytest.raises(ConfigError):
        run_test_run_from_config(valid_suite_cfg, bad_exp)
