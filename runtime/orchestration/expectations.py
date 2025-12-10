"""
Tier-2 Expectations Engine

Evaluates declarative expectations against a ScenarioSuiteResult and returns a
deterministic, JSON-serialisable verdict. Core of the future Deterministic Test
Harness v0.5.

Features:
- Deterministic evaluation of expectations
- JSON-serialisable diagnostics
- Stable hashing of results
- No I/O, network, subprocess, or time/date access
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Mapping, Tuple, Union

from runtime.orchestration.suite import ScenarioSuiteResult


# =============================================================================
# Data Structures
# =============================================================================

ExpectationOp = Literal["eq", "ne", "gt", "lt", "exists"]


@dataclass(frozen=True)
class MissionExpectation:
    """
    A single expectation against a mission result inside a scenario.
    
    Attributes:
        id: Stable identifier for reporting.
        scenario_name: Name of the ScenarioDefinition.
        mission_name: Name of the mission within that scenario.
        path: Dot-separated path inside OrchestrationResult.to_dict().
        op: Comparison operator.
        expected: Expected value for comparison (ignored for 'exists').
    """
    id: str
    scenario_name: str
    mission_name: str
    path: str
    op: ExpectationOp
    expected: Any | None = None


@dataclass(frozen=True)
class ExpectationResult:
    """
    Evaluation result for a single expectation.
    
    Attributes:
        id: Expectation id.
        passed: Boolean verdict.
        actual: Value found at the path (or None if missing).
        expected: Copy of the expected value.
        details: Deterministic, JSON-serialisable diagnostics.
    """
    id: str
    passed: bool
    actual: Any | None
    expected: Any | None
    details: Dict[str, Any]


@dataclass(frozen=True)
class SuiteExpectationsDefinition:
    """
    A collection of expectations to evaluate against a ScenarioSuiteResult.
    """
    expectations: Tuple[MissionExpectation, ...]

    def __init__(self, expectations: List[MissionExpectation] | Tuple[MissionExpectation, ...]):
        # Enforce tuple immutability
        exps_tuple = tuple(expectations) if isinstance(expectations, list) else expectations
        object.__setattr__(self, "expectations", exps_tuple)
        
        # Enforce unique IDs
        ids = [e.id for e in self.expectations]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate expectation IDs are not allowed: {ids}")


@dataclass(frozen=True)
class SuiteExpectationsResult:
    """
    Aggregated expectations verdict.
    
    Attributes:
        passed: Overall boolean verdict (all expectations passed).
        expectation_results: Mapping expectation_id -> ExpectationResult.
        metadata: Deterministic, JSON-serialisable metadata.
    """
    passed: bool
    expectation_results: Dict[str, ExpectationResult]
    metadata: Dict[str, Any]


# =============================================================================
# Helper Functions
# =============================================================================

def _resolve_path(root: Any, path: str) -> Tuple[bool, Any | None]:
    """
    Resolve a dot-separated path against a root object (dict or list).
    
    Args:
        root: The root structure (usually from to_dict()).
        path: Dot-separated path string (e.g. "output.counter" or "steps.0.kind").
        
    Returns:
        (found, value): found is False if any path segment is missing.
    """
    if not path:
        return True, root
        
    current = root
    segments = path.split(".")
    
    for segment in segments:
        # Try list index (integer)
        if isinstance(current, list):
            try:
                index = int(segment)
                if 0 <= index < len(current):
                    current = current[index]
                    continue
                else:
                    return False, None  # Index out of bounds
            except ValueError:
                return False, None  # List key must be integer
        
        # Try dict key
        elif isinstance(current, dict):
            if segment in current:
                current = current[segment]
            else:
                return False, None  # Key missing
        
        else:
            return False, None  # Not a container
            
    return True, current


def _evaluate_op(op: ExpectationOp, actual: Any, expected: Any | None) -> Tuple[bool, Dict[str, Any]]:
    """
    Evaluate an operator against actual/expected values.
    
    Returns:
        (passed, details_dict)
    """
    details: Dict[str, Any] = {}
    
    if op == "exists":
        # 'exists' passes if path resolution succeeded (caller handles resolution)
        # If we reached here, actual is the resolved value, so it "exists".
        return True, {}
        
    elif op == "eq":
        if actual == expected:
            return True, {}
        else:
            return False, {"reason": "eq_mismatch"}
            
    elif op == "ne":
        if actual != expected:
            return True, {}
        else:
            return False, {"reason": "ne_mismatch"}
            
    elif op == "gt":
        try:
            if actual > expected:
                return True, {}
            else:
                return False, {"reason": "gt_mismatch"}
        except TypeError:
            return False, {"reason": "type_error", "message": "Cannot compare types"}
            
    elif op == "lt":
        try:
            if actual < expected:
                return True, {}
            else:
                return False, {"reason": "lt_mismatch"}
        except TypeError:
            return False, {"reason": "type_error", "message": "Cannot compare types"}
            
    return False, {"reason": "unknown_op"}


def _stable_hash(obj: Any) -> str:
    """Deterministic SHA-256 hash of JSON-serialisable object."""
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# =============================================================================
# Public API
# =============================================================================

def evaluate_expectations(
    suite_result: ScenarioSuiteResult,
    definition: SuiteExpectationsDefinition,
) -> SuiteExpectationsResult:
    """
    Evaluate declarative expectations against a ScenarioSuiteResult.
    
    Args:
        suite_result: The result of a run_suite call.
        definition: collection of expectations to evaluate.
        
    Returns:
        SuiteExpectationsResult with pass/fail verdict and diagnostics.
    """
    expectation_results: Dict[str, ExpectationResult] = {}
    
    for expectation in definition.expectations:
        # 1. Locate Scenario
        if expectation.scenario_name not in suite_result.scenario_results:
            expectation_results[expectation.id] = ExpectationResult(
                id=expectation.id,
                passed=False,
                actual=None,
                expected=expectation.expected,
                details={"reason": "scenario_missing", "scenario": expectation.scenario_name}
            )
            continue
            
        scenario_res = suite_result.scenario_results[expectation.scenario_name]
        
        # 2. Locate Mission
        if expectation.mission_name not in scenario_res.mission_results:
            expectation_results[expectation.id] = ExpectationResult(
                id=expectation.id,
                passed=False,
                actual=None,
                expected=expectation.expected,
                details={"reason": "mission_missing", "mission": expectation.mission_name}
            )
            continue
            
        mission_res = scenario_res.mission_results[expectation.mission_name]
        
        # 3. Resolve Path
        # Convert mission result to dict for traversal
        root_data = mission_res.to_dict()
        found, actual_value = _resolve_path(root_data, expectation.path)
        
        if not found:
            # Special handling for 'exists' op: if not found, it fails.
            # For other ops, if path is missing, it also fails (comparison against missing).
            expectation_results[expectation.id] = ExpectationResult(
                id=expectation.id,
                passed=False,
                actual=None,
                expected=expectation.expected,
                details={"reason": "path_missing", "path": expectation.path}
            )
            continue
            
        # 4. Evaluate Operator
        if expectation.op == "exists":
            # If we are here, path was found.
            passed, details = True, {}
        else:
            passed, details = _evaluate_op(expectation.op, actual_value, expectation.expected)
            
        expectation_results[expectation.id] = ExpectationResult(
            id=expectation.id,
            passed=passed,
            actual=actual_value,
            expected=expectation.expected,
            details=details
        )
    
    # Aggregated verdict
    all_passed = all(er.passed for er in expectation_results.values())
    
    # Metadata construction
    serialisable_results = {
        eid: {
            "passed": er.passed,
            "actual": er.actual,
            "expected": er.expected,
            "details": er.details,
        }
        for eid, er in expectation_results.items()
    }
    
    metadata = {
        "expectations_hash": _stable_hash(serialisable_results),
    }
    
    return SuiteExpectationsResult(
        passed=all_passed,
        expectation_results=expectation_results,
        metadata=metadata,
    )
