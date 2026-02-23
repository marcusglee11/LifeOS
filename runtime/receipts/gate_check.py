"""
GateCheck evaluator and rollup for LifeOS build gates.

Provides:
- GateCheck dataclass
- build_gate_results: build sorted gate results dict
- compute_gate_rollup: compute overall status from gate results
- make_artefact_ref: build an artefact reference dict
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_VALID_GATE_STATUSES = {"PASS", "FAIL", "WARN", "BLOCKED", "SKIP"}


@dataclass(frozen=True)
class GateCheck:
    """A single gate check result."""
    gate_id: str
    status: str  # PASS, FAIL, WARN, BLOCKED, SKIP
    blocking: bool
    evidence_ref: dict | None = None

    def to_dict(self) -> dict:
        d = {
            "gate_id": self.gate_id,
            "status": self.status,
            "blocking": self.blocking,
        }
        if self.evidence_ref is not None:
            d["evidence_ref"] = self.evidence_ref
        return d


def build_gate_results(gates: list[dict | GateCheck]) -> dict:
    """
    Build a sorted gate results dict keyed by gate_id.

    Args:
        gates: List of gate result dicts or GateCheck instances.

    Returns:
        Dict mapping gate_id -> gate result dict, sorted by gate_id.
    """
    result = {}
    for gate in gates:
        if isinstance(gate, GateCheck):
            g = gate.to_dict()
        else:
            g = dict(gate)
        result[g["gate_id"]] = g
    # Return sorted by gate_id
    return dict(sorted(result.items()))


def compute_gate_rollup(gates: list[dict | GateCheck]) -> dict:
    """
    Compute overall gate rollup status from a list of gate results.

    Invariant (S13.2):
    - Any blocking FAIL -> overall FAIL
    - Any blocking BLOCKED -> overall BLOCKED (if no blocking FAIL)
    - Any non-blocking FAIL/WARN -> overall WARN (if no harder failures)
    - All PASS/SKIP -> overall PASS

    Args:
        gates: List of gate result dicts or GateCheck instances.

    Returns:
        Dict with 'overall_status' key.

    Raises:
        ValueError: If a gate contains an unknown status.
    """
    gate_list = []
    for g in gates:
        if isinstance(g, GateCheck):
            gate_list.append(g.to_dict())
        else:
            gate_list.append(g)

    overall = "PASS"

    for gate in gate_list:
        status = gate.get("status", "PASS")
        blocking = gate.get("blocking", True)
        if status not in _VALID_GATE_STATUSES:
            gate_id = gate.get("gate_id", "<unknown>")
            raise ValueError(f"Unknown gate status for {gate_id!r}: {status!r}")

        if status == "FAIL" and blocking:
            overall = "FAIL"
            break  # Worst possible -- stop early
        elif status == "BLOCKED" and blocking:
            if overall != "FAIL":
                overall = "BLOCKED"
        elif status in ("FAIL", "WARN") and not blocking:
            if overall not in ("FAIL", "BLOCKED"):
                overall = "WARN"
        elif status == "WARN" and blocking:
            if overall not in ("FAIL", "BLOCKED"):
                overall = "WARN"

    return {"overall_status": overall}


def make_artefact_ref(
    ref_type: str,
    location: str,
    sha256: str | None = None,
) -> dict:
    """
    Build an artefact reference dict.

    Args:
        ref_type: Type of reference (e.g., 'file', 'store', 'url').
        location: Location string (must be non-empty).
        sha256: Optional SHA-256 hex string (64 chars).

    Returns:
        Artefact reference dict.

    Raises:
        ValueError: If location is empty.
    """
    if not location:
        raise ValueError("make_artefact_ref: location must be non-empty")
    ref: dict[str, Any] = {"ref_type": ref_type, "location": location}
    if sha256 is not None:
        ref["sha256"] = sha256
    return ref
