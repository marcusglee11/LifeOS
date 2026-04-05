"""
Challenger review implementation with rework loop (Branch A7).

Implements spec sections 8.3 and 9.3:
- Weakest-claim stress test on every tier
- Contradiction ledger completeness check for T2/T3
- material_issue triggers rework once; persistent issue forces Revise
- Bounded retries on Challenger schema validation (max 2)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from .models import CouncilBlockedError

if TYPE_CHECKING:
    from .schema_gate import SchemaGateResult

# Tiers requiring contradiction ledger
_LEDGER_TIERS = frozenset({"T2", "T3"})

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class ChallengerResult:
    """Structured result of Challenger review of Chair synthesis."""

    weakest_claim: str
    stress_test: str
    material_issue: bool
    issue_class: str  # see VALID_ISSUE_CLASSES
    severity: str  # "p0" | "p1" | "p2"
    required_action: str  # "rework_synthesis" | "downgrade_verdict" | "block" | "none"
    notes: str

    # T2/T3 fields (None when not applicable)
    ledger_completeness_ok: bool | None = None
    missing_disagreements: list[str] = field(default_factory=list)

    VALID_ISSUE_CLASSES: frozenset = field(
        default=frozenset(
            {
                "unsupported_verdict",
                "missing_contradiction_ledger",
                "evidence_misuse",
                "coverage_gap",
                "other",
                "none",
            }
        ),
        init=False,
        repr=False,
        compare=False,
    )

    VALID_SEVERITIES: frozenset = field(
        default=frozenset({"p0", "p1", "p2"}), init=False, repr=False, compare=False
    )

    VALID_ACTIONS: frozenset = field(
        default=frozenset(
            {
                "rework_synthesis",
                "downgrade_verdict",
                "block",
                "none",
            }
        ),
        init=False,
        repr=False,
        compare=False,
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "weakest_claim": self.weakest_claim,
            "stress_test": self.stress_test,
            "material_issue": self.material_issue,
            "issue_class": self.issue_class,
            "severity": self.severity,
            "required_action": self.required_action,
            "notes": self.notes,
            "ledger_completeness_ok": self.ledger_completeness_ok,
            "missing_disagreements": list(self.missing_disagreements),
        }


# ---------------------------------------------------------------------------
# Callback type aliases
# ---------------------------------------------------------------------------

# (synthesis_output, context) -> raw_challenger_output dict
ChallengerExecutor = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]

# (raw_output, run_type, tier) -> SchemaGateResult
ChallengerValidator = Callable[[dict[str, Any], str, str], "SchemaGateResult"]


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def evaluate_challenger(
    synthesis_output: dict[str, Any],
    plan: Any,
    executor: ChallengerExecutor,
    validator: ChallengerValidator,
    lens_results: list[dict[str, Any]] | None = None,
    synthesis_rework_count: int = 0,
    max_retries: int = 2,
) -> ChallengerResult:
    """
    Run Challenger review of Chair synthesis.

    Steps:
    1. Call executor(synthesis_output, context) to get raw challenger output.
    2. Validate via validator(raw_output, run_type, tier).
    3. Retry up to max_retries if validation fails.
    4. Parse validated output into ChallengerResult.
    5. For T2/T3: include ledger_completeness_ok / missing_disagreements fields.

    Raises:
        CouncilBlockedError: if validation is exhausted after max_retries.
    """
    core = plan.core
    context: dict[str, Any] = {
        "lens_results": lens_results or [],
        "rework_count": synthesis_rework_count,
    }

    errors: list[str] = []
    normalized: dict[str, Any] | None = None
    raw_output: dict[str, Any] | None = None

    for _attempt in range(max_retries + 1):
        try:
            raw_output = executor(synthesis_output, context)
        except Exception as exc:
            errors.append(f"{type(exc).__name__}: {exc}")
            continue

        gate = validator(raw_output, core.run_type, core.tier)

        if gate.valid:
            normalized = gate.normalized_output
            break
        else:
            errors.extend(gate.errors)

    if normalized is None:
        raise CouncilBlockedError(
            "CHALLENGER_SCHEMA_FAILURE",
            f"Challenger output failed schema gate after {max_retries} retries: {errors}",
        )

    return _parse_challenger_result(normalized, core.tier)


def apply_challenger_outcome(
    challenger_result: ChallengerResult,
    synthesis_rework_count: int,
) -> dict[str, Any]:
    """
    Determine FSM action from Challenger result and rework counter.

    Returns dict with:
    - action: "proceed" | "rework" | "force_revise"
    - verdict_override: str | None
    - decision_status: str | None
    - closure_gate_status: str | None
    """
    if not challenger_result.material_issue:
        return {
            "action": "proceed",
            "verdict_override": None,
            "decision_status": None,
            "closure_gate_status": None,
        }

    if synthesis_rework_count == 0:
        # First material issue: trigger one rework cycle
        return {
            "action": "rework",
            "verdict_override": None,
            "decision_status": None,
            "closure_gate_status": None,
        }

    # Persistent issue after rework: force Revise + degraded status
    return {
        "action": "force_revise",
        "verdict_override": "Revise",
        "decision_status": "DEGRADED_CHALLENGER",
        "closure_gate_status": "SKIPPED_DEGRADED_REVISE",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_challenger_result(normalized: dict[str, Any], tier: str) -> ChallengerResult:
    """Parse a validated challenger output dict into a ChallengerResult."""
    weakest_claim = str(normalized.get("weakest_claim", ""))
    stress_test = str(normalized.get("stress_test", ""))
    material_issue = bool(normalized.get("material_issue", False))
    issue_class = str(normalized.get("issue_class", "none"))
    severity = str(normalized.get("severity", "p2"))
    required_action = str(normalized.get("required_action", "none"))
    notes = str(normalized.get("notes", ""))

    # T2/T3: extract ledger fields if present; default to None if absent
    ledger_completeness_ok: bool | None = None
    missing_disagreements: list[str] = []

    if tier in _LEDGER_TIERS:
        raw_ok = normalized.get("ledger_completeness_ok")
        if raw_ok is not None:
            ledger_completeness_ok = bool(raw_ok)
        raw_missing = normalized.get("missing_disagreements")
        if isinstance(raw_missing, list):
            missing_disagreements = [str(x) for x in raw_missing]

    return ChallengerResult(
        weakest_claim=weakest_claim,
        stress_test=stress_test,
        material_issue=material_issue,
        issue_class=issue_class,
        severity=severity,
        required_action=required_action,
        notes=notes,
        ledger_completeness_ok=ledger_completeness_ok,
        missing_disagreements=missing_disagreements,
    )
