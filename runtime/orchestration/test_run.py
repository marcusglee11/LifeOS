"""
Tier-2 Test Run Aggregator

Thin, deterministic integration layer that:
1. Executes a ScenarioSuiteDefinition via run_suite.
2. Evaluates SuiteExpectationsDefinition via evaluate_expectations.
3. Returns a single aggregated TestRunResult with stable hashing.

Core component for the future Deterministic Test Harness v0.5.
No I/O, network, subprocess, or time/date access.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Dict, Mapping

from runtime.orchestration.suite import (
    ScenarioSuiteDefinition,
    ScenarioSuiteResult,
    run_suite,
)
from runtime.orchestration.expectations import (
    SuiteExpectationsDefinition,
    SuiteExpectationsResult,
    evaluate_expectations,
)


@dataclass(frozen=True)
class TestRunResult:
    """
    Aggregated result for a full Tier-2 test run.
    
    Attributes:
        suite_result: Result of scenario suite execution.
        expectations_result: Verdict of expectations evaluation.
        passed: Overall boolean verdict (True if all expectations passed).
        metadata: Deterministic, JSON-serialisable metadata (including stable hash).
    """
    suite_result: ScenarioSuiteResult
    expectations_result: SuiteExpectationsResult
    passed: bool
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Enforce strict read-only nature of mapping fields."""
        object.__setattr__(
            self, 
            "metadata", 
            MappingProxyType(dict(self.metadata))
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to JSON-serializable dict with stable key ordering.
        
        Returns:
            Dict containing suite_result, expectations_result, passed, metadata.
        """
        return {
            "schema_version": "test_run_result@1",
            "suite_result": self._serialise_suite_result(self.suite_result),
            "expectations_result": self._serialise_expectations_result(self.expectations_result),
            "passed": self.passed,
            "metadata": dict(self.metadata),
        }

    def _serialise_suite_result(self, res: ScenarioSuiteResult) -> Dict[str, Any]:
         # ScenarioSuiteResult is an internal container. We serialise it here explicitly rather than adding a public to_dict().
         return {
             "suite_name": res.suite_name,
             "scenario_results": {k: v.to_dict() for k, v in dict(res.scenario_results).items()},
             "metadata": dict(res.metadata),
         }

    def _serialise_expectations_result(self, res: SuiteExpectationsResult) -> Dict[str, Any]:
        return {
            "passed": res.passed,
            "expectation_results": {
                k: {
                    "id": v.id,
                    "passed": v.passed,
                    "actual": v.actual,
                    "expected": v.expected,
                    "details": dict(v.details)
                } for k, v in dict(res.expectation_results).items()
            },
            "metadata": dict(res.metadata),
        }


def _stable_hash(obj: Any) -> str:
    """Deterministic SHA-256 hash of JSON-serialisable object."""
    try:
        payload = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    except TypeError:
        payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def run_test_run(
    suite_def: ScenarioSuiteDefinition,
    expectations_def: SuiteExpectationsDefinition,
) -> TestRunResult:
    """
    Execute a full test run: run suite -> evaluate expectations -> aggregate result.
    
    Args:
        suite_def: Definition of scenarios to run.
        expectations_def: Definition of expectations to evaluate.
        
    Returns:
        TestRunResult with aggregated results and deterministic metadata.
    """
    # 1. Run Suite
    suite_res = run_suite(suite_def)
    
    # 2. Evaluate Expectations
    expectations_res = evaluate_expectations(suite_res, expectations_def)
    
    # 3. Aggregate Verdict
    passed = expectations_res.passed
    
    # 4. Generate Deterministic Metadata
    # We need a stable representation of the entire run for hashing
    
    # Serialise suite result components relevant for hashing
    serialised_suite = {
        name: {
            "scenario_name": sr.scenario_name,
            "mission_results": {
                m_name: m_res.to_dict()
                for m_name, m_res in dict(sr.mission_results).items()
            },
            "metadata": dict(sr.metadata),
        }
        for name, sr in dict(suite_res.scenario_results).items()
    }
    
    # Serialise expectations result components
    serialised_expectations = {
        eid: {
            "passed": er.passed,
            "actual": er.actual,
            "expected": er.expected,
            "details": dict(er.details),
        }
        for eid, er in dict(expectations_res.expectation_results).items()
    }
    
    # Construct payload for hashing
    hash_payload = {
        "suite_result": serialised_suite,
        "suite_metadata": dict(suite_res.metadata),
        "expectations_result": serialised_expectations,
        "expectations_metadata": dict(expectations_res.metadata),
        "passed": passed,
    }
    
    test_run_hash = _stable_hash(hash_payload)
    
    metadata: Dict[str, Any] = {
        "suite_name": suite_def.suite_name,
        "test_run_hash": test_run_hash,
    }
    
    return TestRunResult(
        suite_result=suite_res,
        expectations_result=expectations_res,
        passed=passed,
        metadata=metadata,
    )
