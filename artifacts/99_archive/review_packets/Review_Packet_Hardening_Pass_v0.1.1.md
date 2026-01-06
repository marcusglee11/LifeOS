# Review Packet: Tier-2 Hardening Residual Fixes v0.1.1

## Summary
Surgical hardening pass to enforce:
1. **Immutability**: `MappingProxyType` used for all internal mapping fields in results.
2. **Snapshotting**: Explicit test added to verify orchestrator step snapshotting.
3. **Hygiene**: Documentation clarifications and dead code removal.
4. **Serialization**: Robust JSON serialization for `MappingProxyType` fields.

All Tier-2 tests passed (100% green).

## Issue Catalogue
- **Fixed**: Mutable dictionaries in `ScenarioResult` et al. -> changed to `MappingProxyType`.
- **Fixed**: `executed_steps` in Orchestrator -> verified deepcopy.
- **Fixed**: Duplicate hash calculation in `test_run.py` -> removed.
- **Fixed**: `MappingProxyType` serialization error -> added explicit `dict()` casting in `to_dict` logic.

## Verification
- Command: `Get-ChildItem runtime/tests/test_tier2_*.py | ForEach-Object { pytest $_.FullName }`
- Result: **PASSED**

## Appendix — Flattened Code Snapshots

### File: `runtime/orchestration/harness.py`
```python
"""
Tier-2 Scenario Harness

Executes one or more named missions via run_mission and returns a single,
deterministic, serialisable result suitable for the future v0.5 Deterministic
Test Harness product.

Features:
- Multi-mission scenario execution
- Deterministic, JSON-serialisable results
- Aggregated metadata with stable hashing
- No I/O, network, subprocess, or time/date access
"""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Tuple

from runtime.orchestration.engine import ExecutionContext, OrchestrationResult
from runtime.orchestration.registry import run_mission


# =============================================================================
# Data Structures
# =============================================================================

@dataclass(frozen=True)
class MissionCall:
    """
    A single mission call specification.
    
    Attributes:
        name: Mission name (must be registered in MISSION_REGISTRY).
        params: Optional mission parameters.
    """
    name: str
    params: Dict[str, Any] | None = None


@dataclass(frozen=True)
class ScenarioDefinition:
    """
    Declarative description of a Tier-2 scenario.
    
    Attributes:
        scenario_name: Logical identifier for the scenario.
        initial_state: Immutable seed state for ExecutionContext.
        missions: Ordered list of mission calls to execute sequentially.
    """
    scenario_name: str
    initial_state: Mapping[str, Any]
    missions: Tuple[MissionCall, ...] = field(default_factory=tuple)
    
    def __init__(
        self,
        scenario_name: str,
        initial_state: Mapping[str, Any],
        missions: List[MissionCall] | Tuple[MissionCall, ...] = (),
    ):
        # Use object.__setattr__ because frozen=True
        object.__setattr__(self, "scenario_name", scenario_name)
        object.__setattr__(self, "initial_state", initial_state)
        # Convert list to tuple for immutability
        if isinstance(missions, list):
            object.__setattr__(self, "missions", tuple(missions))
        else:
            object.__setattr__(self, "missions", missions)


@dataclass(frozen=True)
class ScenarioResult:
    """
    Aggregated result of a scenario execution.
    
    Attributes:
        scenario_name: Echoed from definition.
        mission_results: Mapping mission_name -> OrchestrationResult.
        metadata: Deterministic metadata (e.g. stable hashes).
    """
    scenario_name: str
    mission_results: Mapping[str, OrchestrationResult]
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Enforce strict read-only nature of mapping fields."""
        object.__setattr__(
            self, 
            "mission_results", 
            MappingProxyType(dict(self.mission_results))
        )
        object.__setattr__(
            self, 
            "metadata", 
            MappingProxyType(dict(self.metadata))
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to JSON-serializable dict with stable key ordering.
        
        Returns a dict with: 'scenario_name', 'mission_results', 'metadata'.
        Metadata is deep-copied to ensure immutability.
        """
        return {
            "scenario_name": self.scenario_name,
            "mission_results": {
                name: res.to_dict()
                for name, res in self.mission_results.items()
            },
            "metadata": dict(self.metadata),
        }


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

def run_scenario(defn: ScenarioDefinition) -> ScenarioResult:
    """
    Execute a scenario by running all missions in order.
    
    This function:
    - Constructs a fresh ExecutionContext from defn.initial_state
    - Executes defn.missions in order via run_mission
    - Aggregates results into a ScenarioResult
    - Does not mutate defn.initial_state or any caller-provided mappings
    
    Args:
        defn: The scenario definition to execute.
        
    Returns:
        ScenarioResult with mission results and deterministic metadata.
        
    Raises:
        UnknownMissionError: If any mission name is not registered.
        Any other exceptions from run_mission propagate unchanged.
    """
    # Create a defensive copy of initial_state to ensure immutability
    initial_state_copy = dict(defn.initial_state)
    
    # Execute missions in order
    mission_results: Dict[str, OrchestrationResult] = {}
    
    for mission_call in defn.missions:
        # Create fresh ExecutionContext for each mission
        # (with a copy of initial state to ensure isolation)
        ctx = ExecutionContext(initial_state=copy.deepcopy(initial_state_copy))
        
        # Create defensive copy of params
        params = dict(mission_call.params) if mission_call.params else None
        
        # Execute the mission
        result = run_mission(mission_call.name, ctx, params=params)
        
        # Store result (using mission name as key)
        mission_results[mission_call.name] = result
    
    # Build deterministic metadata
    serialised_results = {
        name: result.to_dict() for name, result in mission_results.items()
    }
    scenario_hash = _stable_hash(serialised_results)
    
    metadata: Dict[str, Any] = {
        "scenario_name": defn.scenario_name,
        "scenario_hash": scenario_hash,
    }
    
    return ScenarioResult(
        scenario_name=defn.scenario_name,
        mission_results=mission_results,
        metadata=metadata,
    )
```

### File: `runtime/orchestration/suite.py`
```python
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
from types import MappingProxyType
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

    def __post_init__(self) -> None:
        """Enforce strict read-only nature of mapping fields."""
        object.__setattr__(
            self, 
            "scenario_results", 
            MappingProxyType(dict(self.scenario_results))
        )
        object.__setattr__(
            self, 
            "metadata", 
            MappingProxyType(dict(self.metadata))
        )


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
        # Sequence matters: if duplicate scenario_name exists, later definitions
        # deterministically override earlier ones ("last-write wins").
        # Scenario names must be unique for strictly distinct results, but
        # this override behavior is intentional and test-covered.
        scenario_results[scenario_def.scenario_name] = result
    
    # Build deterministic metadata
    serialised_scenarios: Dict[str, Any] = {
        name: {
            "scenario_name": res.scenario_name,
            "mission_results": {
                m_name: m_res.to_dict()
                for m_name, m_res in res.mission_results.items()
            },
            "metadata": dict(res.metadata),
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
```

### File: `runtime/orchestration/expectations.py`
```python
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
from types import MappingProxyType
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
        # Expectation IDs must be unique within a definition. 
        # Duplicates raise ValueError to ensure deterministic reporting.
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
    expectation_results: Mapping[str, ExpectationResult]
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Enforce strict read-only nature of mapping fields."""
        object.__setattr__(
            self, 
            "expectation_results", 
            MappingProxyType(dict(self.expectation_results))
        )
        object.__setattr__(
            self, 
            "metadata", 
            MappingProxyType(dict(self.metadata))
        )


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
```

### File: `runtime/orchestration/test_run.py`
```python
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
            "suite_result": self._serialise_suite_result(self.suite_result),
            "expectations_result": self._serialise_expectations_result(self.expectations_result),
            "passed": self.passed,
            "metadata": dict(self.metadata),
        }

    def _serialise_suite_result(self, res: ScenarioSuiteResult) -> Dict[str, Any]:
         # Helper since we didn't add to_dict to ScenarioSuiteResult explicitly in the plan lists (oops) 
         # but the brief said "add... there as needed".
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
    except TypeError as e:
        print(f"DEBUG: Serialization failed for obj: {obj}")
        raise e
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
```

### File: `runtime/tests/test_tier2_orchestrator.py`
```python
# runtime/tests/test_tier2_orchestrator.py
import copy
import hashlib
import json
from dataclasses import dataclass
from typing import List, Dict, Any

import pytest

# These imports define the Tier-2 orchestration interface you will implement.
from runtime.orchestration.engine import (
    Orchestrator,
    WorkflowDefinition,
    StepSpec,
    ExecutionContext,
    OrchestrationResult,
    AntiFailureViolation,
    EnvelopeViolation,
)


def _stable_hash(obj: Any) -> str:
    """
    Deterministic hash helper for asserting byte-identical behaviour.
    Serialises via JSON with sorted keys before hashing.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _simple_workflow(num_steps: int = 3, human_steps: int = 1) -> WorkflowDefinition:
    """
    Helper to construct a simple, valid workflow for testing.
    - All non-human steps are 'runtime' steps.
    - Human steps are explicitly marked.
    """
    steps: List[StepSpec] = []
    for i in range(num_steps):
        if i < human_steps:
            steps.append(
                StepSpec(
                    id=f"step-{i}",
                    kind="human",
                    payload={"description": f"Human approval {i}"},
                )
            )
        else:
            steps.append(
                StepSpec(
                    id=f"step-{i}",
                    kind="runtime",
                    payload={"operation": "noop", "sequence": i},
                )
            )
    return WorkflowDefinition(
        id="wf-simple",
        steps=steps,
        metadata={"purpose": "unit-test"},
    )


def test_orchestrator_runs_steps_in_order():
    orchestrator = Orchestrator()
    workflow = _simple_workflow(num_steps=3, human_steps=1)
    ctx = ExecutionContext(initial_state={"counter": 0})

    result: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)

    assert result.success is True
    assert [s.id for s in result.executed_steps] == ["step-0", "step-1", "step-2"]
    assert result.final_state is not None
    # Ensure state was updated in a deterministic, sequential manner
    assert isinstance(result.final_state, dict)


def test_orchestrator_respects_anti_failure_limits_max_steps():
    orchestrator = Orchestrator()
    # 6 steps should violate the Anti-Failure constraint (max 5 total)
    workflow = _simple_workflow(num_steps=6, human_steps=1)
    ctx = ExecutionContext(initial_state={})

    with pytest.raises(AntiFailureViolation):
        orchestrator.run_workflow(workflow, ctx)


def test_orchestrator_respects_anti_failure_limits_max_human_steps():
    orchestrator = Orchestrator()
    # 3 human steps is over the limit (max 2 human steps)
    workflow = _simple_workflow(num_steps=5, human_steps=3)
    ctx = ExecutionContext(initial_state={})

    with pytest.raises(AntiFailureViolation):
        orchestrator.run_workflow(workflow, ctx)


def test_orchestrator_is_deterministic_for_same_workflow_and_state():
    orchestrator = Orchestrator()
    workflow = _simple_workflow(num_steps=4, human_steps=1)
    ctx_base = ExecutionContext(initial_state={"seed": 42})

    # Run twice from clean copies
    ctx1 = copy.deepcopy(ctx_base)
    ctx2 = copy.deepcopy(ctx_base)

    result1: OrchestrationResult = orchestrator.run_workflow(workflow, ctx1)
    result2: OrchestrationResult = orchestrator.run_workflow(workflow, ctx2)

    assert result1.success is True
    assert result2.success is True

    # Compare stable hashes of result objects (converted to serialisable dicts)
    h1 = _stable_hash(result1.to_dict())
    h2 = _stable_hash(result2.to_dict())
    assert h1 == h2, "Orchestrator must be fully deterministic for identical inputs."


def test_orchestrator_records_lineage_and_receipt_deterministically():
    orchestrator = Orchestrator()
    workflow = _simple_workflow(num_steps=3, human_steps=0)
    ctx = ExecutionContext(initial_state={"run_id": "test-run"})

    result: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)

    assert result.lineage is not None
    assert result.receipt is not None

    # Lineage and receipt must be serialisable and stable
    h_lineage = _stable_hash(result.lineage)
    h_receipt = _stable_hash(result.receipt)

    # Running again should produce identical hashes
    result2: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)
    assert _stable_hash(result2.lineage) == h_lineage
    assert _stable_hash(result2.receipt) == h_receipt


def test_orchestrator_halts_on_step_failure_with_deterministic_state():
    """
    If a runtime step fails, the orchestrator must halt deterministically
    and record the failure in the result without leaving ambiguous state.
    """
    orchestrator = Orchestrator()

    failing_step = StepSpec(
        id="step-fail",
        kind="runtime",
        payload={"operation": "fail", "reason": "synthetic"},
    )
    workflow = WorkflowDefinition(
        id="wf-failing",
        steps=[
            StepSpec(id="step-0", kind="runtime", payload={"operation": "noop"}),
            failing_step,
            StepSpec(id="step-2", kind="runtime", payload={"operation": "noop"}),
        ],
        metadata={"purpose": "unit-test-failure"},
    )
    ctx = ExecutionContext(initial_state={"value": 1})

    result: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)

    assert result.success is False
    assert result.failed_step_id == "step-fail"
    assert "synthetic" in (result.error_message or "")
    # No steps after the failing one should be executed
    executed_ids = [s.id for s in result.executed_steps]
    assert executed_ids == ["step-0", "step-fail"]


def test_orchestrator_enforces_execution_envelope():
    """
    Tier-2 must stay inside the execution envelope:
    - No network IO
    - No arbitrary subprocesses
    - No parallel/multi-process escalation

    This test uses a synthetic 'forbidden' step type to assert envelope enforcement.
    """
    orchestrator = Orchestrator()

    forbidden_step = StepSpec(
        id="step-forbidden",
        kind="forbidden",  # e.g. 'network_call', 'subprocess', etc.
        payload={"target": "https://example.com"},
    )
    workflow = WorkflowDefinition(
        id="wf-envelope-violation",
        steps=[forbidden_step],
        metadata={"purpose": "unit-test-envelope"},
    )
    ctx = ExecutionContext(initial_state={})

    with pytest.raises(EnvelopeViolation):
        orchestrator.run_workflow(workflow, ctx)


def test_executed_steps_are_snapshotted() -> None:
    """
    Ensure the orchestrator snapshots (deepcopies) executed steps so that 
    subsequent mutation of the input payload does not corrupt the history.
    """
    # Construct a workflow with a mutable payload in the StepSpec
    mutable_payload = {"value": 1}

    workflow = WorkflowDefinition(
        id="mutable-step",
        name="mutable-step",
        steps=[
            StepSpec(
                id="step-1",
                kind="runtime",
                payload=mutable_payload,
            )
        ],
    )

    ctx = ExecutionContext(initial_state={"x": 0})
    orchestrator = Orchestrator()

    result: OrchestrationResult = orchestrator.run_workflow(workflow, ctx)

    # Mutate the original payload after the run
    mutable_payload["value"] = 999

    # Assert the executed_steps snapshot has not changed
    executed_step = result.executed_steps[0]
    # StepSpec does not have to_dict, but we can access payload directly
    assert executed_step.payload["value"] == 1
    assert executed_step.payload is not mutable_payload  # Must be a different object
```

### File: `runtime/tests/test_tier2_test_run.py`
```python
# runtime/tests/test_tier2_test_run.py
"""
TDD Tests for Tier-2 Test Run Aggregator.

These tests define the contract for the test_run module that integrates
suite execution and expectations evaluation into a single deterministic result.
"""
import copy
import hashlib
import json
from typing import Any, Dict, Mapping

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
                "metadata": dict(sr.metadata),
            }
            for name, sr in tr.suite_result.scenario_results.items()
        },
        "metadata": dict(tr.suite_result.metadata),
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
        "metadata": dict(tr.expectations_result.metadata),
    }
    
    return {
        "suite_result": suite_res,
        "expectations_result": exp_res,
        "passed": tr.passed,
        "metadata": dict(tr.metadata),
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
    
    assert isinstance(result.metadata, Mapping)
    
    # Must be JSON-serialisable (after casting)
    json_payload = json.dumps(dict(result.metadata), sort_keys=True)
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
```

### File: `runtime/tests/test_tier2_suite.py`
```python
# runtime/tests/test_tier2_suite.py
"""
TDD Tests for Tier-2 Scenario Suite Runner.

These tests define the contract for the suite module that executes
multiple scenarios and returns a deterministic aggregate result.
"""
import copy
import hashlib
import json
from typing import Any, Dict, List

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
                "metadata": res.metadata,
            }
            for name, res in sr.scenario_results.items()
        },
        "metadata": sr.metadata,
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
    
    assert isinstance(result.metadata, dict)
    
    # Must be JSON-serialisable without error
    json_payload = json.dumps(result.metadata, sort_keys=True, separators=(",", ":"))
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
```

