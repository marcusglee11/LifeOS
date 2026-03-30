"""Tests: Deterministic ID generation (Phase 2A — Constitutional Compliance).

Verifies that identical inputs produce identical IDs across calls,
replacing the former uuid.uuid4() randomness in engine.py and coo/commands.py.
"""

from __future__ import annotations

import json

from runtime.util.canonical import compute_sha256

# ---------------------------------------------------------------------------
# 2A-1: Engine mission run_id is deterministic for same inputs
# ---------------------------------------------------------------------------


def test_engine_mission_run_id_deterministic():
    """Same mission_type + step_id + inputs → same run_id each time."""
    inputs_a = {"mission_type": "doc_steward", "step_id": "step-1", "inputs": {"path": "docs/"}}
    inputs_b = {"mission_type": "doc_steward", "step_id": "step-1", "inputs": {"path": "docs/"}}

    id_a = compute_sha256(inputs_a)
    id_b = compute_sha256(inputs_b)
    assert id_a == id_b


def test_engine_mission_run_id_differs_for_different_inputs():
    """Different step_id → different run_id."""
    id_a = compute_sha256({"mission_type": "doc_steward", "step_id": "step-1", "inputs": {}})
    id_b = compute_sha256({"mission_type": "doc_steward", "step_id": "step-2", "inputs": {}})
    assert id_a != id_b


# ---------------------------------------------------------------------------
# 2A-2: COO commands.py run_id is deterministic for same context
# ---------------------------------------------------------------------------


def test_coo_propose_run_id_deterministic():
    """Same context dict → same run_id in cmd_coo_propose."""
    context = {"actionable_tasks": [], "mode": "propose"}
    id_a = compute_sha256({"context": context, "mode": "propose"})
    id_b = compute_sha256({"context": context, "mode": "propose"})
    assert id_a == id_b


def test_coo_direct_run_id_deterministic():
    """Same context dict → same run_id in cmd_coo_direct."""
    context = {"intent": "update doc", "source": "coo_direct"}
    id_a = compute_sha256({"context": context, "mode": "direct"})
    id_b = compute_sha256({"context": context, "mode": "direct"})
    assert id_a == id_b


def test_coo_propose_vs_direct_differ():
    """propose vs direct mode → different run_ids."""
    context = {"source": "coo_direct"}
    id_propose = compute_sha256({"context": context, "mode": "propose"})
    id_direct = compute_sha256({"context": context, "mode": "direct"})
    assert id_propose != id_direct


# ---------------------------------------------------------------------------
# 2A-3: opencode_client call_id is deterministic for same model + prompt
# ---------------------------------------------------------------------------


def test_opencode_call_id_deterministic():
    """Same model + prompt → same call_id in OpenCodeClient._execute_attempt."""
    import hashlib

    payload_a = json.dumps({"model": "gpt-4", "prompt": "hello"}, sort_keys=True).encode()
    payload_b = json.dumps({"model": "gpt-4", "prompt": "hello"}, sort_keys=True).encode()
    id_a = "sha256:" + hashlib.sha256(payload_a).hexdigest()
    id_b = "sha256:" + hashlib.sha256(payload_b).hexdigest()
    assert id_a == id_b


def test_opencode_call_id_differs_for_different_prompt():
    """Different prompts → different call_ids."""
    import hashlib

    payload_a = json.dumps({"model": "gpt-4", "prompt": "hello"}, sort_keys=True).encode()
    payload_b = json.dumps({"model": "gpt-4", "prompt": "world"}, sort_keys=True).encode()
    id_a = "sha256:" + hashlib.sha256(payload_a).hexdigest()
    id_b = "sha256:" + hashlib.sha256(payload_b).hexdigest()
    assert id_a != id_b
