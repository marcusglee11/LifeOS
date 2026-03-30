"""Tests for runtime/receipts/gate_check.py"""

import pytest

from runtime.receipts.gate_check import (
    build_gate_results,
    compute_gate_rollup,
    make_artefact_ref,
)


def test_build_gate_results_sorted():
    gates = [
        {"gate_id": "c-gate", "status": "PASS", "blocking": True},
        {"gate_id": "a-gate", "status": "PASS", "blocking": True},
        {"gate_id": "b-gate", "status": "WARN", "blocking": False},
    ]
    result = build_gate_results(gates)
    assert list(result.keys()) == ["a-gate", "b-gate", "c-gate"]


def test_rollup_all_pass():
    gates = [
        {"gate_id": "g1", "status": "PASS", "blocking": True},
        {"gate_id": "g2", "status": "PASS", "blocking": True},
    ]
    rollup = compute_gate_rollup(gates)
    assert rollup["overall_status"] == "PASS"


def test_rollup_blocking_fail():
    gates = [
        {"gate_id": "g1", "status": "PASS", "blocking": True},
        {"gate_id": "g2", "status": "FAIL", "blocking": True},
    ]
    rollup = compute_gate_rollup(gates)
    assert rollup["overall_status"] == "FAIL"


def test_rollup_non_blocking_warn():
    gates = [
        {"gate_id": "g1", "status": "PASS", "blocking": True},
        {"gate_id": "g2", "status": "WARN", "blocking": False},
    ]
    rollup = compute_gate_rollup(gates)
    assert rollup["overall_status"] == "WARN"


def test_rollup_blocking_blocked():
    gates = [
        {"gate_id": "g1", "status": "PASS", "blocking": True},
        {"gate_id": "g2", "status": "BLOCKED", "blocking": True},
    ]
    rollup = compute_gate_rollup(gates)
    assert rollup["overall_status"] == "BLOCKED"


def test_rollup_non_blocking_fail():
    """Non-blocking FAIL should result in WARN, not FAIL."""
    gates = [
        {"gate_id": "g1", "status": "PASS", "blocking": True},
        {"gate_id": "g2", "status": "FAIL", "blocking": False},
    ]
    rollup = compute_gate_rollup(gates)
    assert rollup["overall_status"] == "WARN"


def test_make_artefact_ref_rejects_empty():
    with pytest.raises(ValueError, match="non-empty"):
        make_artefact_ref("file", "")


def test_rollup_rejects_unknown_status():
    gates = [{"gate_id": "g1", "status": "UNKNOWN", "blocking": True}]
    with pytest.raises(ValueError, match="Unknown gate status"):
        compute_gate_rollup(gates)
