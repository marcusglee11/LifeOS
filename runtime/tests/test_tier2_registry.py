# runtime/tests/test_tier2_registry.py

import copy
import hashlib
import json
from typing import Any, Dict

import pytest

from runtime.orchestration.engine import (
    ExecutionContext,
    OrchestrationResult,
)
from runtime.orchestration import registry as reg


# Public surface under test
from runtime.orchestration.registry import (
    MISSION_REGISTRY,
    run_mission,
    UnknownMissionError,
)


def _stable_hash(obj: Any) -> str:
    """
    Deterministic hash helper for asserting byte-identical behaviour.

    Uses JSON serialisation with sorted keys and stable separators,
    then hashes via SHA-256.
    """
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _make_ctx(initial_state: Dict[str, Any] | None = None) -> ExecutionContext:
    """
    Helper to construct a minimal ExecutionContext instance for tests.

    Assumes ExecutionContext accepts an `initial_state` mapping and that
    any additional fields are optional / have sensible defaults.
    """
    if initial_state is None:
        initial_state = {}
    return ExecutionContext(initial_state=copy.deepcopy(initial_state))


# ---------------------------------------------------------------------------
# Registry shape & basic contracts
# ---------------------------------------------------------------------------


def test_registry_contains_core_missions() -> None:
    """
    The registry must expose at least the core Tier-2 missions that
    external callers can rely on.
    """
    assert "daily_loop" in MISSION_REGISTRY
    # Minimal synthetic mission for testing / examples.
    assert "echo" in MISSION_REGISTRY


def test_run_mission_dispatches_via_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    run_mission(name, ...) must delegate to the builder registered
    in MISSION_REGISTRY for that name.
    """
    calls: Dict[str, Any] = {}

    def dummy_builder(params: Dict[str, Any] | None = None):
        # Record that we were invoked with the expected params.
        calls["params"] = params

        # Build the smallest possible workflow definition.
        from runtime.orchestration.engine import WorkflowDefinition

        return WorkflowDefinition(name="dummy", steps=[])

    # Replace the registered builder for "daily_loop" with our dummy.
    monkeypatch.setitem(MISSION_REGISTRY, "daily_loop", dummy_builder)

    ctx = _make_ctx({"foo": "bar"})
    params = {"mode": "standard"}

    result = run_mission("daily_loop", ctx, params=params)

    assert isinstance(result, OrchestrationResult)
    assert calls["params"] == params


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_unknown_mission_raises_unknownmissionerror() -> None:
    """
    Unknown mission names must raise a clear, deterministic error so that
    callers can handle configuration mistakes upstream.
    """
    ctx = _make_ctx()

    with pytest.raises(UnknownMissionError):
        run_mission("not-a-real-mission", ctx)


def test_workflow_definition_enforces_id_name_consistency() -> None:
    """
    WorkflowDefinition must enforce consistency between 'id' and 'name'.
    """
    from runtime.orchestration.engine import WorkflowDefinition

    # mismatched id/name should raise ValueError
    with pytest.raises(ValueError, match="mismatch"):
        WorkflowDefinition(id="wf-1", name="wf-2", steps=[])

    # auto-derivation
    wf1 = WorkflowDefinition(id="wf-1", steps=[])
    assert wf1.name == "wf-1"

    wf2 = WorkflowDefinition(name="wf-2", steps=[])
    assert wf2.id == "wf-2"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_run_mission_is_deterministic_for_same_inputs() -> None:
    """
    Same mission + same params + same initial state must produce an
    identical OrchestrationResult when viewed as a serialised dict.
    """
    initial_state = {"counter": 0, "mode": "baseline"}
    params = {"run_mode": "standard"}

    ctx = _make_ctx(initial_state)

    result_1 = run_mission("daily_loop", ctx, params=params)
    result_2 = run_mission("daily_loop", ctx, params=params)

    assert isinstance(result_1, OrchestrationResult)
    assert isinstance(result_2, OrchestrationResult)

    h1 = _stable_hash(result_1.to_dict())
    h2 = _stable_hash(result_2.to_dict())

    assert h1 == h2


def test_run_mission_does_not_mutate_initial_state() -> None:
    """
    The ExecutionContext's initial_state must not be mutated as a side effect
    of running a mission. Any state changes must be represented in the
    OrchestrationResult, not by mutating the input context.
    """
    initial_state = {"message": "hello", "count": 1}
    ctx = _make_ctx(initial_state)

    _ = run_mission("daily_loop", ctx, params=None)

    # The context's initial_state should remain byte-identical.
    assert ctx.initial_state == initial_state


# ---------------------------------------------------------------------------
# Integration behaviour
# ---------------------------------------------------------------------------


def test_integration_daily_loop_yields_serialisable_result() -> None:
    """
    End-to-end execution of the 'daily_loop' mission must produce an
    OrchestrationResult whose dict representation is JSON-serialisable
    and stable-hashable.
    """
    ctx = _make_ctx({"counter": 0})

    result = run_mission("daily_loop", ctx, params=None)
    assert isinstance(result, OrchestrationResult)

    as_dict = result.to_dict()
    assert isinstance(as_dict, dict)

    # Must be JSON-serialisable.
    json_payload = json.dumps(as_dict, sort_keys=True, separators=(",", ":"))
    assert isinstance(json_payload, str)

    # And must produce a stable hash without error.
    h = _stable_hash(as_dict)
    assert isinstance(h, str)
    assert len(h) == 64  # SHA-256 hex digest


def test_integration_echo_mission_executes_successfully() -> None:
    """
    The synthetic 'echo' mission should execute end-to-end and return a
    valid OrchestrationResult. We do not over-specify its semantics here;
    the purpose is to have a minimal, deterministic example mission.
    """
    ctx = _make_ctx({"message": "ping"})

    result = run_mission("echo", ctx, params={"payload_key": "message"})
    assert isinstance(result, OrchestrationResult)

    as_dict = result.to_dict()
    assert isinstance(as_dict, dict)

    # Ensure the result is stable-hashable as well.
    h = _stable_hash(as_dict)
    assert isinstance(h, str)
    assert len(h) == 64
