"""
Typed models for the policy-driven council runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
import uuid


class CouncilRuntimeError(Exception):
    """Base error class for council runtime failures."""


class CouncilBlockedError(CouncilRuntimeError):
    """Raised when protocol-required preconditions are not satisfied."""

    def __init__(self, category: str, detail: str):
        self.category = category
        self.detail = detail
        super().__init__(f"[{category}] {detail}")


@dataclass(frozen=True)
class CouncilRunPlan:
    """
    Immutable execution plan compiled from CCP metadata and council policy.
    """

    aur_id: str
    run_id: str
    timestamp: str

    mode: str
    topology: str
    required_seats: tuple[str, ...]
    model_assignments: Mapping[str, str]
    seat_role_map: Mapping[str, str]

    independence_required: str
    independence_satisfied: bool
    independent_seats: tuple[str, ...]

    compliance_flags: Mapping[str, Any]
    override_active: bool
    override_rationale: str | None

    cochair_required: bool
    contradiction_ledger_required: bool
    closure_gate_required: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-serializable shape."""
        return {
            "aur_id": self.aur_id,
            "closure_gate_required": self.closure_gate_required,
            "cochair_required": self.cochair_required,
            "compliance_flags": dict(sorted(self.compliance_flags.items())),
            "contradiction_ledger_required": self.contradiction_ledger_required,
            "independence_required": self.independence_required,
            "independence_satisfied": self.independence_satisfied,
            "independent_seats": list(self.independent_seats),
            "mode": self.mode,
            "model_assignments": dict(sorted(self.model_assignments.items())),
            "override_active": self.override_active,
            "override_rationale": self.override_rationale,
            "required_seats": list(self.required_seats),
            "run_id": self.run_id,
            "seat_role_map": dict(sorted(self.seat_role_map.items())),
            "timestamp": self.timestamp,
            "topology": self.topology,
        }


@dataclass
class CouncilTransition:
    """A state transition entry for the run audit trail."""

    from_state: str
    to_state: str
    reason: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "details": dict(sorted(self.details.items())) if self.details else {},
            "from_state": self.from_state,
            "reason": self.reason,
            "timestamp": self.timestamp,
            "to_state": self.to_state,
        }


@dataclass
class CouncilSeatResult:
    """Normalized seat execution result after schema-gate processing."""

    seat: str
    status: str
    model: str
    raw_output: dict[str, Any] | str
    normalized_output: dict[str, Any] | None
    retries_used: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    waived: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "errors": list(self.errors),
            "model": self.model,
            "normalized_output": self.normalized_output,
            "raw_output": self.raw_output,
            "retries_used": self.retries_used,
            "seat": self.seat,
            "status": self.status,
            "waived": self.waived,
            "warnings": list(self.warnings),
        }


@dataclass
class CouncilRuntimeResult:
    """Terminal council runtime result."""

    status: str
    run_log: dict[str, Any]
    decision_payload: dict[str, Any]
    block_report: dict[str, Any] | None = None


def generate_run_id() -> str:
    """Generate a unique run identifier."""
    return f"council_{uuid.uuid4().hex}"
