"""
Typed models for the policy-driven council runtime.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# v2.2.1 Constants
# ---------------------------------------------------------------------------

# Tiers
TIER_T0 = "T0"
TIER_T1 = "T1"
TIER_T2 = "T2"
TIER_T3 = "T3"

# Run types
RUN_TYPE_REVIEW = "review"
RUN_TYPE_ADVISORY = "advisory"

# Verdicts (v2.2.1: "Go with Fixes" replaced by "Revise")
VERDICT_ACCEPT = "Accept"
VERDICT_REVISE = "Revise"
VERDICT_REJECT = "Reject"

# Decision status
DECISION_STATUS_NORMAL = "NORMAL"
DECISION_STATUS_DEGRADED_COVERAGE = "DEGRADED_COVERAGE"
DECISION_STATUS_DEGRADED_CHALLENGER = "DEGRADED_CHALLENGER"

# Issue classes
ISSUE_CLASS_UNSUPPORTED_VERDICT = "unsupported_verdict"
ISSUE_CLASS_MISSING_LEDGER = "missing_contradiction_ledger"
ISSUE_CLASS_EVIDENCE_MISUSE = "evidence_misuse"
ISSUE_CLASS_COVERAGE_GAP = "coverage_gap"
ISSUE_CLASS_OTHER = "other"

# Severity
SEVERITY_P0 = "p0"
SEVERITY_P1 = "p1"
SEVERITY_P2 = "p2"

# Required actions
REQUIRED_ACTION_REWORK_SYNTHESIS = "rework_synthesis"
REQUIRED_ACTION_DOWNGRADE_VERDICT = "downgrade_verdict"
REQUIRED_ACTION_BLOCK = "block"


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


# ---------------------------------------------------------------------------
# v2.2.1 Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CouncilRunPlanCore:
    """
    Deterministic execution plan core — excludes non-deterministic fields
    (run_id, timestamp). Suitable for canonical hashing.
    """

    aur_id: str
    tier: str
    run_type: str
    topology: str
    required_lenses: tuple[str, ...]
    model_assignments: Mapping[str, str]
    lens_role_map: Mapping[str, str]

    independence_required: str
    independence_satisfied: bool
    independent_lenses: tuple[str, ...]

    compliance_flags: Mapping[str, Any]
    override_active: bool
    override_rationale: str | None

    challenger_required: bool
    contradiction_ledger_required: bool
    closure_gate_required: bool

    mandatory_lenses: tuple[str, ...]
    waivable_lenses: tuple[str, ...]
    padded_lenses: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a deterministic JSON-serializable shape (all keys sorted)."""
        return {
            "aur_id": self.aur_id,
            "challenger_required": self.challenger_required,
            "closure_gate_required": self.closure_gate_required,
            "compliance_flags": dict(sorted(self.compliance_flags.items())),
            "contradiction_ledger_required": self.contradiction_ledger_required,
            "independence_required": self.independence_required,
            "independence_satisfied": self.independence_satisfied,
            "independent_lenses": sorted(self.independent_lenses),
            "lens_role_map": dict(sorted(self.lens_role_map.items())),
            "mandatory_lenses": sorted(self.mandatory_lenses),
            "model_assignments": dict(sorted(self.model_assignments.items())),
            "override_active": self.override_active,
            "override_rationale": self.override_rationale,
            "padded_lenses": sorted(self.padded_lenses),
            "required_lenses": sorted(self.required_lenses),
            "run_type": self.run_type,
            "tier": self.tier,
            "topology": self.topology,
            "waivable_lenses": sorted(self.waivable_lenses),
        }


@dataclass(frozen=True)
class CouncilRunMeta:
    """
    Non-deterministic run metadata: run_id, timestamp, and the hash of the
    deterministic core so both can be linked without the core being mutable.
    """

    run_id: str
    timestamp: str
    plan_core_hash: str


def compute_plan_core_hash(core: CouncilRunPlanCore) -> str:
    """Compute SHA-256 canonical hash of a CouncilRunPlanCore."""
    canonical = json.dumps(core.to_dict(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class ChallengerResult:
    """Result of the Challenger review pass."""

    weakest_claim: str
    stress_test: str
    material_issue: bool
    issue_class: str
    severity: str
    required_action: str
    notes: str
    # T2/T3 fields — optional; None for T0/T1
    ledger_completeness_ok: bool | None = None
    missing_disagreements: list[str] | None = None


@dataclass
class ContradictionLedgerEntry:
    """A single entry in the contradiction ledger."""

    topic: str
    positions: dict[str, str]  # lens_name -> claim_id
    resolution: dict[str, Any]  # decision, rationale, refs|assumption
    status: str  # "resolved" | "unresolved"


def generate_run_id() -> str:
    """Generate a unique run identifier."""
    return f"council_{uuid.uuid4().hex}"
