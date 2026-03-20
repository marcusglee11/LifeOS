# Review Packet: Council Runtime Implementation for Claude Code v1.0

## Scope
This packet hands off the approved implementation from:
- `artifacts/plans/Council_Runtime_Plan.V1.0md.md`

Implemented capabilities:
- New council runtime policy config (`council_policy.yaml`) for protocol-driven mode/seat/independence rules
- New `runtime/orchestration/council/` runtime package (`models`, `policy`, `compiler`, `schema_gate`, `fsm`)
- Review mission integration seam in `runtime/orchestration/missions/review.py` behind `use_council_runtime` opt-in
- New council-runtime tests and review mission integration tests

## Reviewer Brief (Claude Code)
Please review for:
- Protocol fidelity: mode resolution, independence MUST/SHOULD handling, schema gate behavior, deterministic transitions
- Fail-closed behavior for malformed CCP/policy and missing required sections
- Backward compatibility of the review mission when `use_council_runtime` is false
- Test completeness and edge-case coverage

## Branch
- `main`

## Base Commit
- `10dc07b` (working tree contains uncommitted council-runtime changes)

## Change Inventory
- `config/policy/council_policy.yaml`
- `runtime/orchestration/council/__init__.py`
- `runtime/orchestration/council/models.py`
- `runtime/orchestration/council/policy.py`
- `runtime/orchestration/council/compiler.py`
- `runtime/orchestration/council/schema_gate.py`
- `runtime/orchestration/council/fsm.py`
- `runtime/orchestration/missions/review.py`
- `runtime/tests/orchestration/council/test_compiler.py`
- `runtime/tests/orchestration/council/test_schema_gate.py`
- `runtime/tests/orchestration/council/test_fsm.py`
- `runtime/tests/orchestration/missions/test_review_council_runtime.py`

## Verification
Executed on 2026-02-22 (UTC), last run at 2026-02-22T10:59:53Z.

1. Full baseline test sweep before packet generation:
- `pytest runtime/tests -q`
- Result: FAIL (known environment-related failures), summary:
  - 3 failed, 1704 passed, 8 skipped, 6 warnings
  - Failed tests:
    - `runtime/tests/test_coo_worktree_marker_receipt.py::test_coo_e2e_marker_receipt_projects_canonical_capsule`
    - `runtime/tests/test_opencode_stage1_5_live.py::TestZenModelComparison::test_model_responds[opencode/kimi-k2.5-free]`
    - `runtime/tests/test_opencode_stage1_5_live.py::TestZenModelComparison::test_model_responds[opencode/glm-5-free]`

2. Council runtime targeted tests:
- `pytest -q runtime/tests/orchestration/council runtime/tests/orchestration/missions/test_review_council_runtime.py`
- Result: PASS (15 passed in 4.24s)

3. Full post-change sweep (packet-only doc artifact added):
- `pytest runtime/tests -q`
- Result: FAIL (same known environment-related failures), summary:
  - 3 failed, 1704 passed, 8 skipped, 6 warnings
  - Failed tests:
    - `runtime/tests/test_coo_worktree_marker_receipt.py::test_coo_e2e_marker_receipt_projects_canonical_capsule`
    - `runtime/tests/test_opencode_stage1_5_live.py::TestZenModelComparison::test_model_responds[opencode/kimi-k2.5-free]`
    - `runtime/tests/test_opencode_stage1_5_live.py::TestZenModelComparison::test_model_responds[opencode/glm-5-free]`

## Appendix A: Flattened Code (Full)

### FILE: `config/policy/council_policy.yaml`

```yaml
protocol_version: "1.3"

required_ccp_sections:
  - objective
  - scope
  - constraints
  - artifacts

enums:
  aur_type: [governance, spec, code, doc, plan, other]
  change_class: [new, amend, refactor, hygiene, bugfix]
  blast_radius: [local, module, system, ecosystem]
  reversibility: [easy, moderate, hard]
  uncertainty: [low, medium, high]
  touches: [governance_protocol, tier_activation, runtime_core, interfaces, prompts, tests, docs_only]
  verdict: [Accept, "Go with Fixes", Reject]
  mode: [M0_FAST, M1_STANDARD, M2_FULL]
  topology: [MONO, HYBRID, DISTRIBUTED]

modes:
  default: M1_STANDARD
  M2_FULL_triggers:
    - "touches includes governance_protocol"
    - "touches includes tier_activation"
    - "touches includes runtime_core"
    - "safety_critical == true"
    - "blast_radius in [system, ecosystem] and reversibility == hard"
    - "uncertainty == high and blast_radius != local"
  M0_FAST_conditions:
    - "aur_type in [doc, plan, other]"
    - "touches == [docs_only] or (touches excludes runtime_core and touches excludes interfaces and touches excludes governance_protocol)"
    - "blast_radius == local"
    - "reversibility == easy"
    - "safety_critical == false"
    - "uncertainty == low"

seats:
  officers:
    Chair:
      required_in: [M0_FAST, M1_STANDARD, M2_FULL]
    CoChair:
      required_in: [M1_STANDARD, M2_FULL]
      optional_in: [M0_FAST]
  reviewers:
    M0_FAST: [L1UnifiedReviewer]
    M1_STANDARD: [Chair, CoChair]
    M2_FULL:
      - Chair
      - CoChair
      - Architect
      - Alignment
      - StructuralOperational
      - Technical
      - Testing
      - RiskAdversarial
      - Simplicity
      - Determinism
      - Governance

seat_role_map:
  Chair: reviewer_architect
  CoChair: reviewer_architect
  L1UnifiedReviewer: reviewer_architect
  Architect: reviewer_architect
  Alignment: reviewer_architect
  StructuralOperational: reviewer_architect
  Technical: reviewer_architect
  Testing: reviewer_architect
  RiskAdversarial: reviewer_security
  Simplicity: reviewer_architect
  Determinism: reviewer_architect
  Governance: reviewer_architect

independence:
  must_conditions:
    triggers:
      - "safety_critical == true"
      - "touches includes governance_protocol"
      - "touches includes tier_activation"
    enforcement: "At least one of RiskAdversarial or Governance must run on independent model family"
  should_conditions:
    triggers:
      - "touches includes runtime_core"
      - "uncertainty == high and blast_radius != local"
    enforcement: "At least one of RiskAdversarial or Governance should run on independent model family"

schema_gate:
  max_retry_cycles: 2
  required_sections:
    - verdict
    - key_findings
    - risks
    - fixes
    - confidence
    - assumptions
    - complexity_budget
    - operator_view
  evidence_rule: "Material claims require REF: citation or ASSUMPTION label"

closure:
  max_prompt_closure_cycles: 2
  build_script: "scripts/closure/build_closure_bundle.py"
  validate_script: "scripts/closure/validate_closure_bundle.py"

bootstrap:
  max_consecutive_without_cso: 2
  restore_deadline_hours: 24
  safety_critical_requires_ceo_approval: true

model_families:
  anthropic:
    - claude-opus-4-5
    - claude-sonnet-4-5
    - claude-haiku-4-5
  openai:
    - gpt-4o
    - o1
    - o3-mini
  google:
    - gemini-2.0-flash
    - gemini-2.0-pro

```

### FILE: `runtime/orchestration/council/__init__.py`

```python
"""Policy-driven council runtime package."""

from .compiler import compile_council_run_plan
from .fsm import CouncilFSM
from .models import (
    CouncilBlockedError,
    CouncilRunPlan,
    CouncilRuntimeError,
    CouncilRuntimeResult,
    CouncilSeatResult,
    CouncilTransition,
)
from .policy import CouncilPolicy, evaluate_expression, load_council_policy, resolve_model_family
from .schema_gate import SchemaGateResult, validate_seat_output

__all__ = [
    "CouncilBlockedError",
    "CouncilFSM",
    "CouncilPolicy",
    "CouncilRunPlan",
    "CouncilRuntimeError",
    "CouncilRuntimeResult",
    "CouncilSeatResult",
    "CouncilTransition",
    "SchemaGateResult",
    "compile_council_run_plan",
    "evaluate_expression",
    "load_council_policy",
    "resolve_model_family",
    "validate_seat_output",
]

```

### FILE: `runtime/orchestration/council/models.py`

```python
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

```

### FILE: `runtime/orchestration/council/policy.py`

```python
"""
Council policy loading and expression evaluation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from .models import CouncilRuntimeError


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_policy_path() -> Path:
    return _repo_root() / "config" / "policy" / "council_policy.yaml"


def _strip_outer_parens(expr: str) -> str:
    expr = expr.strip()
    while expr.startswith("(") and expr.endswith(")"):
        depth = 0
        balanced = True
        for i, ch in enumerate(expr):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth < 0:
                    balanced = False
                    break
                if depth == 0 and i != len(expr) - 1:
                    balanced = False
                    break
        if not balanced or depth != 0:
            break
        expr = expr[1:-1].strip()
    return expr


def _split_top_level(expr: str, op: str) -> list[str]:
    pieces: list[str] = []
    depth = 0
    i = 0
    start = 0
    token = f" {op} "
    while i < len(expr):
        ch = expr[i]
        if ch == "(":
            depth += 1
            i += 1
            continue
        if ch == ")":
            depth -= 1
            i += 1
            continue
        if depth == 0 and expr.startswith(token, i):
            pieces.append(expr[start:i].strip())
            i += len(token)
            start = i
            continue
        i += 1
    pieces.append(expr[start:].strip())
    return [piece for piece in pieces if piece]


def _parse_literal(raw: str) -> Any:
    value = raw.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_literal(part) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.isdigit():
        return int(value)
    return value


def _get_path_value(data: Mapping[str, Any], field_path: str) -> Any:
    current: Any = data
    for part in field_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _eval_predicate(predicate: str, metadata: Mapping[str, Any]) -> bool:
    normalized = " ".join(predicate.strip().split())
    if " includes " in normalized:
        field, rhs = normalized.split(" includes ", 1)
        lhs_values = _as_list(_get_path_value(metadata, field.strip()))
        rhs_value = _parse_literal(rhs)
        return rhs_value in lhs_values
    if " excludes " in normalized:
        field, rhs = normalized.split(" excludes ", 1)
        lhs_values = _as_list(_get_path_value(metadata, field.strip()))
        rhs_value = _parse_literal(rhs)
        return rhs_value not in lhs_values
    if " not in " in normalized:
        field, rhs = normalized.split(" not in ", 1)
        lhs_value = _get_path_value(metadata, field.strip())
        rhs_values = _as_list(_parse_literal(rhs))
        return lhs_value not in rhs_values
    if " in " in normalized:
        field, rhs = normalized.split(" in ", 1)
        lhs_value = _get_path_value(metadata, field.strip())
        rhs_values = _as_list(_parse_literal(rhs))
        return lhs_value in rhs_values
    if " == " in normalized:
        field, rhs = normalized.split(" == ", 1)
        lhs_value = _get_path_value(metadata, field.strip())
        rhs_value = _parse_literal(rhs)
        if isinstance(rhs_value, list):
            lhs_values = _as_list(lhs_value)
            return sorted(lhs_values) == sorted(rhs_value)
        return lhs_value == rhs_value
    if " != " in normalized:
        field, rhs = normalized.split(" != ", 1)
        lhs_value = _get_path_value(metadata, field.strip())
        rhs_value = _parse_literal(rhs)
        if isinstance(rhs_value, list):
            lhs_values = _as_list(lhs_value)
            return sorted(lhs_values) != sorted(rhs_value)
        return lhs_value != rhs_value
    raise CouncilRuntimeError(f"Unsupported policy predicate: {predicate}")


def evaluate_expression(expression: str, metadata: Mapping[str, Any]) -> bool:
    """
    Evaluate a council policy expression against CCP metadata.

    Supported operators:
    - and / or with parenthesis grouping
    - includes / excludes for list-like fields
    - == / !=
    - in / not in
    """
    expr = _strip_outer_parens(expression.strip())
    if not expr:
        return False

    or_parts = _split_top_level(expr, "or")
    if len(or_parts) > 1:
        return any(evaluate_expression(part, metadata) for part in or_parts)

    and_parts = _split_top_level(expr, "and")
    if len(and_parts) > 1:
        return all(evaluate_expression(part, metadata) for part in and_parts)

    return _eval_predicate(expr, metadata)


def resolve_model_family(model_name: str, registry: Mapping[str, list[str]]) -> str:
    """
    Resolve model family from explicit registry, then fallback heuristics.
    """
    lower_name = (model_name or "").lower()
    for family, models in registry.items():
        for declared in models:
            d = declared.lower()
            if lower_name == d or lower_name.endswith(f"/{d}") or d in lower_name:
                return family
    if "claude" in lower_name:
        return "anthropic"
    if "gpt" in lower_name or lower_name.startswith("o1") or lower_name.startswith("o3"):
        return "openai"
    if "gemini" in lower_name:
        return "google"
    if "/" in lower_name:
        return lower_name.split("/", 1)[0]
    return "unknown"


@dataclass(frozen=True)
class CouncilPolicy:
    """Structured accessor for `config/policy/council_policy.yaml`."""

    raw: Mapping[str, Any]

    @property
    def protocol_version(self) -> str:
        return str(self.raw.get("protocol_version", "unknown"))

    @property
    def enums(self) -> Mapping[str, list[Any]]:
        return self.raw.get("enums", {})

    @property
    def required_ccp_sections(self) -> tuple[str, ...]:
        sections = self.raw.get("required_ccp_sections", [])
        return tuple(str(s) for s in sections)

    @property
    def schema_gate_required_sections(self) -> tuple[str, ...]:
        gate = self.raw.get("schema_gate", {})
        return tuple(str(s) for s in gate.get("required_sections", []))

    @property
    def schema_gate_retry_cap(self) -> int:
        gate = self.raw.get("schema_gate", {})
        retry_cap = gate.get("max_retry_cycles", 2)
        if not isinstance(retry_cap, int) or retry_cap < 0:
            return 2
        return retry_cap

    @property
    def closure_retry_cap(self) -> int:
        closure = self.raw.get("closure", {})
        retry_cap = closure.get("max_prompt_closure_cycles", 2)
        if not isinstance(retry_cap, int) or retry_cap < 0:
            return 2
        return retry_cap

    @property
    def seat_role_map(self) -> Mapping[str, str]:
        return self.raw.get("seat_role_map", {})

    @property
    def model_families(self) -> Mapping[str, list[str]]:
        return self.raw.get("model_families", {})

    @property
    def mode_default(self) -> str:
        return str(self.raw.get("modes", {}).get("default", "M1_STANDARD"))

    def mode_m2_triggers(self) -> tuple[str, ...]:
        entries = self.raw.get("modes", {}).get("M2_FULL_triggers", [])
        return tuple(str(s) for s in entries)

    def mode_m0_conditions(self) -> tuple[str, ...]:
        entries = self.raw.get("modes", {}).get("M0_FAST_conditions", [])
        return tuple(str(s) for s in entries)

    def required_seats_for_mode(self, mode: str) -> tuple[str, ...]:
        reviewers = self.raw.get("seats", {}).get("reviewers", {})
        seats = reviewers.get(mode, [])
        return tuple(str(seat) for seat in seats)

    def independence_must_triggers(self) -> tuple[str, ...]:
        triggers = (
            self.raw.get("independence", {})
            .get("must_conditions", {})
            .get("triggers", [])
        )
        return tuple(str(s) for s in triggers)

    def independence_should_triggers(self) -> tuple[str, ...]:
        triggers = (
            self.raw.get("independence", {})
            .get("should_conditions", {})
            .get("triggers", [])
        )
        return tuple(str(s) for s in triggers)

    @property
    def bootstrap_policy(self) -> Mapping[str, Any]:
        return self.raw.get("bootstrap", {})


def load_council_policy(policy_path: str | Path | None = None) -> CouncilPolicy:
    """
    Load council runtime policy from YAML.
    """
    path = Path(policy_path) if policy_path else _default_policy_path()
    if not path.exists():
        raise CouncilRuntimeError(f"Council policy not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle)
    if not isinstance(parsed, dict):
        raise CouncilRuntimeError(f"Council policy is invalid: {path}")
    return CouncilPolicy(raw=parsed)

```

### FILE: `runtime/orchestration/council/compiler.py`

```python
"""
Compiler for producing an immutable CouncilRunPlan from CCP + policy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from runtime.agents.models import resolve_model_auto, load_model_config

from .models import CouncilBlockedError, CouncilRunPlan, generate_run_id
from .policy import CouncilPolicy, evaluate_expression, resolve_model_family


def _normalize_metadata(ccp: Mapping[str, Any]) -> dict[str, Any]:
    header = ccp.get("header")
    if isinstance(header, dict):
        meta = dict(header)
    else:
        meta = dict(ccp)
    touches = meta.get("touches")
    if touches is None:
        meta["touches"] = []
    elif isinstance(touches, str):
        meta["touches"] = [touches]
    elif isinstance(touches, (tuple, set)):
        meta["touches"] = list(touches)
    return meta


def _validate_required_sections(
    ccp: Mapping[str, Any], required_sections: tuple[str, ...]
) -> None:
    sections = ccp.get("sections", {})
    if not isinstance(sections, Mapping):
        sections = {}
    missing: list[str] = []
    for section in required_sections:
        value = sections.get(section, ccp.get(section))
        if value is None:
            missing.append(section)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(section)
            continue
        if isinstance(value, (list, dict)) and len(value) == 0:
            missing.append(section)
    if missing:
        raise CouncilBlockedError(
            "ccp_incomplete",
            f"Missing required CCP sections: {', '.join(sorted(missing))}",
        )


def _validate_enum_fields(metadata: Mapping[str, Any], policy: CouncilPolicy) -> None:
    enums = policy.enums
    for key, allowed in enums.items():
        if key not in metadata:
            continue
        value = metadata.get(key)
        if key == "touches":
            values = value if isinstance(value, list) else [value]
            unknown = [v for v in values if v not in allowed]
            if unknown:
                raise CouncilBlockedError(
                    "unknown_enum_value",
                    f"{key}: unknown value(s): {sorted(set(str(v) for v in unknown))}",
                )
            continue
        if value not in allowed:
            raise CouncilBlockedError(
                "unknown_enum_value",
                f"{key}: '{value}' is not one of {allowed}",
            )


def _resolve_mode(metadata: Mapping[str, Any], policy: CouncilPolicy) -> str:
    override = metadata.get("override", {})
    if isinstance(override, Mapping) and override.get("mode"):
        return str(override.get("mode"))
    if any(evaluate_expression(expr, metadata) for expr in policy.mode_m2_triggers()):
        return "M2_FULL"
    if all(evaluate_expression(expr, metadata) for expr in policy.mode_m0_conditions()):
        return "M0_FAST"
    return policy.mode_default


def _resolve_independence_required(metadata: Mapping[str, Any], mode: str, policy: CouncilPolicy) -> str:
    must_triggered = any(
        evaluate_expression(expr, metadata) for expr in policy.independence_must_triggers()
    )
    should_triggered = any(
        evaluate_expression(expr, metadata) for expr in policy.independence_should_triggers()
    )
    if must_triggered and mode == "M2_FULL":
        return "must"
    if should_triggered:
        return "should"
    return "none"


def _resolve_topology(
    metadata: Mapping[str, Any], mode: str, independence_required: str
) -> str:
    override = metadata.get("override", {})
    if isinstance(override, Mapping) and override.get("topology"):
        return str(override.get("topology"))
    if mode == "M0_FAST":
        return "MONO"
    if mode == "M1_STANDARD":
        return "HYBRID" if independence_required == "should" else "MONO"
    if mode == "M2_FULL":
        independent_seat_count = int(metadata.get("independent_seat_count", 1) or 1)
        return "DISTRIBUTED" if independent_seat_count > 1 else "HYBRID"
    return "MONO"


def _resolve_default_models() -> tuple[str, str]:
    try:
        config = load_model_config()
        primary, _, _ = resolve_model_auto("reviewer_architect", config=config)
        independent, _, _ = resolve_model_auto("reviewer_security", config=config)
        return primary, independent
    except Exception:
        return ("claude-sonnet-4-5", "opencode/glm-5-free")


def _assign_models(
    required_seats: tuple[str, ...],
    topology: str,
    independence_required: str,
    metadata: Mapping[str, Any],
    seat_role_map: Mapping[str, str],
) -> dict[str, str]:
    model_plan = metadata.get("model_plan_v1", metadata.get("model_plan", {}))
    if not isinstance(model_plan, Mapping):
        model_plan = {}

    primary_default, independent_default = _resolve_default_models()
    primary_model = str(model_plan.get("primary", primary_default))
    independent_model = str(model_plan.get("independent", independent_default))
    seat_overrides = model_plan.get("seat_overrides", {})
    if not isinstance(seat_overrides, Mapping):
        seat_overrides = {}
    role_overrides = model_plan.get("role_to_model", {})
    if not isinstance(role_overrides, Mapping):
        role_overrides = {}

    assignments: dict[str, str] = {}
    independent_targets = {"RiskAdversarial", "Governance"}
    for seat in required_seats:
        if seat in seat_overrides:
            assignments[seat] = str(seat_overrides[seat])
            continue
        seat_role = seat_role_map.get(seat, "reviewer_architect")
        if seat_role in role_overrides:
            assignments[seat] = str(role_overrides[seat_role])
            continue
        if topology == "MONO":
            assignments[seat] = primary_model
            continue
        if topology == "DISTRIBUTED":
            if seat in independent_targets and independence_required in {"must", "should"}:
                assignments[seat] = independent_model
            else:
                try:
                    role_model, _, _ = resolve_model_auto(seat_role, config=load_model_config())
                    assignments[seat] = role_model
                except Exception:
                    assignments[seat] = primary_model
            continue
        # HYBRID
        if seat == "RiskAdversarial" and independence_required in {"must", "should"}:
            assignments[seat] = independent_model
        else:
            assignments[seat] = primary_model
    return assignments


def _resolve_independence(
    metadata: Mapping[str, Any],
    policy: CouncilPolicy,
    required_seats: tuple[str, ...],
    assignments: dict[str, str],
    independence_required: str,
) -> tuple[bool, tuple[str, ...], dict[str, Any]]:
    compliance_flags: dict[str, Any] = {}
    if independence_required == "none":
        return True, tuple(), compliance_flags

    chair_model = assignments.get("Chair")
    if chair_model is None and required_seats:
        chair_model = assignments.get(required_seats[0], "")
    chair_family = resolve_model_family(chair_model or "", policy.model_families)

    independent_candidates = [seat for seat in ("RiskAdversarial", "Governance") if seat in assignments]
    independent_seats = tuple(
        seat
        for seat in independent_candidates
        if resolve_model_family(assignments[seat], policy.model_families) != chair_family
    )

    if independent_seats:
        return True, independent_seats, compliance_flags

    model_plan = metadata.get("model_plan_v1", metadata.get("model_plan", {}))
    independent_model = ""
    if isinstance(model_plan, Mapping):
        independent_model = str(model_plan.get("independent", ""))

    if independent_model:
        independent_family = resolve_model_family(independent_model, policy.model_families)
        if independent_family != chair_family and independent_candidates:
            target = independent_candidates[0]
            assignments[target] = independent_model
            return True, (target,), compliance_flags

    override = metadata.get("override", {})
    emergency_override = bool(
        isinstance(override, Mapping) and override.get("emergency_ceo", False)
    )
    if independence_required == "must":
        if emergency_override:
            compliance_flags["compliance_status"] = "non-compliant-ceo-authorized"
            compliance_flags["cso_notification_required"] = True
            return False, tuple(), compliance_flags
        raise CouncilBlockedError(
            "independence_unsatisfied",
            "MUST independence condition could not be satisfied; emergency CEO override absent.",
        )

    # SHOULD path
    compliance_flags["independence_waived"] = True
    compliance_flags["override_rationale"] = (
        override.get("rationale")
        if isinstance(override, Mapping)
        else "independent model unavailable"
    )
    return False, tuple(), compliance_flags


def _enforce_bootstrap(metadata: Mapping[str, Any], policy: CouncilPolicy) -> dict[str, Any]:
    flags = {"bootstrap_used": False}
    bootstrap = metadata.get("bootstrap", {})
    if not isinstance(bootstrap, Mapping):
        return flags
    if not bootstrap.get("used", False):
        return flags

    flags["bootstrap_used"] = True
    consecutive = int(bootstrap.get("consecutive_count", 1) or 1)
    max_without_cso = int(policy.bootstrap_policy.get("max_consecutive_without_cso", 2))
    if consecutive > max_without_cso:
        raise CouncilBlockedError(
            "bootstrap_limit_exceeded",
            f"Bootstrap consecutive count {consecutive} exceeds limit {max_without_cso}.",
        )

    safety_critical = bool(metadata.get("safety_critical", False))
    requires_ceo = bool(
        policy.bootstrap_policy.get("safety_critical_requires_ceo_approval", True)
    )
    if safety_critical and requires_ceo and not bool(bootstrap.get("ceo_approved", False)):
        raise CouncilBlockedError(
            "bootstrap_requires_ceo_approval",
            "Safety-critical bootstrap run requires explicit CEO approval.",
        )
    return flags


def compile_council_run_plan(
    ccp: Mapping[str, Any],
    policy: CouncilPolicy,
) -> CouncilRunPlan:
    """
    Compile immutable CouncilRunPlan from CCP metadata and loaded policy.
    """
    metadata = _normalize_metadata(ccp)
    _validate_required_sections(ccp, policy.required_ccp_sections)
    _validate_enum_fields(metadata, policy)

    mode = _resolve_mode(metadata, policy)
    if mode not in policy.enums.get("mode", []):
        raise CouncilBlockedError("unknown_mode", f"Resolved mode '{mode}' is not policy-allowed.")

    independence_required = _resolve_independence_required(metadata, mode, policy)
    topology = _resolve_topology(metadata, mode, independence_required)
    if topology not in policy.enums.get("topology", []):
        raise CouncilBlockedError(
            "unknown_topology",
            f"Resolved topology '{topology}' is not policy-allowed.",
        )

    required_seats = policy.required_seats_for_mode(mode)
    if not required_seats:
        raise CouncilBlockedError(
            "seat_resolution_failed",
            f"No seats configured for mode '{mode}'.",
        )

    seat_role_map = {
        seat: policy.seat_role_map.get(seat, "reviewer_architect")
        for seat in required_seats
    }
    model_assignments = _assign_models(
        required_seats=required_seats,
        topology=topology,
        independence_required=independence_required,
        metadata=metadata,
        seat_role_map=seat_role_map,
    )

    independence_satisfied, independent_seats, compliance_independence = _resolve_independence(
        metadata=metadata,
        policy=policy,
        required_seats=required_seats,
        assignments=model_assignments,
        independence_required=independence_required,
    )
    bootstrap_flags = _enforce_bootstrap(metadata, policy)

    override = metadata.get("override", {})
    override_active = isinstance(override, Mapping) and (
        bool(override.get("mode"))
        or bool(override.get("topology"))
        or bool(override.get("emergency_ceo"))
    )
    override_rationale = (
        str(override.get("rationale"))
        if isinstance(override, Mapping) and override.get("rationale")
        else None
    )

    compliance_flags: dict[str, Any] = {
        **bootstrap_flags,
        **compliance_independence,
        "ceo_override": bool(
            isinstance(override, Mapping) and override.get("emergency_ceo", False)
        ),
        "waivers": list(metadata.get("waivers", []))
        if isinstance(metadata.get("waivers"), list)
        else [],
    }

    aur_id = str(metadata.get("aur_id", ccp.get("aur_id", "unknown_aur")))
    run_id = str(metadata.get("run_id", generate_run_id()))
    timestamp = str(
        metadata.get(
            "timestamp",
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
    )

    return CouncilRunPlan(
        aur_id=aur_id,
        run_id=run_id,
        timestamp=timestamp,
        mode=mode,
        topology=topology,
        required_seats=required_seats,
        model_assignments=model_assignments,
        seat_role_map=seat_role_map,
        independence_required=independence_required,
        independence_satisfied=independence_satisfied,
        independent_seats=independent_seats,
        compliance_flags=compliance_flags,
        override_active=override_active,
        override_rationale=override_rationale,
        cochair_required=(mode != "M0_FAST"),
        contradiction_ledger_required=(mode in {"M1_STANDARD", "M2_FULL"}),
        closure_gate_required=bool(metadata.get("closure_gate_required", True)),
    )

```

### FILE: `runtime/orchestration/council/schema_gate.py`

```python
"""
Deterministic schema gate for council seat outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
import copy
import re

import yaml

from .policy import CouncilPolicy


P0_ALLOWED_CATEGORIES = {
    "determinism",
    "auditability",
    "authority_chain",
    "governance_boundary",
    "security_boundary",
    "correctness",
}


@dataclass
class SchemaGateResult:
    """Outcome of deterministic schema validation for one seat output."""

    valid: bool
    rejected: bool
    normalized_output: dict[str, Any] | None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _normalize_packet(raw_output: dict[str, Any] | str) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if isinstance(raw_output, dict):
        return copy.deepcopy(raw_output), errors
    if isinstance(raw_output, str):
        text = raw_output.strip()
        if not text:
            errors.append("Seat output is empty.")
            return None, errors
        try:
            parsed = yaml.safe_load(text)
        except Exception as exc:
            errors.append(f"Seat output is not valid YAML/JSON: {exc}")
            return None, errors
        if not isinstance(parsed, dict):
            errors.append("Seat output must parse to an object.")
            return None, errors
        return parsed, errors
    errors.append(f"Seat output type '{type(raw_output).__name__}' is unsupported.")
    return None, errors


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _add_assumption_labels(output: dict[str, Any], warnings: list[str]) -> None:
    for section in ("key_findings", "risks", "fixes"):
        value = output.get(section)
        if not isinstance(value, list):
            continue
        normalized: list[Any] = []
        for item in value:
            if isinstance(item, str):
                has_ref = "REF:" in item
                has_assumption = "[ASSUMPTION]" in item
                if not has_ref and not has_assumption:
                    normalized.append(f"{item} [ASSUMPTION]")
                    warnings.append(f"{section}: added ASSUMPTION label for claim without REF.")
                else:
                    normalized.append(item)
                continue
            if isinstance(item, dict):
                claim_text = str(item.get("claim", item.get("text", "")))
                has_ref = "REF:" in claim_text or bool(item.get("ref"))
                if not has_ref:
                    item = dict(item)
                    item["assumption"] = True
                    warnings.append(f"{section}: added assumption=true for claim without REF.")
                normalized.append(item)
                continue
            normalized.append(item)
        output[section] = normalized


def _parse_net_steps(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if re.fullmatch(r"[+-]?\d+", cleaned):
            return int(cleaned)
    return None


def _validate_complexity_budget(output: dict[str, Any], warnings: list[str]) -> None:
    budget = output.get("complexity_budget")
    if not isinstance(budget, dict):
        warnings.append("complexity_budget is missing or malformed.")
        return
    required = (
        "net_human_steps",
        "new_surfaces_introduced",
        "surfaces_removed",
        "mechanized",
        "trade_statement",
    )
    missing = [key for key in required if key not in budget]
    if missing:
        warnings.append(
            f"complexity_budget missing fields: {', '.join(sorted(missing))}"
        )
        return

    net_steps = _parse_net_steps(budget.get("net_human_steps"))
    mechanized = str(budget.get("mechanized", "")).strip().lower()
    trade_statement = str(budget.get("trade_statement", "")).strip().lower()
    if net_steps is not None and net_steps > 0 and mechanized == "no" and trade_statement in {"", "none"}:
        warnings.append(
            "complexity_budget has net-positive human steps without mechanization trade statement."
        )


def _validate_p0_labels(output: dict[str, Any], warnings: list[str]) -> None:
    findings = output.get("key_findings")
    if not isinstance(findings, list):
        return
    for idx, finding in enumerate(findings):
        if isinstance(finding, dict):
            priority = str(finding.get("priority", "")).upper()
            if priority != "P0":
                continue
            category = str(finding.get("category", "")).lower()
            if category not in P0_ALLOWED_CATEGORIES:
                warnings.append(
                    f"key_findings[{idx}] uses P0 without recognized blocker category."
                )
            continue
        if isinstance(finding, str) and "P0" in finding:
            lowered = finding.lower()
            if not any(category in lowered for category in P0_ALLOWED_CATEGORIES):
                warnings.append(
                    f"key_findings[{idx}] may have P0 inflation without blocker category."
                )


def validate_seat_output(
    raw_output: dict[str, Any] | str,
    policy: CouncilPolicy,
) -> SchemaGateResult:
    """
    Validate and normalize a seat output packet deterministically.
    """
    normalized, parse_errors = _normalize_packet(raw_output)
    if normalized is None:
        return SchemaGateResult(
            valid=False,
            rejected=True,
            normalized_output=None,
            errors=parse_errors,
            warnings=[],
        )

    errors = list(parse_errors)
    warnings: list[str] = []

    for section in policy.schema_gate_required_sections:
        if section not in normalized or _is_empty(normalized.get(section)):
            errors.append(f"Missing required section: {section}")

    verdict = normalized.get("verdict")
    allowed_verdicts = set(policy.enums.get("verdict", []))
    if verdict not in allowed_verdicts:
        errors.append(
            f"Invalid verdict '{verdict}'. Allowed values: {sorted(allowed_verdicts)}"
        )

    _add_assumption_labels(normalized, warnings)
    _validate_complexity_budget(normalized, warnings)
    _validate_p0_labels(normalized, warnings)

    rejected = len(errors) > 0
    return SchemaGateResult(
        valid=not rejected,
        rejected=rejected,
        normalized_output=normalized,
        errors=errors,
        warnings=warnings,
    )

```

### FILE: `runtime/orchestration/council/fsm.py`

```python
"""
Deterministic state machine for council review execution.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Mapping

from runtime.agents.api import AgentCall, call_agent

from .compiler import compile_council_run_plan
from .models import (
    CouncilBlockedError,
    CouncilRunPlan,
    CouncilRuntimeResult,
    CouncilSeatResult,
    CouncilTransition,
)
from .policy import CouncilPolicy
from .schema_gate import validate_seat_output


SeatExecutor = Callable[[str, Mapping[str, Any], CouncilRunPlan, int], dict[str, Any] | str]
ClosureCallable = Callable[[Mapping[str, Any], CouncilRunPlan], tuple[bool, dict[str, Any]]]


STATE_S0_ASSEMBLE = "S0_ASSEMBLE"
STATE_S0_5_COCHAIR_VALIDATE = "S0_5_COCHAIR_VALIDATE"
STATE_S1_EXECUTE_SEATS = "S1_EXECUTE_SEATS"
STATE_S1_25_SCHEMA_GATE = "S1_25_SCHEMA_GATE"
STATE_S1_5_SEAT_COMPLETION = "S1_5_SEAT_COMPLETION"
STATE_S2_SYNTHESIS = "S2_SYNTHESIS"
STATE_S2_5_COCHAIR_CHALLENGE = "S2_5_COCHAIR_CHALLENGE"
STATE_S3_CLOSURE_GATE = "S3_CLOSURE_GATE"
STATE_S4_CLOSEOUT = "S4_CLOSEOUT"
STATE_TERMINAL_BLOCKED = "TERMINAL_BLOCKED"
STATE_TERMINAL_COMPLETE = "TERMINAL_COMPLETE"


def _default_seat_executor(
    seat: str,
    ccp: Mapping[str, Any],
    plan: CouncilRunPlan,
    retry_count: int,
) -> dict[str, Any] | str:
    """
    Default seat executor using the Agent API.
    """
    role = plan.seat_role_map.get(seat, "reviewer_architect")
    model = plan.model_assignments.get(seat, "auto")
    packet = {
        "ccp": ccp,
        "seat": seat,
        "plan": {
            "mode": plan.mode,
            "topology": plan.topology,
            "required_sections": list(ccp.get("sections", {}).keys())
            if isinstance(ccp.get("sections"), Mapping)
            else [],
        },
        "retry_count": retry_count,
    }
    response = call_agent(
        AgentCall(
            role=role,
            packet=packet,
            model=model,
        ),
        run_id=plan.run_id,
    )
    if response.packet is not None:
        return response.packet
    return response.content


def _default_closure_builder(
    synthesis: Mapping[str, Any], plan: CouncilRunPlan
) -> tuple[bool, dict[str, Any]]:
    """
    Default closure-build hook. Side-effect free unless caller injects a real hook.
    """
    return True, {"builder": "noop", "run_id": plan.run_id, "synthesis_verdict": synthesis.get("verdict")}


def _default_closure_validator(
    synthesis: Mapping[str, Any], plan: CouncilRunPlan
) -> tuple[bool, dict[str, Any]]:
    """
    Default closure-validate hook. Side-effect free unless caller injects a real hook.
    """
    return True, {"validator": "noop", "run_id": plan.run_id, "synthesis_verdict": synthesis.get("verdict")}


class CouncilFSM:
    """
    Protocol-aligned council review runtime.
    """

    def __init__(
        self,
        policy: CouncilPolicy,
        seat_executor: SeatExecutor | None = None,
        closure_builder: ClosureCallable | None = None,
        closure_validator: ClosureCallable | None = None,
    ):
        self.policy = policy
        self.seat_executor = seat_executor or _default_seat_executor
        self.closure_builder = closure_builder or _default_closure_builder
        self.closure_validator = closure_validator or _default_closure_validator

    @staticmethod
    def _transition(
        transitions: list[CouncilTransition],
        from_state: str,
        to_state: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        transitions.append(
            CouncilTransition(
                from_state=from_state,
                to_state=to_state,
                reason=reason,
                details=details or {},
            )
        )

    @staticmethod
    def _waived_seats(ccp: Mapping[str, Any]) -> set[str]:
        waivers = ccp.get("waived_seats", [])
        if not isinstance(waivers, list):
            return set()
        return {str(item) for item in waivers}

    @staticmethod
    def _cochair_validate_ccp(ccp: Mapping[str, Any], plan: CouncilRunPlan) -> tuple[bool, str]:
        required_sections = {"objective", "scope", "constraints", "artifacts"}
        sections = ccp.get("sections", {})
        if not isinstance(sections, Mapping):
            return False, "CCP sections block missing."
        missing = [section for section in sorted(required_sections) if section not in sections]
        if missing:
            return False, f"Missing required sections: {', '.join(missing)}"
        if not plan.cochair_required:
            return True, "cochair_not_required"
        return True, "cochair_validation_passed"

    @staticmethod
    def _extract_verdict(seat_outputs: Mapping[str, CouncilSeatResult]) -> str:
        verdicts = []
        for result in seat_outputs.values():
            payload = result.normalized_output or {}
            verdict = payload.get("verdict")
            if isinstance(verdict, str):
                verdicts.append(verdict)
        if not verdicts:
            return "Reject"
        if "Reject" in verdicts:
            return "Reject"
        if "Go with Fixes" in verdicts:
            return "Go with Fixes"
        return "Accept"

    @staticmethod
    def _aggregate_complexity(seat_outputs: Mapping[str, CouncilSeatResult]) -> dict[str, Any]:
        total_net_human_steps = 0
        total_new_surfaces = 0
        total_surfaces_removed = 0
        unmechanized_additions = 0

        for result in seat_outputs.values():
            budget = (result.normalized_output or {}).get("complexity_budget", {})
            if not isinstance(budget, Mapping):
                continue
            net_raw = budget.get("net_human_steps", 0)
            if isinstance(net_raw, str):
                cleaned = net_raw.strip()
                net = int(cleaned) if cleaned.lstrip("+-").isdigit() else 0
            elif isinstance(net_raw, int):
                net = net_raw
            else:
                net = 0
            total_net_human_steps += net

            total_new_surfaces += int(budget.get("new_surfaces_introduced", 0) or 0)
            total_surfaces_removed += int(budget.get("surfaces_removed", 0) or 0)
            mechanized = str(budget.get("mechanized", "")).strip().lower()
            if net > 0 and mechanized == "no":
                unmechanized_additions += 1

        return {
            "governance_creep_flag": bool(total_net_human_steps > 0 and unmechanized_additions > 0),
            "total_net_human_steps": total_net_human_steps,
            "total_new_surfaces": total_new_surfaces,
            "total_surfaces_removed": total_surfaces_removed,
            "unmechanized_additions": unmechanized_additions,
        }

    def _build_contradiction_ledger(
        self, seat_outputs: Mapping[str, CouncilSeatResult], required: bool
    ) -> list[dict[str, Any]]:
        if not required:
            return []
        by_verdict: dict[str, list[str]] = {}
        for seat, result in seat_outputs.items():
            verdict = str((result.normalized_output or {}).get("verdict", "unknown"))
            by_verdict.setdefault(verdict, []).append(seat)
        if len(by_verdict) <= 1:
            return []
        ledger = []
        for verdict, seats in sorted(by_verdict.items()):
            ledger.append(
                {
                    "resolution": "requires synthesis reconciliation",
                    "seats": sorted(seats),
                    "verdict": verdict,
                }
            )
        return ledger

    def _synthesize(
        self,
        seat_outputs: Mapping[str, CouncilSeatResult],
        plan: CouncilRunPlan,
        ccp: Mapping[str, Any],
    ) -> dict[str, Any]:
        chair_output = (seat_outputs.get("Chair") or seat_outputs.get("L1UnifiedReviewer"))
        chair_payload = chair_output.normalized_output if chair_output else {}
        if not isinstance(chair_payload, Mapping):
            chair_payload = {}

        contradiction_ledger = self._build_contradiction_ledger(
            seat_outputs=seat_outputs,
            required=plan.contradiction_ledger_required,
        )
        rollup = self._aggregate_complexity(seat_outputs)

        synthesis = {
            "ceo_decisions": list(chair_payload.get("ceo_decisions", []))
            if isinstance(chair_payload.get("ceo_decisions"), list)
            else [],
            "change_list": list(chair_payload.get("fixes", []))
            if isinstance(chair_payload.get("fixes"), list)
            else [],
            "contradiction_ledger": contradiction_ledger,
            "deletion_line": str(
                chair_payload.get(
                    "deletion_line",
                    "Nothing — no deletion requested by synthesized council output.",
                )
            ),
            "fix_plan": list(chair_payload.get("fixes", []))
            if isinstance(chair_payload.get("fixes"), list)
            else [],
            "mechanization_plan": list(chair_payload.get("mechanization_plan", []))
            if isinstance(chair_payload.get("mechanization_plan"), list)
            else [],
            "run_complexity_rollup": rollup,
            "verdict": self._extract_verdict(seat_outputs),
        }

        if bool(plan.compliance_flags.get("bootstrap_used", False)):
            synthesis["fix_plan"].append(
                {
                    "owner": "operations",
                    "priority": "P0",
                    "text": "Restore canonical artifacts and re-run council validation.",
                }
            )
        return synthesis

    @staticmethod
    def _challenge_synthesis(
        synthesis: Mapping[str, Any],
        seat_outputs: Mapping[str, CouncilSeatResult],
        plan: CouncilRunPlan,
    ) -> tuple[bool, str]:
        if not plan.cochair_required:
            return True, "cochair_not_required"

        cochair = seat_outputs.get("CoChair")
        if cochair is None or cochair.normalized_output is None:
            return False, "CoChair output missing."

        if plan.contradiction_ledger_required:
            ledger = synthesis.get("contradiction_ledger")
            if not isinstance(ledger, list):
                return False, "Contradiction Ledger missing from synthesis."
            if plan.topology == "MONO":
                verified = bool(cochair.normalized_output.get("contradiction_ledger_verified", False))
                if not verified:
                    return False, "CoChair did not verify contradiction ledger completeness."
        return True, "cochair_challenge_passed"

    def run(self, ccp: Mapping[str, Any]) -> CouncilRuntimeResult:
        """
        Execute the council protocol runtime for one CCP payload.
        """
        transitions: list[CouncilTransition] = []
        state = STATE_S0_ASSEMBLE
        seat_results: dict[str, CouncilSeatResult] = {}
        synthesis: dict[str, Any] = {}
        closure_events: list[dict[str, Any]] = []
        compliance = {}

        try:
            plan = compile_council_run_plan(ccp=ccp, policy=self.policy)
            compliance = dict(plan.compliance_flags)
            self._transition(
                transitions,
                STATE_S0_ASSEMBLE,
                STATE_S0_5_COCHAIR_VALIDATE if plan.cochair_required else STATE_S1_EXECUTE_SEATS,
                "plan_compiled",
                {"mode": plan.mode, "topology": plan.topology},
            )
            state = STATE_S0_5_COCHAIR_VALIDATE if plan.cochair_required else STATE_S1_EXECUTE_SEATS
        except CouncilBlockedError as err:
            self._transition(
                transitions,
                STATE_S0_ASSEMBLE,
                STATE_TERMINAL_BLOCKED,
                "plan_blocked",
                {"category": err.category, "detail": err.detail},
            )
            block_report = {"category": err.category, "detail": err.detail}
            return CouncilRuntimeResult(
                status="blocked",
                run_log={
                    "status": "blocked",
                    "state_transitions": [event.to_dict() for event in transitions],
                },
                decision_payload={"status": "BLOCKED", "reason": err.category, "detail": err.detail},
                block_report=block_report,
            )

        if state == STATE_S0_5_COCHAIR_VALIDATE:
            ok, reason = self._cochair_validate_ccp(ccp, plan)
            if not ok:
                self._transition(
                    transitions,
                    STATE_S0_5_COCHAIR_VALIDATE,
                    STATE_TERMINAL_BLOCKED,
                    "cochair_validation_failed",
                    {"detail": reason},
                )
                return CouncilRuntimeResult(
                    status="blocked",
                    run_log={
                        "execution": plan.to_dict(),
                        "status": "blocked",
                        "state_transitions": [event.to_dict() for event in transitions],
                    },
                    decision_payload={"status": "BLOCKED", "reason": "ccp_validation_failed", "detail": reason},
                    block_report={"category": "ccp_validation_failed", "detail": reason},
                )
            self._transition(
                transitions,
                STATE_S0_5_COCHAIR_VALIDATE,
                STATE_S1_EXECUTE_SEATS,
                reason,
            )
            state = STATE_S1_EXECUTE_SEATS

        waived = self._waived_seats(ccp)
        if state == STATE_S1_EXECUTE_SEATS:
            for seat in plan.required_seats:
                retries_used = 0
                errors: list[str] = []
                warnings: list[str] = []
                normalized_output = None
                raw_output: dict[str, Any] | str = {}
                status = "failed"
                while retries_used <= self.policy.schema_gate_retry_cap:
                    raw_output = self.seat_executor(seat, ccp, plan, retries_used)
                    gate_result = validate_seat_output(raw_output=raw_output, policy=self.policy)
                    self._transition(
                        transitions,
                        STATE_S1_EXECUTE_SEATS,
                        STATE_S1_25_SCHEMA_GATE,
                        "seat_output_received",
                        {"retries": retries_used, "seat": seat},
                    )
                    errors = list(gate_result.errors)
                    warnings = list(gate_result.warnings)
                    if gate_result.valid:
                        status = "complete"
                        normalized_output = gate_result.normalized_output
                        break
                    if retries_used >= self.policy.schema_gate_retry_cap:
                        status = "failed"
                        normalized_output = gate_result.normalized_output
                        break
                    retries_used += 1
                waived_seat = seat in waived
                if status != "complete" and waived_seat:
                    status = "waived"
                seat_results[seat] = CouncilSeatResult(
                    seat=seat,
                    status=status,
                    model=plan.model_assignments.get(seat, "unknown"),
                    raw_output=raw_output,
                    normalized_output=normalized_output,
                    retries_used=retries_used,
                    errors=errors,
                    warnings=warnings,
                    waived=waived_seat,
                )
            self._transition(
                transitions,
                STATE_S1_25_SCHEMA_GATE,
                STATE_S1_5_SEAT_COMPLETION,
                "all_seats_processed",
                {
                    "seats_failed": sum(1 for item in seat_results.values() if item.status == "failed"),
                    "seats_total": len(seat_results),
                    "seats_waived": sum(1 for item in seat_results.values() if item.status == "waived"),
                },
            )
            state = STATE_S1_5_SEAT_COMPLETION

        if state == STATE_S1_5_SEAT_COMPLETION:
            blocking_gaps = [
                seat
                for seat in plan.required_seats
                if seat_results.get(seat) is None or seat_results[seat].status == "failed"
            ]
            if blocking_gaps:
                self._transition(
                    transitions,
                    STATE_S1_5_SEAT_COMPLETION,
                    STATE_TERMINAL_BLOCKED,
                    "required_seats_missing",
                    {"missing_or_failed_seats": blocking_gaps},
                )
                return CouncilRuntimeResult(
                    status="blocked",
                    run_log={
                        "execution": plan.to_dict(),
                        "seat_outputs": {seat: result.to_dict() for seat, result in seat_results.items()},
                        "status": "blocked",
                        "state_transitions": [event.to_dict() for event in transitions],
                    },
                    decision_payload={
                        "status": "BLOCKED",
                        "reason": "required_seats_missing",
                        "seats": blocking_gaps,
                    },
                    block_report={
                        "category": "required_seats_missing",
                        "detail": f"Blocking seat gaps: {', '.join(blocking_gaps)}",
                    },
                )
            self._transition(
                transitions,
                STATE_S1_5_SEAT_COMPLETION,
                STATE_S2_SYNTHESIS,
                "seat_completion_ok",
            )
            state = STATE_S2_SYNTHESIS

        if state == STATE_S2_SYNTHESIS:
            synthesis = self._synthesize(seat_outputs=seat_results, plan=plan, ccp=ccp)
            self._transition(
                transitions,
                STATE_S2_SYNTHESIS,
                STATE_S2_5_COCHAIR_CHALLENGE,
                "synthesis_complete",
                {"verdict": synthesis.get("verdict")},
            )
            state = STATE_S2_5_COCHAIR_CHALLENGE

        if state == STATE_S2_5_COCHAIR_CHALLENGE:
            passed, reason = self._challenge_synthesis(
                synthesis=synthesis, seat_outputs=seat_results, plan=plan
            )
            if not passed:
                # One synthesis rework cycle only.
                synthesis = self._synthesize(seat_outputs=seat_results, plan=plan, ccp=ccp)
                passed_after_rework, reason_after_rework = self._challenge_synthesis(
                    synthesis=synthesis, seat_outputs=seat_results, plan=plan
                )
                if not passed_after_rework:
                    self._transition(
                        transitions,
                        STATE_S2_5_COCHAIR_CHALLENGE,
                        STATE_TERMINAL_BLOCKED,
                        "cochair_challenge_failed",
                        {"detail": reason_after_rework},
                    )
                    return CouncilRuntimeResult(
                        status="blocked",
                        run_log={
                            "execution": plan.to_dict(),
                            "seat_outputs": {seat: result.to_dict() for seat, result in seat_results.items()},
                            "status": "blocked",
                            "state_transitions": [event.to_dict() for event in transitions],
                            "synthesis": synthesis,
                        },
                        decision_payload={
                            "status": "BLOCKED",
                            "reason": "cochair_challenge_failed",
                            "detail": reason_after_rework,
                        },
                        block_report={
                            "category": "cochair_challenge_failed",
                            "detail": reason_after_rework,
                        },
                    )
            next_state = (
                STATE_S3_CLOSURE_GATE
                if plan.closure_gate_required and synthesis.get("verdict") in {"Accept", "Go with Fixes"}
                else STATE_S4_CLOSEOUT
            )
            self._transition(
                transitions,
                STATE_S2_5_COCHAIR_CHALLENGE,
                next_state,
                "cochair_challenge_passed",
                {"detail": reason},
            )
            state = next_state

        if state == STATE_S3_CLOSURE_GATE:
            cycles = 0
            closure_ok = False
            while cycles <= self.policy.closure_retry_cap:
                build_ok, build_details = self.closure_builder(synthesis, plan)
                validate_ok, validate_details = self.closure_validator(synthesis, plan)
                closure_events.append(
                    {
                        "build_details": build_details,
                        "build_ok": build_ok,
                        "cycle": cycles,
                        "validate_details": validate_details,
                        "validate_ok": validate_ok,
                    }
                )
                if build_ok and validate_ok:
                    closure_ok = True
                    break
                cycles += 1
            if not closure_ok:
                waivers = compliance.get("waivers", [])
                if not isinstance(waivers, list):
                    waivers = []
                waivers.append("closure_gate_residual_issues")
                compliance["waivers"] = waivers
            self._transition(
                transitions,
                STATE_S3_CLOSURE_GATE,
                STATE_S4_CLOSEOUT,
                "closure_gate_complete",
                {"closure_ok": closure_ok, "cycles": len(closure_events)},
            )
            state = STATE_S4_CLOSEOUT

        if state == STATE_S4_CLOSEOUT:
            self._transition(
                transitions,
                STATE_S4_CLOSEOUT,
                STATE_TERMINAL_COMPLETE,
                "run_complete",
            )

        seat_outputs_dict = {
            seat: seat_results[seat].to_dict()
            for seat in plan.required_seats
            if seat in seat_results
        }
        transition_dicts = [event.to_dict() for event in transitions]
        model_counter = Counter(plan.model_assignments.values())
        model_plan = {
            "by_model": dict(sorted(model_counter.items())),
            "seat_assignments": [
                {"model": plan.model_assignments.get(seat, "unknown"), "seat": seat}
                for seat in plan.required_seats
            ],
        }

        run_log = {
            "aur_id": plan.aur_id,
            "compliance": {
                "bootstrap_used": bool(compliance.get("bootstrap_used", False)),
                "ceo_override": bool(compliance.get("ceo_override", False)),
                "independence_required": plan.independence_required,
                "independence_satisfied": plan.independence_satisfied,
                "waivers": list(compliance.get("waivers", []))
                if isinstance(compliance.get("waivers"), list)
                else [],
            },
            "execution": {
                "mode": plan.mode,
                "model_plan": model_plan,
                "protocol_version": self.policy.protocol_version,
                "run_id": plan.run_id,
                "timestamp": plan.timestamp,
                "topology": plan.topology,
            },
            "seat_outputs": seat_outputs_dict,
            "state_transitions": transition_dicts,
            "status": "complete",
            "synthesis": synthesis,
        }
        if closure_events:
            run_log["closure_gate"] = closure_events

        decision_payload = {
            "compliance": run_log["compliance"],
            "status": "COMPLETE",
            "verdict": synthesis.get("verdict", "Reject"),
            "fix_plan": synthesis.get("fix_plan", []),
            "ceo_decisions": synthesis.get("ceo_decisions", []),
            "deletion_line": synthesis.get("deletion_line", ""),
            "run_id": plan.run_id,
        }
        return CouncilRuntimeResult(
            status="complete",
            run_log=run_log,
            decision_payload=decision_payload,
            block_report=None,
        )

```

### FILE: `runtime/orchestration/missions/review.py`

```python
"""
Phase 3 Mission Types - Review Mission

Runs council review on a packet (BUILD_PACKET or REVIEW_PACKET).
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3 - Mission: review
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
)
from runtime.orchestration.council import CouncilFSM, load_council_policy


# Valid review verdicts per Council Protocol
VALID_VERDICTS = frozenset({"approved", "rejected", "needs_revision", "escalate"})
PROTOCOL_TO_MISSION_VERDICT = {
    "Accept": "approved",
    "Go with Fixes": "needs_revision",
    "Reject": "rejected",
}

# Review seats per architecture
REVIEW_SEATS = ("architect", "alignment", "risk", "governance")


class ReviewMission(BaseMission):
    """
    Review mission: Run council review on a packet.
    
    Inputs:
        - subject_packet (dict): The packet to review
        - review_type (str): Type of review (build_review, output_review)
        
    Outputs:
        - verdict (str): Review verdict
        - council_decision (dict): Full council decision with seat outputs
        
    Steps:
        1. prepare_ccp: Transform packet to Council Context Pack
        2. run_seats: Run each review seat (stubbed for MVP)
        3. synthesize: Synthesize seat outputs into decision
        4. validate_decision: Validate output against schema
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.REVIEW
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Validate review mission inputs.
        
        Required: subject_packet (dict), review_type (string)
        """
        # Check subject_packet
        subject_packet = inputs.get("subject_packet")
        if not subject_packet:
            raise MissionValidationError("subject_packet is required")
        if not isinstance(subject_packet, dict):
            raise MissionValidationError("subject_packet must be a dict")
        
        # Check review_type
        review_type = inputs.get("review_type")
        if not review_type:
            raise MissionValidationError("review_type is required")
        if not isinstance(review_type, str):
            raise MissionValidationError("review_type must be a string")
        
        valid_review_types = ("build_review", "output_review", "governance_review")
        if review_type not in valid_review_types:
            raise MissionValidationError(
                f"review_type must be one of {valid_review_types}, got '{review_type}'"
            )
    
    def run(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> MissionResult:
        executed_steps: List[str] = []
        
        try:
            # Step 1: Validate inputs
            self.validate_inputs(inputs)
            executed_steps.append("validate_inputs")
            use_council_runtime = bool(inputs.get("use_council_runtime", False))
            if use_council_runtime:
                return self._run_council_runtime(context, inputs, executed_steps)
            return self._run_legacy_single_seat(context, inputs, executed_steps)
            
        except MissionValidationError as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Input validation failed: {e}",
            )
        except Exception as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Unexpected error: {e}",
            )

    def _run_legacy_single_seat(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
        executed_steps: List[str],
    ) -> MissionResult:
        """Preserve existing single-seat behavior for compatibility."""
        from runtime.agents.api import call_agent, AgentCall

        call = AgentCall(
            role="reviewer_architect",
            packet={
                "subject_packet": inputs["subject_packet"],
                "review_type": inputs["review_type"]
            },
            model="auto",
        )

        response = call_agent(call, run_id=context.run_id)
        executed_steps.append("architect_review_llm_call")

        reviewer_packet_parsed = response.packet is not None
        if response.packet is not None:
            decision = response.packet
        else:
            fallback_verdict = None
            verdict_match = re.search(
                r'(?m)^verdict:\s*["\']?(\w+)["\']?\s*$',
                response.content,
            )
            if verdict_match:
                candidate = verdict_match.group(1).lower()
                if candidate in VALID_VERDICTS:
                    fallback_verdict = candidate
            decision = {
                "verdict": fallback_verdict or "needs_revision",
                "rationale": response.content,
                "concerns": [],
                "recommendations": [],
            }

        final_verdict = decision.get("verdict", "needs_revision")
        if final_verdict not in VALID_VERDICTS:
            final_verdict = "needs_revision"

        council_decision = {
            "verdict": final_verdict,
            "seat_outputs": {"architect": decision},
            "synthesis": decision.get("rationale", response.content),
        }
        executed_steps.append("synthesize")

        if final_verdict == "escalate":
            return self._make_result(
                success=True,
                outputs={
                    "verdict": final_verdict,
                    "council_decision": council_decision,
                    "reviewer_packet_parsed": reviewer_packet_parsed,
                },
                executed_steps=executed_steps,
                escalation_reason="Architect review requires CEO escalation",
                evidence={
                    "call_id": response.call_id,
                    "model_used": response.model_used,
                    "usage": response.usage,
                },
            )

        return self._make_result(
            success=True,
            outputs={
                "verdict": final_verdict,
                "council_decision": council_decision,
                "reviewer_packet_parsed": reviewer_packet_parsed,
            },
            executed_steps=executed_steps,
            evidence={
                "call_id": response.call_id,
                "model_used": response.model_used,
                "usage": response.usage,
            },
        )

    @staticmethod
    def _default_touches(review_type: str) -> list[str]:
        if review_type == "governance_review":
            return ["governance_protocol"]
        if review_type == "build_review":
            return ["runtime_core"]
        return ["interfaces"]

    def _build_ccp(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        review_type = str(inputs["review_type"])
        subject_packet = inputs["subject_packet"]
        subject_hash = hashlib.sha256(
            json.dumps(subject_packet, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        header = {
            "aur_id": inputs.get("aur_id", f"{review_type}:{subject_hash[:12]}"),
            "aur_type": inputs.get("aur_type", "code"),
            "blast_radius": inputs.get("blast_radius", "module"),
            "change_class": inputs.get("change_class", "amend"),
            "closure_gate_required": bool(inputs.get("closure_gate_required", review_type == "output_review")),
            "model_plan_v1": inputs.get("model_plan_v1", {}),
            "override": inputs.get("override", {}),
            "reversibility": inputs.get("reversibility", "moderate"),
            "run_id": context.run_id,
            "safety_critical": bool(inputs.get("safety_critical", False)),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "touches": inputs.get("touches", self._default_touches(review_type)),
            "uncertainty": inputs.get("uncertainty", "medium"),
        }

        sections = inputs.get("sections")
        if not isinstance(sections, dict):
            sections = {
                "objective": f"Run council review for {review_type}.",
                "scope": {
                    "review_type": review_type,
                    "subject_fields": sorted(subject_packet.keys()),
                },
                "constraints": inputs.get(
                    "constraints",
                    ["Fail closed on schema and protocol violations."],
                ),
                "artifacts": inputs.get(
                    "artifacts",
                    [{"kind": "subject_packet", "sha256": subject_hash}],
                ),
            }

        ccp = {
            "header": header,
            "review_type": review_type,
            "sections": sections,
            "subject_packet": subject_packet,
        }

        bootstrap = inputs.get("bootstrap")
        if isinstance(bootstrap, dict):
            ccp["header"]["bootstrap"] = bootstrap
        return ccp

    def _run_council_runtime(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
        executed_steps: List[str],
    ) -> MissionResult:
        ccp = self._build_ccp(context, inputs)
        executed_steps.append("prepare_ccp")

        policy_path = inputs.get("council_policy_path")
        policy = load_council_policy(policy_path)
        fsm = CouncilFSM(policy=policy)
        runtime_result = fsm.run(ccp)
        executed_steps.append("execute_council_fsm")

        if runtime_result.status == "blocked":
            detail = "blocked"
            if runtime_result.block_report:
                detail = runtime_result.block_report.get("detail", detail)
            council_decision = {
                "protocol_status": "BLOCKED",
                "run_log": runtime_result.run_log,
                "block_report": runtime_result.block_report,
                "synthesis": {"verdict": "Reject"},
                "verdict": "escalate",
            }
            return self._make_result(
                success=True,
                outputs={
                    "verdict": "escalate",
                    "council_decision": council_decision,
                    "reviewer_packet_parsed": True,
                },
                executed_steps=executed_steps,
                escalation_reason=f"Council runtime blocked: {detail}",
                evidence={
                    "council_runtime_status": runtime_result.status,
                    "usage": {"total": 0},
                },
            )

        protocol_verdict = str(runtime_result.decision_payload.get("verdict", "Reject"))
        mission_verdict = PROTOCOL_TO_MISSION_VERDICT.get(protocol_verdict, "needs_revision")
        council_decision = {
            "protocol_status": runtime_result.decision_payload.get("status", "COMPLETE"),
            "protocol_verdict": protocol_verdict,
            "run_log": runtime_result.run_log,
            "synthesis": runtime_result.run_log.get("synthesis", {}),
            "verdict": mission_verdict,
        }

        escalation_reason = None
        if mission_verdict == "escalate":
            escalation_reason = "Council runtime requested escalation."

        return self._make_result(
            success=True,
            outputs={
                "verdict": mission_verdict,
                "council_decision": council_decision,
                "reviewer_packet_parsed": True,
            },
            executed_steps=executed_steps,
            escalation_reason=escalation_reason,
            evidence={
                "council_runtime_status": runtime_result.status,
                "run_id": runtime_result.decision_payload.get("run_id"),
                "usage": {"total": 0},
            },
        )

```

### FILE: `runtime/tests/orchestration/council/test_compiler.py`

```python
from __future__ import annotations

import pytest

from runtime.orchestration.council.compiler import compile_council_run_plan
from runtime.orchestration.council.models import CouncilBlockedError
from runtime.orchestration.council.policy import load_council_policy


def _base_sections() -> dict:
    return {
        "objective": "Review candidate change.",
        "scope": {"surface": "runtime"},
        "constraints": ["deterministic outputs"],
        "artifacts": [{"id": "artifact-1"}],
    }


def test_compile_plan_m0_fast_success():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-1",
            "aur_type": "doc",
            "change_class": "hygiene",
            "blast_radius": "local",
            "reversibility": "easy",
            "uncertainty": "low",
            "touches": ["docs_only"],
            "safety_critical": False,
        },
        "sections": _base_sections(),
    }
    plan = compile_council_run_plan(ccp=ccp, policy=policy)
    assert plan.mode == "M0_FAST"
    assert plan.topology == "MONO"
    assert plan.required_seats == ("L1UnifiedReviewer",)
    assert plan.cochair_required is False


def test_compile_plan_m2_triggered_by_runtime_core():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-2",
            "aur_type": "code",
            "change_class": "amend",
            "blast_radius": "module",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["runtime_core"],
            "safety_critical": False,
        },
        "sections": _base_sections(),
    }
    plan = compile_council_run_plan(ccp=ccp, policy=policy)
    assert plan.mode == "M2_FULL"
    assert plan.topology == "HYBRID"
    assert "Chair" in plan.required_seats
    assert "RiskAdversarial" in plan.required_seats


def test_compile_plan_blocks_on_unknown_enum():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-3",
            "aur_type": "code",
            "change_class": "hygiene",
            "blast_radius": "local",
            "reversibility": "easy",
            "uncertainty": "low",
            "touches": ["nonexistent_surface"],
            "safety_critical": False,
        },
        "sections": _base_sections(),
    }
    with pytest.raises(CouncilBlockedError) as exc:
        compile_council_run_plan(ccp=ccp, policy=policy)
    assert exc.value.category == "unknown_enum_value"


def test_compile_plan_must_independence_blocks_without_override():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-4",
            "aur_type": "code",
            "change_class": "amend",
            "blast_radius": "system",
            "reversibility": "hard",
            "uncertainty": "high",
            "touches": ["runtime_core"],
            "safety_critical": True,
            "model_plan_v1": {
                "primary": "claude-sonnet-4-5",
                "independent": "claude-haiku-4-5",
            },
        },
        "sections": _base_sections(),
    }
    with pytest.raises(CouncilBlockedError) as exc:
        compile_council_run_plan(ccp=ccp, policy=policy)
    assert exc.value.category == "independence_unsatisfied"


def test_compile_plan_must_independence_with_emergency_override():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-5",
            "aur_type": "code",
            "change_class": "amend",
            "blast_radius": "system",
            "reversibility": "hard",
            "uncertainty": "high",
            "touches": ["runtime_core"],
            "safety_critical": True,
            "model_plan_v1": {
                "primary": "claude-sonnet-4-5",
                "independent": "claude-haiku-4-5",
            },
            "override": {"emergency_ceo": True, "rationale": "break-glass"},
        },
        "sections": _base_sections(),
    }
    plan = compile_council_run_plan(ccp=ccp, policy=policy)
    assert plan.mode == "M2_FULL"
    assert plan.independence_required == "must"
    assert plan.compliance_flags["ceo_override"] is True
    assert plan.compliance_flags["compliance_status"] == "non-compliant-ceo-authorized"


def test_compile_plan_bootstrap_limit_blocks():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-6",
            "aur_type": "doc",
            "change_class": "hygiene",
            "blast_radius": "local",
            "reversibility": "easy",
            "uncertainty": "low",
            "touches": ["docs_only"],
            "safety_critical": False,
            "bootstrap": {"used": True, "consecutive_count": 3},
        },
        "sections": _base_sections(),
    }
    with pytest.raises(CouncilBlockedError) as exc:
        compile_council_run_plan(ccp=ccp, policy=policy)
    assert exc.value.category == "bootstrap_limit_exceeded"

```

### FILE: `runtime/tests/orchestration/council/test_schema_gate.py`

```python
from __future__ import annotations

from runtime.orchestration.council.policy import load_council_policy
from runtime.orchestration.council.schema_gate import validate_seat_output


def _valid_output() -> dict:
    return {
        "verdict": "Accept",
        "key_findings": ["- Deterministic behavior preserved"],
        "risks": ["- No major risk identified"],
        "fixes": ["- Add one integration test"],
        "confidence": "high",
        "assumptions": ["environment has git"],
        "operator_view": "Safe and simple.",
        "complexity_budget": {
            "net_human_steps": 1,
            "new_surfaces_introduced": 0,
            "surfaces_removed": 0,
            "mechanized": "yes",
            "trade_statement": "n/a",
        },
    }


def test_schema_gate_accepts_valid_output_and_labels_assumptions():
    policy = load_council_policy()
    result = validate_seat_output(_valid_output(), policy)
    assert result.valid is True
    assert result.rejected is False
    assert result.normalized_output is not None
    assert result.normalized_output["key_findings"][0].endswith("[ASSUMPTION]")
    assert any("ASSUMPTION" in warning for warning in result.warnings)


def test_schema_gate_rejects_missing_section():
    policy = load_council_policy()
    payload = _valid_output()
    payload.pop("operator_view")
    result = validate_seat_output(payload, policy)
    assert result.valid is False
    assert result.rejected is True
    assert "Missing required section: operator_view" in result.errors


def test_schema_gate_rejects_invalid_verdict():
    policy = load_council_policy()
    payload = _valid_output()
    payload["verdict"] = "PASS"
    result = validate_seat_output(payload, policy)
    assert result.valid is False
    assert result.rejected is True
    assert any("Invalid verdict" in msg for msg in result.errors)


def test_schema_gate_flags_complexity_budget_without_trade_statement():
    policy = load_council_policy()
    payload = _valid_output()
    payload["complexity_budget"]["mechanized"] = "no"
    payload["complexity_budget"]["trade_statement"] = "none"
    result = validate_seat_output(payload, policy)
    assert result.valid is True
    assert any("complexity_budget has net-positive" in msg for msg in result.warnings)

```

### FILE: `runtime/tests/orchestration/council/test_fsm.py`

```python
from __future__ import annotations

from runtime.orchestration.council.fsm import CouncilFSM
from runtime.orchestration.council.policy import load_council_policy


def _valid_seat_output(verify_ledger: bool = False) -> dict:
    return {
        "verdict": "Accept",
        "key_findings": ["- Finding with no citation"],
        "risks": ["- Minimal"],
        "fixes": ["- Add regression test"],
        "confidence": "high",
        "assumptions": ["test fixture controls runtime"],
        "operator_view": "Looks safe.",
        "complexity_budget": {
            "net_human_steps": 0,
            "new_surfaces_introduced": 0,
            "surfaces_removed": 0,
            "mechanized": "yes",
            "trade_statement": "none",
        },
        "contradiction_ledger_verified": verify_ledger,
    }


def _m1_ccp() -> dict:
    return {
        "header": {
            "aur_id": "AUR-FSM-1",
            "aur_type": "code",
            "change_class": "amend",
            "blast_radius": "module",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["tests"],
            "safety_critical": False,
        },
        "sections": {
            "objective": "Run M1 council review.",
            "scope": {"surface": "runtime"},
            "constraints": ["deterministic behavior"],
            "artifacts": [{"id": "artifact-x"}],
        },
    }


def test_fsm_m1_happy_path_complete():
    policy = load_council_policy()

    def seat_executor(seat, ccp, plan, retry_count):
        return _valid_seat_output(verify_ledger=(seat == "CoChair"))

    fsm = CouncilFSM(policy=policy, seat_executor=seat_executor)
    result = fsm.run(_m1_ccp())

    assert result.status == "complete"
    assert result.decision_payload["status"] == "COMPLETE"
    assert result.decision_payload["verdict"] == "Accept"
    assert result.run_log["execution"]["mode"] == "M1_STANDARD"
    assert result.run_log["state_transitions"][-1]["to_state"] == "TERMINAL_COMPLETE"


def test_fsm_blocks_when_cochair_does_not_verify_contradiction_ledger():
    policy = load_council_policy()

    def seat_executor(seat, ccp, plan, retry_count):
        # CoChair intentionally omits contradiction ledger verification.
        return _valid_seat_output(verify_ledger=False)

    fsm = CouncilFSM(policy=policy, seat_executor=seat_executor)
    result = fsm.run(_m1_ccp())

    assert result.status == "blocked"
    assert result.decision_payload["reason"] == "cochair_challenge_failed"


def test_fsm_retries_schema_rejects_and_recovers():
    policy = load_council_policy()
    calls = {"Chair": 0, "CoChair": 0}

    def seat_executor(seat, ccp, plan, retry_count):
        calls[seat] += 1
        if seat == "Chair" and retry_count < 2:
            return {"verdict": "Accept"}  # Missing required sections -> reject.
        return _valid_seat_output(verify_ledger=(seat == "CoChair"))

    fsm = CouncilFSM(policy=policy, seat_executor=seat_executor)
    result = fsm.run(_m1_ccp())

    assert result.status == "complete"
    chair_out = result.run_log["seat_outputs"]["Chair"]
    assert chair_out["retries_used"] == 2
    assert calls["Chair"] == 3

```

### FILE: `runtime/tests/orchestration/missions/test_review_council_runtime.py`

```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from runtime.orchestration.council.models import CouncilRuntimeResult
from runtime.orchestration.missions.base import MissionContext
from runtime.orchestration.missions.review import ReviewMission


def _context(tmp_path: Path) -> MissionContext:
    return MissionContext(
        repo_root=tmp_path,
        baseline_commit="abc123",
        run_id="review-run-1",
        operation_executor=None,
    )


def _inputs() -> dict:
    return {
        "subject_packet": {"goal": "test"},
        "review_type": "build_review",
        "use_council_runtime": True,
    }


@patch("runtime.orchestration.missions.review.load_council_policy")
@patch("runtime.orchestration.missions.review.CouncilFSM")
def test_review_mission_opt_in_maps_protocol_verdict(MockFSM, mock_load_policy, tmp_path: Path):
    mock_policy = object()
    mock_load_policy.return_value = mock_policy

    runtime_result = CouncilRuntimeResult(
        status="complete",
        run_log={"synthesis": {"verdict": "Accept"}},
        decision_payload={"status": "COMPLETE", "verdict": "Accept", "run_id": "council-1"},
        block_report=None,
    )
    MockFSM.return_value.run.return_value = runtime_result

    mission = ReviewMission()
    result = mission.run(_context(tmp_path), _inputs())

    assert result.success is True
    assert result.outputs["verdict"] == "approved"
    assert "prepare_ccp" in result.executed_steps
    assert "execute_council_fsm" in result.executed_steps
    assert result.evidence["usage"]["total"] == 0


@patch("runtime.orchestration.missions.review.load_council_policy")
@patch("runtime.orchestration.missions.review.CouncilFSM")
def test_review_mission_opt_in_handles_blocked_runtime(MockFSM, mock_load_policy, tmp_path: Path):
    mock_policy = object()
    mock_load_policy.return_value = mock_policy

    runtime_result = CouncilRuntimeResult(
        status="blocked",
        run_log={"status": "blocked"},
        decision_payload={"status": "BLOCKED", "reason": "required_seats_missing"},
        block_report={"category": "required_seats_missing", "detail": "Chair failed"},
    )
    MockFSM.return_value.run.return_value = runtime_result

    mission = ReviewMission()
    result = mission.run(_context(tmp_path), _inputs())

    assert result.success is True
    assert result.outputs["verdict"] == "escalate"
    assert "Council runtime blocked" in (result.escalation_reason or "")

```

### FILE: `config/policy/council_policy.yaml`

```yaml
protocol_version: "1.3"

required_ccp_sections:
  - objective
  - scope
  - constraints
  - artifacts

enums:
  aur_type: [governance, spec, code, doc, plan, other]
  change_class: [new, amend, refactor, hygiene, bugfix]
  blast_radius: [local, module, system, ecosystem]
  reversibility: [easy, moderate, hard]
  uncertainty: [low, medium, high]
  touches: [governance_protocol, tier_activation, runtime_core, interfaces, prompts, tests, docs_only]
  verdict: [Accept, "Go with Fixes", Reject]
  mode: [M0_FAST, M1_STANDARD, M2_FULL]
  topology: [MONO, HYBRID, DISTRIBUTED]

modes:
  default: M1_STANDARD
  M2_FULL_triggers:
    - "touches includes governance_protocol"
    - "touches includes tier_activation"
    - "touches includes runtime_core"
    - "safety_critical == true"
    - "blast_radius in [system, ecosystem] and reversibility == hard"
    - "uncertainty == high and blast_radius != local"
  M0_FAST_conditions:
    - "aur_type in [doc, plan, other]"
    - "touches == [docs_only] or (touches excludes runtime_core and touches excludes interfaces and touches excludes governance_protocol)"
    - "blast_radius == local"
    - "reversibility == easy"
    - "safety_critical == false"
    - "uncertainty == low"

seats:
  officers:
    Chair:
      required_in: [M0_FAST, M1_STANDARD, M2_FULL]
    CoChair:
      required_in: [M1_STANDARD, M2_FULL]
      optional_in: [M0_FAST]
  reviewers:
    M0_FAST: [L1UnifiedReviewer]
    M1_STANDARD: [Chair, CoChair]
    M2_FULL:
      - Chair
      - CoChair
      - Architect
      - Alignment
      - StructuralOperational
      - Technical
      - Testing
      - RiskAdversarial
      - Simplicity
      - Determinism
      - Governance

seat_role_map:
  Chair: reviewer_architect
  CoChair: reviewer_architect
  L1UnifiedReviewer: reviewer_architect
  Architect: reviewer_architect
  Alignment: reviewer_architect
  StructuralOperational: reviewer_architect
  Technical: reviewer_architect
  Testing: reviewer_architect
  RiskAdversarial: reviewer_security
  Simplicity: reviewer_architect
  Determinism: reviewer_architect
  Governance: reviewer_architect

independence:
  must_conditions:
    triggers:
      - "safety_critical == true"
      - "touches includes governance_protocol"
      - "touches includes tier_activation"
    enforcement: "At least one of RiskAdversarial or Governance must run on independent model family"
  should_conditions:
    triggers:
      - "touches includes runtime_core"
      - "uncertainty == high and blast_radius != local"
    enforcement: "At least one of RiskAdversarial or Governance should run on independent model family"

schema_gate:
  max_retry_cycles: 2
  required_sections:
    - verdict
    - key_findings
    - risks
    - fixes
    - confidence
    - assumptions
    - complexity_budget
    - operator_view
  evidence_rule: "Material claims require REF: citation or ASSUMPTION label"

closure:
  max_prompt_closure_cycles: 2
  build_script: "scripts/closure/build_closure_bundle.py"
  validate_script: "scripts/closure/validate_closure_bundle.py"

bootstrap:
  max_consecutive_without_cso: 2
  restore_deadline_hours: 24
  safety_critical_requires_ceo_approval: true

model_families:
  anthropic:
    - claude-opus-4-5
    - claude-sonnet-4-5
    - claude-haiku-4-5
  openai:
    - gpt-4o
    - o1
    - o3-mini
  google:
    - gemini-2.0-flash
    - gemini-2.0-pro

```

### FILE: `runtime/orchestration/council/__init__.py`

```python
"""Policy-driven council runtime package."""

from .compiler import compile_council_run_plan
from .fsm import CouncilFSM
from .models import (
    CouncilBlockedError,
    CouncilRunPlan,
    CouncilRuntimeError,
    CouncilRuntimeResult,
    CouncilSeatResult,
    CouncilTransition,
)
from .policy import CouncilPolicy, evaluate_expression, load_council_policy, resolve_model_family
from .schema_gate import SchemaGateResult, validate_seat_output

__all__ = [
    "CouncilBlockedError",
    "CouncilFSM",
    "CouncilPolicy",
    "CouncilRunPlan",
    "CouncilRuntimeError",
    "CouncilRuntimeResult",
    "CouncilSeatResult",
    "CouncilTransition",
    "SchemaGateResult",
    "compile_council_run_plan",
    "evaluate_expression",
    "load_council_policy",
    "resolve_model_family",
    "validate_seat_output",
]

```

### FILE: `runtime/orchestration/council/models.py`

```python
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

```

### FILE: `runtime/orchestration/council/policy.py`

```python
"""
Council policy loading and expression evaluation utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from .models import CouncilRuntimeError


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_policy_path() -> Path:
    return _repo_root() / "config" / "policy" / "council_policy.yaml"


def _strip_outer_parens(expr: str) -> str:
    expr = expr.strip()
    while expr.startswith("(") and expr.endswith(")"):
        depth = 0
        balanced = True
        for i, ch in enumerate(expr):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth < 0:
                    balanced = False
                    break
                if depth == 0 and i != len(expr) - 1:
                    balanced = False
                    break
        if not balanced or depth != 0:
            break
        expr = expr[1:-1].strip()
    return expr


def _split_top_level(expr: str, op: str) -> list[str]:
    pieces: list[str] = []
    depth = 0
    i = 0
    start = 0
    token = f" {op} "
    while i < len(expr):
        ch = expr[i]
        if ch == "(":
            depth += 1
            i += 1
            continue
        if ch == ")":
            depth -= 1
            i += 1
            continue
        if depth == 0 and expr.startswith(token, i):
            pieces.append(expr[start:i].strip())
            i += len(token)
            start = i
            continue
        i += 1
    pieces.append(expr[start:].strip())
    return [piece for piece in pieces if piece]


def _parse_literal(raw: str) -> Any:
    value = raw.strip()
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_parse_literal(part) for part in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    if value.isdigit():
        return int(value)
    return value


def _get_path_value(data: Mapping[str, Any], field_path: str) -> Any:
    current: Any = data
    for part in field_path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            return None
        current = current[part]
    return current


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _eval_predicate(predicate: str, metadata: Mapping[str, Any]) -> bool:
    normalized = " ".join(predicate.strip().split())
    if " includes " in normalized:
        field, rhs = normalized.split(" includes ", 1)
        lhs_values = _as_list(_get_path_value(metadata, field.strip()))
        rhs_value = _parse_literal(rhs)
        return rhs_value in lhs_values
    if " excludes " in normalized:
        field, rhs = normalized.split(" excludes ", 1)
        lhs_values = _as_list(_get_path_value(metadata, field.strip()))
        rhs_value = _parse_literal(rhs)
        return rhs_value not in lhs_values
    if " not in " in normalized:
        field, rhs = normalized.split(" not in ", 1)
        lhs_value = _get_path_value(metadata, field.strip())
        rhs_values = _as_list(_parse_literal(rhs))
        return lhs_value not in rhs_values
    if " in " in normalized:
        field, rhs = normalized.split(" in ", 1)
        lhs_value = _get_path_value(metadata, field.strip())
        rhs_values = _as_list(_parse_literal(rhs))
        return lhs_value in rhs_values
    if " == " in normalized:
        field, rhs = normalized.split(" == ", 1)
        lhs_value = _get_path_value(metadata, field.strip())
        rhs_value = _parse_literal(rhs)
        if isinstance(rhs_value, list):
            lhs_values = _as_list(lhs_value)
            return sorted(lhs_values) == sorted(rhs_value)
        return lhs_value == rhs_value
    if " != " in normalized:
        field, rhs = normalized.split(" != ", 1)
        lhs_value = _get_path_value(metadata, field.strip())
        rhs_value = _parse_literal(rhs)
        if isinstance(rhs_value, list):
            lhs_values = _as_list(lhs_value)
            return sorted(lhs_values) != sorted(rhs_value)
        return lhs_value != rhs_value
    raise CouncilRuntimeError(f"Unsupported policy predicate: {predicate}")


def evaluate_expression(expression: str, metadata: Mapping[str, Any]) -> bool:
    """
    Evaluate a council policy expression against CCP metadata.

    Supported operators:
    - and / or with parenthesis grouping
    - includes / excludes for list-like fields
    - == / !=
    - in / not in
    """
    expr = _strip_outer_parens(expression.strip())
    if not expr:
        return False

    or_parts = _split_top_level(expr, "or")
    if len(or_parts) > 1:
        return any(evaluate_expression(part, metadata) for part in or_parts)

    and_parts = _split_top_level(expr, "and")
    if len(and_parts) > 1:
        return all(evaluate_expression(part, metadata) for part in and_parts)

    return _eval_predicate(expr, metadata)


def resolve_model_family(model_name: str, registry: Mapping[str, list[str]]) -> str:
    """
    Resolve model family from explicit registry, then fallback heuristics.
    """
    lower_name = (model_name or "").lower()
    for family, models in registry.items():
        for declared in models:
            d = declared.lower()
            if lower_name == d or lower_name.endswith(f"/{d}") or d in lower_name:
                return family
    if "claude" in lower_name:
        return "anthropic"
    if "gpt" in lower_name or lower_name.startswith("o1") or lower_name.startswith("o3"):
        return "openai"
    if "gemini" in lower_name:
        return "google"
    if "/" in lower_name:
        return lower_name.split("/", 1)[0]
    return "unknown"


@dataclass(frozen=True)
class CouncilPolicy:
    """Structured accessor for `config/policy/council_policy.yaml`."""

    raw: Mapping[str, Any]

    @property
    def protocol_version(self) -> str:
        return str(self.raw.get("protocol_version", "unknown"))

    @property
    def enums(self) -> Mapping[str, list[Any]]:
        return self.raw.get("enums", {})

    @property
    def required_ccp_sections(self) -> tuple[str, ...]:
        sections = self.raw.get("required_ccp_sections", [])
        return tuple(str(s) for s in sections)

    @property
    def schema_gate_required_sections(self) -> tuple[str, ...]:
        gate = self.raw.get("schema_gate", {})
        return tuple(str(s) for s in gate.get("required_sections", []))

    @property
    def schema_gate_retry_cap(self) -> int:
        gate = self.raw.get("schema_gate", {})
        retry_cap = gate.get("max_retry_cycles", 2)
        if not isinstance(retry_cap, int) or retry_cap < 0:
            return 2
        return retry_cap

    @property
    def closure_retry_cap(self) -> int:
        closure = self.raw.get("closure", {})
        retry_cap = closure.get("max_prompt_closure_cycles", 2)
        if not isinstance(retry_cap, int) or retry_cap < 0:
            return 2
        return retry_cap

    @property
    def seat_role_map(self) -> Mapping[str, str]:
        return self.raw.get("seat_role_map", {})

    @property
    def model_families(self) -> Mapping[str, list[str]]:
        return self.raw.get("model_families", {})

    @property
    def mode_default(self) -> str:
        return str(self.raw.get("modes", {}).get("default", "M1_STANDARD"))

    def mode_m2_triggers(self) -> tuple[str, ...]:
        entries = self.raw.get("modes", {}).get("M2_FULL_triggers", [])
        return tuple(str(s) for s in entries)

    def mode_m0_conditions(self) -> tuple[str, ...]:
        entries = self.raw.get("modes", {}).get("M0_FAST_conditions", [])
        return tuple(str(s) for s in entries)

    def required_seats_for_mode(self, mode: str) -> tuple[str, ...]:
        reviewers = self.raw.get("seats", {}).get("reviewers", {})
        seats = reviewers.get(mode, [])
        return tuple(str(seat) for seat in seats)

    def independence_must_triggers(self) -> tuple[str, ...]:
        triggers = (
            self.raw.get("independence", {})
            .get("must_conditions", {})
            .get("triggers", [])
        )
        return tuple(str(s) for s in triggers)

    def independence_should_triggers(self) -> tuple[str, ...]:
        triggers = (
            self.raw.get("independence", {})
            .get("should_conditions", {})
            .get("triggers", [])
        )
        return tuple(str(s) for s in triggers)

    @property
    def bootstrap_policy(self) -> Mapping[str, Any]:
        return self.raw.get("bootstrap", {})


def load_council_policy(policy_path: str | Path | None = None) -> CouncilPolicy:
    """
    Load council runtime policy from YAML.
    """
    path = Path(policy_path) if policy_path else _default_policy_path()
    if not path.exists():
        raise CouncilRuntimeError(f"Council policy not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        parsed = yaml.safe_load(handle)
    if not isinstance(parsed, dict):
        raise CouncilRuntimeError(f"Council policy is invalid: {path}")
    return CouncilPolicy(raw=parsed)

```

### FILE: `runtime/orchestration/council/compiler.py`

```python
"""
Compiler for producing an immutable CouncilRunPlan from CCP + policy.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from runtime.agents.models import resolve_model_auto, load_model_config

from .models import CouncilBlockedError, CouncilRunPlan, generate_run_id
from .policy import CouncilPolicy, evaluate_expression, resolve_model_family


def _normalize_metadata(ccp: Mapping[str, Any]) -> dict[str, Any]:
    header = ccp.get("header")
    if isinstance(header, dict):
        meta = dict(header)
    else:
        meta = dict(ccp)
    touches = meta.get("touches")
    if touches is None:
        meta["touches"] = []
    elif isinstance(touches, str):
        meta["touches"] = [touches]
    elif isinstance(touches, (tuple, set)):
        meta["touches"] = list(touches)
    return meta


def _validate_required_sections(
    ccp: Mapping[str, Any], required_sections: tuple[str, ...]
) -> None:
    sections = ccp.get("sections", {})
    if not isinstance(sections, Mapping):
        sections = {}
    missing: list[str] = []
    for section in required_sections:
        value = sections.get(section, ccp.get(section))
        if value is None:
            missing.append(section)
            continue
        if isinstance(value, str) and not value.strip():
            missing.append(section)
            continue
        if isinstance(value, (list, dict)) and len(value) == 0:
            missing.append(section)
    if missing:
        raise CouncilBlockedError(
            "ccp_incomplete",
            f"Missing required CCP sections: {', '.join(sorted(missing))}",
        )


def _validate_enum_fields(metadata: Mapping[str, Any], policy: CouncilPolicy) -> None:
    enums = policy.enums
    for key, allowed in enums.items():
        if key not in metadata:
            continue
        value = metadata.get(key)
        if key == "touches":
            values = value if isinstance(value, list) else [value]
            unknown = [v for v in values if v not in allowed]
            if unknown:
                raise CouncilBlockedError(
                    "unknown_enum_value",
                    f"{key}: unknown value(s): {sorted(set(str(v) for v in unknown))}",
                )
            continue
        if value not in allowed:
            raise CouncilBlockedError(
                "unknown_enum_value",
                f"{key}: '{value}' is not one of {allowed}",
            )


def _resolve_mode(metadata: Mapping[str, Any], policy: CouncilPolicy) -> str:
    override = metadata.get("override", {})
    if isinstance(override, Mapping) and override.get("mode"):
        return str(override.get("mode"))
    if any(evaluate_expression(expr, metadata) for expr in policy.mode_m2_triggers()):
        return "M2_FULL"
    if all(evaluate_expression(expr, metadata) for expr in policy.mode_m0_conditions()):
        return "M0_FAST"
    return policy.mode_default


def _resolve_independence_required(metadata: Mapping[str, Any], mode: str, policy: CouncilPolicy) -> str:
    must_triggered = any(
        evaluate_expression(expr, metadata) for expr in policy.independence_must_triggers()
    )
    should_triggered = any(
        evaluate_expression(expr, metadata) for expr in policy.independence_should_triggers()
    )
    if must_triggered and mode == "M2_FULL":
        return "must"
    if should_triggered:
        return "should"
    return "none"


def _resolve_topology(
    metadata: Mapping[str, Any], mode: str, independence_required: str
) -> str:
    override = metadata.get("override", {})
    if isinstance(override, Mapping) and override.get("topology"):
        return str(override.get("topology"))
    if mode == "M0_FAST":
        return "MONO"
    if mode == "M1_STANDARD":
        return "HYBRID" if independence_required == "should" else "MONO"
    if mode == "M2_FULL":
        independent_seat_count = int(metadata.get("independent_seat_count", 1) or 1)
        return "DISTRIBUTED" if independent_seat_count > 1 else "HYBRID"
    return "MONO"


def _resolve_default_models() -> tuple[str, str]:
    try:
        config = load_model_config()
        primary, _, _ = resolve_model_auto("reviewer_architect", config=config)
        independent, _, _ = resolve_model_auto("reviewer_security", config=config)
        return primary, independent
    except Exception:
        return ("claude-sonnet-4-5", "opencode/glm-5-free")


def _assign_models(
    required_seats: tuple[str, ...],
    topology: str,
    independence_required: str,
    metadata: Mapping[str, Any],
    seat_role_map: Mapping[str, str],
) -> dict[str, str]:
    model_plan = metadata.get("model_plan_v1", metadata.get("model_plan", {}))
    if not isinstance(model_plan, Mapping):
        model_plan = {}

    primary_default, independent_default = _resolve_default_models()
    primary_model = str(model_plan.get("primary", primary_default))
    independent_model = str(model_plan.get("independent", independent_default))
    seat_overrides = model_plan.get("seat_overrides", {})
    if not isinstance(seat_overrides, Mapping):
        seat_overrides = {}
    role_overrides = model_plan.get("role_to_model", {})
    if not isinstance(role_overrides, Mapping):
        role_overrides = {}

    assignments: dict[str, str] = {}
    independent_targets = {"RiskAdversarial", "Governance"}
    for seat in required_seats:
        if seat in seat_overrides:
            assignments[seat] = str(seat_overrides[seat])
            continue
        seat_role = seat_role_map.get(seat, "reviewer_architect")
        if seat_role in role_overrides:
            assignments[seat] = str(role_overrides[seat_role])
            continue
        if topology == "MONO":
            assignments[seat] = primary_model
            continue
        if topology == "DISTRIBUTED":
            if seat in independent_targets and independence_required in {"must", "should"}:
                assignments[seat] = independent_model
            else:
                try:
                    role_model, _, _ = resolve_model_auto(seat_role, config=load_model_config())
                    assignments[seat] = role_model
                except Exception:
                    assignments[seat] = primary_model
            continue
        # HYBRID
        if seat == "RiskAdversarial" and independence_required in {"must", "should"}:
            assignments[seat] = independent_model
        else:
            assignments[seat] = primary_model
    return assignments


def _resolve_independence(
    metadata: Mapping[str, Any],
    policy: CouncilPolicy,
    required_seats: tuple[str, ...],
    assignments: dict[str, str],
    independence_required: str,
) -> tuple[bool, tuple[str, ...], dict[str, Any]]:
    compliance_flags: dict[str, Any] = {}
    if independence_required == "none":
        return True, tuple(), compliance_flags

    chair_model = assignments.get("Chair")
    if chair_model is None and required_seats:
        chair_model = assignments.get(required_seats[0], "")
    chair_family = resolve_model_family(chair_model or "", policy.model_families)

    independent_candidates = [seat for seat in ("RiskAdversarial", "Governance") if seat in assignments]
    independent_seats = tuple(
        seat
        for seat in independent_candidates
        if resolve_model_family(assignments[seat], policy.model_families) != chair_family
    )

    if independent_seats:
        return True, independent_seats, compliance_flags

    model_plan = metadata.get("model_plan_v1", metadata.get("model_plan", {}))
    independent_model = ""
    if isinstance(model_plan, Mapping):
        independent_model = str(model_plan.get("independent", ""))

    if independent_model:
        independent_family = resolve_model_family(independent_model, policy.model_families)
        if independent_family != chair_family and independent_candidates:
            target = independent_candidates[0]
            assignments[target] = independent_model
            return True, (target,), compliance_flags

    override = metadata.get("override", {})
    emergency_override = bool(
        isinstance(override, Mapping) and override.get("emergency_ceo", False)
    )
    if independence_required == "must":
        if emergency_override:
            compliance_flags["compliance_status"] = "non-compliant-ceo-authorized"
            compliance_flags["cso_notification_required"] = True
            return False, tuple(), compliance_flags
        raise CouncilBlockedError(
            "independence_unsatisfied",
            "MUST independence condition could not be satisfied; emergency CEO override absent.",
        )

    # SHOULD path
    compliance_flags["independence_waived"] = True
    compliance_flags["override_rationale"] = (
        override.get("rationale")
        if isinstance(override, Mapping)
        else "independent model unavailable"
    )
    return False, tuple(), compliance_flags


def _enforce_bootstrap(metadata: Mapping[str, Any], policy: CouncilPolicy) -> dict[str, Any]:
    flags = {"bootstrap_used": False}
    bootstrap = metadata.get("bootstrap", {})
    if not isinstance(bootstrap, Mapping):
        return flags
    if not bootstrap.get("used", False):
        return flags

    flags["bootstrap_used"] = True
    consecutive = int(bootstrap.get("consecutive_count", 1) or 1)
    max_without_cso = int(policy.bootstrap_policy.get("max_consecutive_without_cso", 2))
    if consecutive > max_without_cso:
        raise CouncilBlockedError(
            "bootstrap_limit_exceeded",
            f"Bootstrap consecutive count {consecutive} exceeds limit {max_without_cso}.",
        )

    safety_critical = bool(metadata.get("safety_critical", False))
    requires_ceo = bool(
        policy.bootstrap_policy.get("safety_critical_requires_ceo_approval", True)
    )
    if safety_critical and requires_ceo and not bool(bootstrap.get("ceo_approved", False)):
        raise CouncilBlockedError(
            "bootstrap_requires_ceo_approval",
            "Safety-critical bootstrap run requires explicit CEO approval.",
        )
    return flags


def compile_council_run_plan(
    ccp: Mapping[str, Any],
    policy: CouncilPolicy,
) -> CouncilRunPlan:
    """
    Compile immutable CouncilRunPlan from CCP metadata and loaded policy.
    """
    metadata = _normalize_metadata(ccp)
    _validate_required_sections(ccp, policy.required_ccp_sections)
    _validate_enum_fields(metadata, policy)

    mode = _resolve_mode(metadata, policy)
    if mode not in policy.enums.get("mode", []):
        raise CouncilBlockedError("unknown_mode", f"Resolved mode '{mode}' is not policy-allowed.")

    independence_required = _resolve_independence_required(metadata, mode, policy)
    topology = _resolve_topology(metadata, mode, independence_required)
    if topology not in policy.enums.get("topology", []):
        raise CouncilBlockedError(
            "unknown_topology",
            f"Resolved topology '{topology}' is not policy-allowed.",
        )

    required_seats = policy.required_seats_for_mode(mode)
    if not required_seats:
        raise CouncilBlockedError(
            "seat_resolution_failed",
            f"No seats configured for mode '{mode}'.",
        )

    seat_role_map = {
        seat: policy.seat_role_map.get(seat, "reviewer_architect")
        for seat in required_seats
    }
    model_assignments = _assign_models(
        required_seats=required_seats,
        topology=topology,
        independence_required=independence_required,
        metadata=metadata,
        seat_role_map=seat_role_map,
    )

    independence_satisfied, independent_seats, compliance_independence = _resolve_independence(
        metadata=metadata,
        policy=policy,
        required_seats=required_seats,
        assignments=model_assignments,
        independence_required=independence_required,
    )
    bootstrap_flags = _enforce_bootstrap(metadata, policy)

    override = metadata.get("override", {})
    override_active = isinstance(override, Mapping) and (
        bool(override.get("mode"))
        or bool(override.get("topology"))
        or bool(override.get("emergency_ceo"))
    )
    override_rationale = (
        str(override.get("rationale"))
        if isinstance(override, Mapping) and override.get("rationale")
        else None
    )

    compliance_flags: dict[str, Any] = {
        **bootstrap_flags,
        **compliance_independence,
        "ceo_override": bool(
            isinstance(override, Mapping) and override.get("emergency_ceo", False)
        ),
        "waivers": list(metadata.get("waivers", []))
        if isinstance(metadata.get("waivers"), list)
        else [],
    }

    aur_id = str(metadata.get("aur_id", ccp.get("aur_id", "unknown_aur")))
    run_id = str(metadata.get("run_id", generate_run_id()))
    timestamp = str(
        metadata.get(
            "timestamp",
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
    )

    return CouncilRunPlan(
        aur_id=aur_id,
        run_id=run_id,
        timestamp=timestamp,
        mode=mode,
        topology=topology,
        required_seats=required_seats,
        model_assignments=model_assignments,
        seat_role_map=seat_role_map,
        independence_required=independence_required,
        independence_satisfied=independence_satisfied,
        independent_seats=independent_seats,
        compliance_flags=compliance_flags,
        override_active=override_active,
        override_rationale=override_rationale,
        cochair_required=(mode != "M0_FAST"),
        contradiction_ledger_required=(mode in {"M1_STANDARD", "M2_FULL"}),
        closure_gate_required=bool(metadata.get("closure_gate_required", True)),
    )

```

### FILE: `runtime/orchestration/council/schema_gate.py`

```python
"""
Deterministic schema gate for council seat outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
import copy
import re

import yaml

from .policy import CouncilPolicy


P0_ALLOWED_CATEGORIES = {
    "determinism",
    "auditability",
    "authority_chain",
    "governance_boundary",
    "security_boundary",
    "correctness",
}


@dataclass
class SchemaGateResult:
    """Outcome of deterministic schema validation for one seat output."""

    valid: bool
    rejected: bool
    normalized_output: dict[str, Any] | None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _normalize_packet(raw_output: dict[str, Any] | str) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if isinstance(raw_output, dict):
        return copy.deepcopy(raw_output), errors
    if isinstance(raw_output, str):
        text = raw_output.strip()
        if not text:
            errors.append("Seat output is empty.")
            return None, errors
        try:
            parsed = yaml.safe_load(text)
        except Exception as exc:
            errors.append(f"Seat output is not valid YAML/JSON: {exc}")
            return None, errors
        if not isinstance(parsed, dict):
            errors.append("Seat output must parse to an object.")
            return None, errors
        return parsed, errors
    errors.append(f"Seat output type '{type(raw_output).__name__}' is unsupported.")
    return None, errors


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _add_assumption_labels(output: dict[str, Any], warnings: list[str]) -> None:
    for section in ("key_findings", "risks", "fixes"):
        value = output.get(section)
        if not isinstance(value, list):
            continue
        normalized: list[Any] = []
        for item in value:
            if isinstance(item, str):
                has_ref = "REF:" in item
                has_assumption = "[ASSUMPTION]" in item
                if not has_ref and not has_assumption:
                    normalized.append(f"{item} [ASSUMPTION]")
                    warnings.append(f"{section}: added ASSUMPTION label for claim without REF.")
                else:
                    normalized.append(item)
                continue
            if isinstance(item, dict):
                claim_text = str(item.get("claim", item.get("text", "")))
                has_ref = "REF:" in claim_text or bool(item.get("ref"))
                if not has_ref:
                    item = dict(item)
                    item["assumption"] = True
                    warnings.append(f"{section}: added assumption=true for claim without REF.")
                normalized.append(item)
                continue
            normalized.append(item)
        output[section] = normalized


def _parse_net_steps(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        cleaned = value.strip()
        if re.fullmatch(r"[+-]?\d+", cleaned):
            return int(cleaned)
    return None


def _validate_complexity_budget(output: dict[str, Any], warnings: list[str]) -> None:
    budget = output.get("complexity_budget")
    if not isinstance(budget, dict):
        warnings.append("complexity_budget is missing or malformed.")
        return
    required = (
        "net_human_steps",
        "new_surfaces_introduced",
        "surfaces_removed",
        "mechanized",
        "trade_statement",
    )
    missing = [key for key in required if key not in budget]
    if missing:
        warnings.append(
            f"complexity_budget missing fields: {', '.join(sorted(missing))}"
        )
        return

    net_steps = _parse_net_steps(budget.get("net_human_steps"))
    mechanized = str(budget.get("mechanized", "")).strip().lower()
    trade_statement = str(budget.get("trade_statement", "")).strip().lower()
    if net_steps is not None and net_steps > 0 and mechanized == "no" and trade_statement in {"", "none"}:
        warnings.append(
            "complexity_budget has net-positive human steps without mechanization trade statement."
        )


def _validate_p0_labels(output: dict[str, Any], warnings: list[str]) -> None:
    findings = output.get("key_findings")
    if not isinstance(findings, list):
        return
    for idx, finding in enumerate(findings):
        if isinstance(finding, dict):
            priority = str(finding.get("priority", "")).upper()
            if priority != "P0":
                continue
            category = str(finding.get("category", "")).lower()
            if category not in P0_ALLOWED_CATEGORIES:
                warnings.append(
                    f"key_findings[{idx}] uses P0 without recognized blocker category."
                )
            continue
        if isinstance(finding, str) and "P0" in finding:
            lowered = finding.lower()
            if not any(category in lowered for category in P0_ALLOWED_CATEGORIES):
                warnings.append(
                    f"key_findings[{idx}] may have P0 inflation without blocker category."
                )


def validate_seat_output(
    raw_output: dict[str, Any] | str,
    policy: CouncilPolicy,
) -> SchemaGateResult:
    """
    Validate and normalize a seat output packet deterministically.
    """
    normalized, parse_errors = _normalize_packet(raw_output)
    if normalized is None:
        return SchemaGateResult(
            valid=False,
            rejected=True,
            normalized_output=None,
            errors=parse_errors,
            warnings=[],
        )

    errors = list(parse_errors)
    warnings: list[str] = []

    for section in policy.schema_gate_required_sections:
        if section not in normalized or _is_empty(normalized.get(section)):
            errors.append(f"Missing required section: {section}")

    verdict = normalized.get("verdict")
    allowed_verdicts = set(policy.enums.get("verdict", []))
    if verdict not in allowed_verdicts:
        errors.append(
            f"Invalid verdict '{verdict}'. Allowed values: {sorted(allowed_verdicts)}"
        )

    _add_assumption_labels(normalized, warnings)
    _validate_complexity_budget(normalized, warnings)
    _validate_p0_labels(normalized, warnings)

    rejected = len(errors) > 0
    return SchemaGateResult(
        valid=not rejected,
        rejected=rejected,
        normalized_output=normalized,
        errors=errors,
        warnings=warnings,
    )

```

### FILE: `runtime/orchestration/council/fsm.py`

```python
"""
Deterministic state machine for council review execution.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Mapping

from runtime.agents.api import AgentCall, call_agent

from .compiler import compile_council_run_plan
from .models import (
    CouncilBlockedError,
    CouncilRunPlan,
    CouncilRuntimeResult,
    CouncilSeatResult,
    CouncilTransition,
)
from .policy import CouncilPolicy
from .schema_gate import validate_seat_output


SeatExecutor = Callable[[str, Mapping[str, Any], CouncilRunPlan, int], dict[str, Any] | str]
ClosureCallable = Callable[[Mapping[str, Any], CouncilRunPlan], tuple[bool, dict[str, Any]]]


STATE_S0_ASSEMBLE = "S0_ASSEMBLE"
STATE_S0_5_COCHAIR_VALIDATE = "S0_5_COCHAIR_VALIDATE"
STATE_S1_EXECUTE_SEATS = "S1_EXECUTE_SEATS"
STATE_S1_25_SCHEMA_GATE = "S1_25_SCHEMA_GATE"
STATE_S1_5_SEAT_COMPLETION = "S1_5_SEAT_COMPLETION"
STATE_S2_SYNTHESIS = "S2_SYNTHESIS"
STATE_S2_5_COCHAIR_CHALLENGE = "S2_5_COCHAIR_CHALLENGE"
STATE_S3_CLOSURE_GATE = "S3_CLOSURE_GATE"
STATE_S4_CLOSEOUT = "S4_CLOSEOUT"
STATE_TERMINAL_BLOCKED = "TERMINAL_BLOCKED"
STATE_TERMINAL_COMPLETE = "TERMINAL_COMPLETE"


def _default_seat_executor(
    seat: str,
    ccp: Mapping[str, Any],
    plan: CouncilRunPlan,
    retry_count: int,
) -> dict[str, Any] | str:
    """
    Default seat executor using the Agent API.
    """
    role = plan.seat_role_map.get(seat, "reviewer_architect")
    model = plan.model_assignments.get(seat, "auto")
    packet = {
        "ccp": ccp,
        "seat": seat,
        "plan": {
            "mode": plan.mode,
            "topology": plan.topology,
            "required_sections": list(ccp.get("sections", {}).keys())
            if isinstance(ccp.get("sections"), Mapping)
            else [],
        },
        "retry_count": retry_count,
    }
    response = call_agent(
        AgentCall(
            role=role,
            packet=packet,
            model=model,
        ),
        run_id=plan.run_id,
    )
    if response.packet is not None:
        return response.packet
    return response.content


def _default_closure_builder(
    synthesis: Mapping[str, Any], plan: CouncilRunPlan
) -> tuple[bool, dict[str, Any]]:
    """
    Default closure-build hook. Side-effect free unless caller injects a real hook.
    """
    return True, {"builder": "noop", "run_id": plan.run_id, "synthesis_verdict": synthesis.get("verdict")}


def _default_closure_validator(
    synthesis: Mapping[str, Any], plan: CouncilRunPlan
) -> tuple[bool, dict[str, Any]]:
    """
    Default closure-validate hook. Side-effect free unless caller injects a real hook.
    """
    return True, {"validator": "noop", "run_id": plan.run_id, "synthesis_verdict": synthesis.get("verdict")}


class CouncilFSM:
    """
    Protocol-aligned council review runtime.
    """

    def __init__(
        self,
        policy: CouncilPolicy,
        seat_executor: SeatExecutor | None = None,
        closure_builder: ClosureCallable | None = None,
        closure_validator: ClosureCallable | None = None,
    ):
        self.policy = policy
        self.seat_executor = seat_executor or _default_seat_executor
        self.closure_builder = closure_builder or _default_closure_builder
        self.closure_validator = closure_validator or _default_closure_validator

    @staticmethod
    def _transition(
        transitions: list[CouncilTransition],
        from_state: str,
        to_state: str,
        reason: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        transitions.append(
            CouncilTransition(
                from_state=from_state,
                to_state=to_state,
                reason=reason,
                details=details or {},
            )
        )

    @staticmethod
    def _waived_seats(ccp: Mapping[str, Any]) -> set[str]:
        waivers = ccp.get("waived_seats", [])
        if not isinstance(waivers, list):
            return set()
        return {str(item) for item in waivers}

    @staticmethod
    def _cochair_validate_ccp(ccp: Mapping[str, Any], plan: CouncilRunPlan) -> tuple[bool, str]:
        required_sections = {"objective", "scope", "constraints", "artifacts"}
        sections = ccp.get("sections", {})
        if not isinstance(sections, Mapping):
            return False, "CCP sections block missing."
        missing = [section for section in sorted(required_sections) if section not in sections]
        if missing:
            return False, f"Missing required sections: {', '.join(missing)}"
        if not plan.cochair_required:
            return True, "cochair_not_required"
        return True, "cochair_validation_passed"

    @staticmethod
    def _extract_verdict(seat_outputs: Mapping[str, CouncilSeatResult]) -> str:
        verdicts = []
        for result in seat_outputs.values():
            payload = result.normalized_output or {}
            verdict = payload.get("verdict")
            if isinstance(verdict, str):
                verdicts.append(verdict)
        if not verdicts:
            return "Reject"
        if "Reject" in verdicts:
            return "Reject"
        if "Go with Fixes" in verdicts:
            return "Go with Fixes"
        return "Accept"

    @staticmethod
    def _aggregate_complexity(seat_outputs: Mapping[str, CouncilSeatResult]) -> dict[str, Any]:
        total_net_human_steps = 0
        total_new_surfaces = 0
        total_surfaces_removed = 0
        unmechanized_additions = 0

        for result in seat_outputs.values():
            budget = (result.normalized_output or {}).get("complexity_budget", {})
            if not isinstance(budget, Mapping):
                continue
            net_raw = budget.get("net_human_steps", 0)
            if isinstance(net_raw, str):
                cleaned = net_raw.strip()
                net = int(cleaned) if cleaned.lstrip("+-").isdigit() else 0
            elif isinstance(net_raw, int):
                net = net_raw
            else:
                net = 0
            total_net_human_steps += net

            total_new_surfaces += int(budget.get("new_surfaces_introduced", 0) or 0)
            total_surfaces_removed += int(budget.get("surfaces_removed", 0) or 0)
            mechanized = str(budget.get("mechanized", "")).strip().lower()
            if net > 0 and mechanized == "no":
                unmechanized_additions += 1

        return {
            "governance_creep_flag": bool(total_net_human_steps > 0 and unmechanized_additions > 0),
            "total_net_human_steps": total_net_human_steps,
            "total_new_surfaces": total_new_surfaces,
            "total_surfaces_removed": total_surfaces_removed,
            "unmechanized_additions": unmechanized_additions,
        }

    def _build_contradiction_ledger(
        self, seat_outputs: Mapping[str, CouncilSeatResult], required: bool
    ) -> list[dict[str, Any]]:
        if not required:
            return []
        by_verdict: dict[str, list[str]] = {}
        for seat, result in seat_outputs.items():
            verdict = str((result.normalized_output or {}).get("verdict", "unknown"))
            by_verdict.setdefault(verdict, []).append(seat)
        if len(by_verdict) <= 1:
            return []
        ledger = []
        for verdict, seats in sorted(by_verdict.items()):
            ledger.append(
                {
                    "resolution": "requires synthesis reconciliation",
                    "seats": sorted(seats),
                    "verdict": verdict,
                }
            )
        return ledger

    def _synthesize(
        self,
        seat_outputs: Mapping[str, CouncilSeatResult],
        plan: CouncilRunPlan,
        ccp: Mapping[str, Any],
    ) -> dict[str, Any]:
        chair_output = (seat_outputs.get("Chair") or seat_outputs.get("L1UnifiedReviewer"))
        chair_payload = chair_output.normalized_output if chair_output else {}
        if not isinstance(chair_payload, Mapping):
            chair_payload = {}

        contradiction_ledger = self._build_contradiction_ledger(
            seat_outputs=seat_outputs,
            required=plan.contradiction_ledger_required,
        )
        rollup = self._aggregate_complexity(seat_outputs)

        synthesis = {
            "ceo_decisions": list(chair_payload.get("ceo_decisions", []))
            if isinstance(chair_payload.get("ceo_decisions"), list)
            else [],
            "change_list": list(chair_payload.get("fixes", []))
            if isinstance(chair_payload.get("fixes"), list)
            else [],
            "contradiction_ledger": contradiction_ledger,
            "deletion_line": str(
                chair_payload.get(
                    "deletion_line",
                    "Nothing — no deletion requested by synthesized council output.",
                )
            ),
            "fix_plan": list(chair_payload.get("fixes", []))
            if isinstance(chair_payload.get("fixes"), list)
            else [],
            "mechanization_plan": list(chair_payload.get("mechanization_plan", []))
            if isinstance(chair_payload.get("mechanization_plan"), list)
            else [],
            "run_complexity_rollup": rollup,
            "verdict": self._extract_verdict(seat_outputs),
        }

        if bool(plan.compliance_flags.get("bootstrap_used", False)):
            synthesis["fix_plan"].append(
                {
                    "owner": "operations",
                    "priority": "P0",
                    "text": "Restore canonical artifacts and re-run council validation.",
                }
            )
        return synthesis

    @staticmethod
    def _challenge_synthesis(
        synthesis: Mapping[str, Any],
        seat_outputs: Mapping[str, CouncilSeatResult],
        plan: CouncilRunPlan,
    ) -> tuple[bool, str]:
        if not plan.cochair_required:
            return True, "cochair_not_required"

        cochair = seat_outputs.get("CoChair")
        if cochair is None or cochair.normalized_output is None:
            return False, "CoChair output missing."

        if plan.contradiction_ledger_required:
            ledger = synthesis.get("contradiction_ledger")
            if not isinstance(ledger, list):
                return False, "Contradiction Ledger missing from synthesis."
            if plan.topology == "MONO":
                verified = bool(cochair.normalized_output.get("contradiction_ledger_verified", False))
                if not verified:
                    return False, "CoChair did not verify contradiction ledger completeness."
        return True, "cochair_challenge_passed"

    def run(self, ccp: Mapping[str, Any]) -> CouncilRuntimeResult:
        """
        Execute the council protocol runtime for one CCP payload.
        """
        transitions: list[CouncilTransition] = []
        state = STATE_S0_ASSEMBLE
        seat_results: dict[str, CouncilSeatResult] = {}
        synthesis: dict[str, Any] = {}
        closure_events: list[dict[str, Any]] = []
        compliance = {}

        try:
            plan = compile_council_run_plan(ccp=ccp, policy=self.policy)
            compliance = dict(plan.compliance_flags)
            self._transition(
                transitions,
                STATE_S0_ASSEMBLE,
                STATE_S0_5_COCHAIR_VALIDATE if plan.cochair_required else STATE_S1_EXECUTE_SEATS,
                "plan_compiled",
                {"mode": plan.mode, "topology": plan.topology},
            )
            state = STATE_S0_5_COCHAIR_VALIDATE if plan.cochair_required else STATE_S1_EXECUTE_SEATS
        except CouncilBlockedError as err:
            self._transition(
                transitions,
                STATE_S0_ASSEMBLE,
                STATE_TERMINAL_BLOCKED,
                "plan_blocked",
                {"category": err.category, "detail": err.detail},
            )
            block_report = {"category": err.category, "detail": err.detail}
            return CouncilRuntimeResult(
                status="blocked",
                run_log={
                    "status": "blocked",
                    "state_transitions": [event.to_dict() for event in transitions],
                },
                decision_payload={"status": "BLOCKED", "reason": err.category, "detail": err.detail},
                block_report=block_report,
            )

        if state == STATE_S0_5_COCHAIR_VALIDATE:
            ok, reason = self._cochair_validate_ccp(ccp, plan)
            if not ok:
                self._transition(
                    transitions,
                    STATE_S0_5_COCHAIR_VALIDATE,
                    STATE_TERMINAL_BLOCKED,
                    "cochair_validation_failed",
                    {"detail": reason},
                )
                return CouncilRuntimeResult(
                    status="blocked",
                    run_log={
                        "execution": plan.to_dict(),
                        "status": "blocked",
                        "state_transitions": [event.to_dict() for event in transitions],
                    },
                    decision_payload={"status": "BLOCKED", "reason": "ccp_validation_failed", "detail": reason},
                    block_report={"category": "ccp_validation_failed", "detail": reason},
                )
            self._transition(
                transitions,
                STATE_S0_5_COCHAIR_VALIDATE,
                STATE_S1_EXECUTE_SEATS,
                reason,
            )
            state = STATE_S1_EXECUTE_SEATS

        waived = self._waived_seats(ccp)
        if state == STATE_S1_EXECUTE_SEATS:
            for seat in plan.required_seats:
                retries_used = 0
                errors: list[str] = []
                warnings: list[str] = []
                normalized_output = None
                raw_output: dict[str, Any] | str = {}
                status = "failed"
                while retries_used <= self.policy.schema_gate_retry_cap:
                    raw_output = self.seat_executor(seat, ccp, plan, retries_used)
                    gate_result = validate_seat_output(raw_output=raw_output, policy=self.policy)
                    self._transition(
                        transitions,
                        STATE_S1_EXECUTE_SEATS,
                        STATE_S1_25_SCHEMA_GATE,
                        "seat_output_received",
                        {"retries": retries_used, "seat": seat},
                    )
                    errors = list(gate_result.errors)
                    warnings = list(gate_result.warnings)
                    if gate_result.valid:
                        status = "complete"
                        normalized_output = gate_result.normalized_output
                        break
                    if retries_used >= self.policy.schema_gate_retry_cap:
                        status = "failed"
                        normalized_output = gate_result.normalized_output
                        break
                    retries_used += 1
                waived_seat = seat in waived
                if status != "complete" and waived_seat:
                    status = "waived"
                seat_results[seat] = CouncilSeatResult(
                    seat=seat,
                    status=status,
                    model=plan.model_assignments.get(seat, "unknown"),
                    raw_output=raw_output,
                    normalized_output=normalized_output,
                    retries_used=retries_used,
                    errors=errors,
                    warnings=warnings,
                    waived=waived_seat,
                )
            self._transition(
                transitions,
                STATE_S1_25_SCHEMA_GATE,
                STATE_S1_5_SEAT_COMPLETION,
                "all_seats_processed",
                {
                    "seats_failed": sum(1 for item in seat_results.values() if item.status == "failed"),
                    "seats_total": len(seat_results),
                    "seats_waived": sum(1 for item in seat_results.values() if item.status == "waived"),
                },
            )
            state = STATE_S1_5_SEAT_COMPLETION

        if state == STATE_S1_5_SEAT_COMPLETION:
            blocking_gaps = [
                seat
                for seat in plan.required_seats
                if seat_results.get(seat) is None or seat_results[seat].status == "failed"
            ]
            if blocking_gaps:
                self._transition(
                    transitions,
                    STATE_S1_5_SEAT_COMPLETION,
                    STATE_TERMINAL_BLOCKED,
                    "required_seats_missing",
                    {"missing_or_failed_seats": blocking_gaps},
                )
                return CouncilRuntimeResult(
                    status="blocked",
                    run_log={
                        "execution": plan.to_dict(),
                        "seat_outputs": {seat: result.to_dict() for seat, result in seat_results.items()},
                        "status": "blocked",
                        "state_transitions": [event.to_dict() for event in transitions],
                    },
                    decision_payload={
                        "status": "BLOCKED",
                        "reason": "required_seats_missing",
                        "seats": blocking_gaps,
                    },
                    block_report={
                        "category": "required_seats_missing",
                        "detail": f"Blocking seat gaps: {', '.join(blocking_gaps)}",
                    },
                )
            self._transition(
                transitions,
                STATE_S1_5_SEAT_COMPLETION,
                STATE_S2_SYNTHESIS,
                "seat_completion_ok",
            )
            state = STATE_S2_SYNTHESIS

        if state == STATE_S2_SYNTHESIS:
            synthesis = self._synthesize(seat_outputs=seat_results, plan=plan, ccp=ccp)
            self._transition(
                transitions,
                STATE_S2_SYNTHESIS,
                STATE_S2_5_COCHAIR_CHALLENGE,
                "synthesis_complete",
                {"verdict": synthesis.get("verdict")},
            )
            state = STATE_S2_5_COCHAIR_CHALLENGE

        if state == STATE_S2_5_COCHAIR_CHALLENGE:
            passed, reason = self._challenge_synthesis(
                synthesis=synthesis, seat_outputs=seat_results, plan=plan
            )
            if not passed:
                # One synthesis rework cycle only.
                synthesis = self._synthesize(seat_outputs=seat_results, plan=plan, ccp=ccp)
                passed_after_rework, reason_after_rework = self._challenge_synthesis(
                    synthesis=synthesis, seat_outputs=seat_results, plan=plan
                )
                if not passed_after_rework:
                    self._transition(
                        transitions,
                        STATE_S2_5_COCHAIR_CHALLENGE,
                        STATE_TERMINAL_BLOCKED,
                        "cochair_challenge_failed",
                        {"detail": reason_after_rework},
                    )
                    return CouncilRuntimeResult(
                        status="blocked",
                        run_log={
                            "execution": plan.to_dict(),
                            "seat_outputs": {seat: result.to_dict() for seat, result in seat_results.items()},
                            "status": "blocked",
                            "state_transitions": [event.to_dict() for event in transitions],
                            "synthesis": synthesis,
                        },
                        decision_payload={
                            "status": "BLOCKED",
                            "reason": "cochair_challenge_failed",
                            "detail": reason_after_rework,
                        },
                        block_report={
                            "category": "cochair_challenge_failed",
                            "detail": reason_after_rework,
                        },
                    )
            next_state = (
                STATE_S3_CLOSURE_GATE
                if plan.closure_gate_required and synthesis.get("verdict") in {"Accept", "Go with Fixes"}
                else STATE_S4_CLOSEOUT
            )
            self._transition(
                transitions,
                STATE_S2_5_COCHAIR_CHALLENGE,
                next_state,
                "cochair_challenge_passed",
                {"detail": reason},
            )
            state = next_state

        if state == STATE_S3_CLOSURE_GATE:
            cycles = 0
            closure_ok = False
            while cycles <= self.policy.closure_retry_cap:
                build_ok, build_details = self.closure_builder(synthesis, plan)
                validate_ok, validate_details = self.closure_validator(synthesis, plan)
                closure_events.append(
                    {
                        "build_details": build_details,
                        "build_ok": build_ok,
                        "cycle": cycles,
                        "validate_details": validate_details,
                        "validate_ok": validate_ok,
                    }
                )
                if build_ok and validate_ok:
                    closure_ok = True
                    break
                cycles += 1
            if not closure_ok:
                waivers = compliance.get("waivers", [])
                if not isinstance(waivers, list):
                    waivers = []
                waivers.append("closure_gate_residual_issues")
                compliance["waivers"] = waivers
            self._transition(
                transitions,
                STATE_S3_CLOSURE_GATE,
                STATE_S4_CLOSEOUT,
                "closure_gate_complete",
                {"closure_ok": closure_ok, "cycles": len(closure_events)},
            )
            state = STATE_S4_CLOSEOUT

        if state == STATE_S4_CLOSEOUT:
            self._transition(
                transitions,
                STATE_S4_CLOSEOUT,
                STATE_TERMINAL_COMPLETE,
                "run_complete",
            )

        seat_outputs_dict = {
            seat: seat_results[seat].to_dict()
            for seat in plan.required_seats
            if seat in seat_results
        }
        transition_dicts = [event.to_dict() for event in transitions]
        model_counter = Counter(plan.model_assignments.values())
        model_plan = {
            "by_model": dict(sorted(model_counter.items())),
            "seat_assignments": [
                {"model": plan.model_assignments.get(seat, "unknown"), "seat": seat}
                for seat in plan.required_seats
            ],
        }

        run_log = {
            "aur_id": plan.aur_id,
            "compliance": {
                "bootstrap_used": bool(compliance.get("bootstrap_used", False)),
                "ceo_override": bool(compliance.get("ceo_override", False)),
                "independence_required": plan.independence_required,
                "independence_satisfied": plan.independence_satisfied,
                "waivers": list(compliance.get("waivers", []))
                if isinstance(compliance.get("waivers"), list)
                else [],
            },
            "execution": {
                "mode": plan.mode,
                "model_plan": model_plan,
                "protocol_version": self.policy.protocol_version,
                "run_id": plan.run_id,
                "timestamp": plan.timestamp,
                "topology": plan.topology,
            },
            "seat_outputs": seat_outputs_dict,
            "state_transitions": transition_dicts,
            "status": "complete",
            "synthesis": synthesis,
        }
        if closure_events:
            run_log["closure_gate"] = closure_events

        decision_payload = {
            "compliance": run_log["compliance"],
            "status": "COMPLETE",
            "verdict": synthesis.get("verdict", "Reject"),
            "fix_plan": synthesis.get("fix_plan", []),
            "ceo_decisions": synthesis.get("ceo_decisions", []),
            "deletion_line": synthesis.get("deletion_line", ""),
            "run_id": plan.run_id,
        }
        return CouncilRuntimeResult(
            status="complete",
            run_log=run_log,
            decision_payload=decision_payload,
            block_report=None,
        )

```

### FILE: `runtime/orchestration/missions/review.py`

```python
"""
Phase 3 Mission Types - Review Mission

Runs council review on a packet (BUILD_PACKET or REVIEW_PACKET).
Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.3 - Mission: review
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from runtime.orchestration.missions.base import (
    BaseMission,
    MissionContext,
    MissionResult,
    MissionType,
    MissionValidationError,
)
from runtime.orchestration.council import CouncilFSM, load_council_policy


# Valid review verdicts per Council Protocol
VALID_VERDICTS = frozenset({"approved", "rejected", "needs_revision", "escalate"})
PROTOCOL_TO_MISSION_VERDICT = {
    "Accept": "approved",
    "Go with Fixes": "needs_revision",
    "Reject": "rejected",
}

# Review seats per architecture
REVIEW_SEATS = ("architect", "alignment", "risk", "governance")


class ReviewMission(BaseMission):
    """
    Review mission: Run council review on a packet.
    
    Inputs:
        - subject_packet (dict): The packet to review
        - review_type (str): Type of review (build_review, output_review)
        
    Outputs:
        - verdict (str): Review verdict
        - council_decision (dict): Full council decision with seat outputs
        
    Steps:
        1. prepare_ccp: Transform packet to Council Context Pack
        2. run_seats: Run each review seat (stubbed for MVP)
        3. synthesize: Synthesize seat outputs into decision
        4. validate_decision: Validate output against schema
    """
    
    @property
    def mission_type(self) -> MissionType:
        return MissionType.REVIEW
    
    def validate_inputs(self, inputs: Dict[str, Any]) -> None:
        """
        Validate review mission inputs.
        
        Required: subject_packet (dict), review_type (string)
        """
        # Check subject_packet
        subject_packet = inputs.get("subject_packet")
        if not subject_packet:
            raise MissionValidationError("subject_packet is required")
        if not isinstance(subject_packet, dict):
            raise MissionValidationError("subject_packet must be a dict")
        
        # Check review_type
        review_type = inputs.get("review_type")
        if not review_type:
            raise MissionValidationError("review_type is required")
        if not isinstance(review_type, str):
            raise MissionValidationError("review_type must be a string")
        
        valid_review_types = ("build_review", "output_review", "governance_review")
        if review_type not in valid_review_types:
            raise MissionValidationError(
                f"review_type must be one of {valid_review_types}, got '{review_type}'"
            )
    
    def run(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> MissionResult:
        executed_steps: List[str] = []
        
        try:
            # Step 1: Validate inputs
            self.validate_inputs(inputs)
            executed_steps.append("validate_inputs")
            use_council_runtime = bool(inputs.get("use_council_runtime", False))
            if use_council_runtime:
                return self._run_council_runtime(context, inputs, executed_steps)
            return self._run_legacy_single_seat(context, inputs, executed_steps)
            
        except MissionValidationError as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Input validation failed: {e}",
            )
        except Exception as e:
            return self._make_result(
                success=False,
                executed_steps=executed_steps,
                error=f"Unexpected error: {e}",
            )

    def _run_legacy_single_seat(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
        executed_steps: List[str],
    ) -> MissionResult:
        """Preserve existing single-seat behavior for compatibility."""
        from runtime.agents.api import call_agent, AgentCall

        call = AgentCall(
            role="reviewer_architect",
            packet={
                "subject_packet": inputs["subject_packet"],
                "review_type": inputs["review_type"]
            },
            model="auto",
        )

        response = call_agent(call, run_id=context.run_id)
        executed_steps.append("architect_review_llm_call")

        reviewer_packet_parsed = response.packet is not None
        if response.packet is not None:
            decision = response.packet
        else:
            fallback_verdict = None
            verdict_match = re.search(
                r'(?m)^verdict:\s*["\']?(\w+)["\']?\s*$',
                response.content,
            )
            if verdict_match:
                candidate = verdict_match.group(1).lower()
                if candidate in VALID_VERDICTS:
                    fallback_verdict = candidate
            decision = {
                "verdict": fallback_verdict or "needs_revision",
                "rationale": response.content,
                "concerns": [],
                "recommendations": [],
            }

        final_verdict = decision.get("verdict", "needs_revision")
        if final_verdict not in VALID_VERDICTS:
            final_verdict = "needs_revision"

        council_decision = {
            "verdict": final_verdict,
            "seat_outputs": {"architect": decision},
            "synthesis": decision.get("rationale", response.content),
        }
        executed_steps.append("synthesize")

        if final_verdict == "escalate":
            return self._make_result(
                success=True,
                outputs={
                    "verdict": final_verdict,
                    "council_decision": council_decision,
                    "reviewer_packet_parsed": reviewer_packet_parsed,
                },
                executed_steps=executed_steps,
                escalation_reason="Architect review requires CEO escalation",
                evidence={
                    "call_id": response.call_id,
                    "model_used": response.model_used,
                    "usage": response.usage,
                },
            )

        return self._make_result(
            success=True,
            outputs={
                "verdict": final_verdict,
                "council_decision": council_decision,
                "reviewer_packet_parsed": reviewer_packet_parsed,
            },
            executed_steps=executed_steps,
            evidence={
                "call_id": response.call_id,
                "model_used": response.model_used,
                "usage": response.usage,
            },
        )

    @staticmethod
    def _default_touches(review_type: str) -> list[str]:
        if review_type == "governance_review":
            return ["governance_protocol"]
        if review_type == "build_review":
            return ["runtime_core"]
        return ["interfaces"]

    def _build_ccp(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        review_type = str(inputs["review_type"])
        subject_packet = inputs["subject_packet"]
        subject_hash = hashlib.sha256(
            json.dumps(subject_packet, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
        header = {
            "aur_id": inputs.get("aur_id", f"{review_type}:{subject_hash[:12]}"),
            "aur_type": inputs.get("aur_type", "code"),
            "blast_radius": inputs.get("blast_radius", "module"),
            "change_class": inputs.get("change_class", "amend"),
            "closure_gate_required": bool(inputs.get("closure_gate_required", review_type == "output_review")),
            "model_plan_v1": inputs.get("model_plan_v1", {}),
            "override": inputs.get("override", {}),
            "reversibility": inputs.get("reversibility", "moderate"),
            "run_id": context.run_id,
            "safety_critical": bool(inputs.get("safety_critical", False)),
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "touches": inputs.get("touches", self._default_touches(review_type)),
            "uncertainty": inputs.get("uncertainty", "medium"),
        }

        sections = inputs.get("sections")
        if not isinstance(sections, dict):
            sections = {
                "objective": f"Run council review for {review_type}.",
                "scope": {
                    "review_type": review_type,
                    "subject_fields": sorted(subject_packet.keys()),
                },
                "constraints": inputs.get(
                    "constraints",
                    ["Fail closed on schema and protocol violations."],
                ),
                "artifacts": inputs.get(
                    "artifacts",
                    [{"kind": "subject_packet", "sha256": subject_hash}],
                ),
            }

        ccp = {
            "header": header,
            "review_type": review_type,
            "sections": sections,
            "subject_packet": subject_packet,
        }

        bootstrap = inputs.get("bootstrap")
        if isinstance(bootstrap, dict):
            ccp["header"]["bootstrap"] = bootstrap
        return ccp

    def _run_council_runtime(
        self,
        context: MissionContext,
        inputs: Dict[str, Any],
        executed_steps: List[str],
    ) -> MissionResult:
        ccp = self._build_ccp(context, inputs)
        executed_steps.append("prepare_ccp")

        policy_path = inputs.get("council_policy_path")
        policy = load_council_policy(policy_path)
        fsm = CouncilFSM(policy=policy)
        runtime_result = fsm.run(ccp)
        executed_steps.append("execute_council_fsm")

        if runtime_result.status == "blocked":
            detail = "blocked"
            if runtime_result.block_report:
                detail = runtime_result.block_report.get("detail", detail)
            council_decision = {
                "protocol_status": "BLOCKED",
                "run_log": runtime_result.run_log,
                "block_report": runtime_result.block_report,
                "synthesis": {"verdict": "Reject"},
                "verdict": "escalate",
            }
            return self._make_result(
                success=True,
                outputs={
                    "verdict": "escalate",
                    "council_decision": council_decision,
                    "reviewer_packet_parsed": True,
                },
                executed_steps=executed_steps,
                escalation_reason=f"Council runtime blocked: {detail}",
                evidence={
                    "council_runtime_status": runtime_result.status,
                    "usage": {"total": 0},
                },
            )

        protocol_verdict = str(runtime_result.decision_payload.get("verdict", "Reject"))
        mission_verdict = PROTOCOL_TO_MISSION_VERDICT.get(protocol_verdict, "needs_revision")
        council_decision = {
            "protocol_status": runtime_result.decision_payload.get("status", "COMPLETE"),
            "protocol_verdict": protocol_verdict,
            "run_log": runtime_result.run_log,
            "synthesis": runtime_result.run_log.get("synthesis", {}),
            "verdict": mission_verdict,
        }

        escalation_reason = None
        if mission_verdict == "escalate":
            escalation_reason = "Council runtime requested escalation."

        return self._make_result(
            success=True,
            outputs={
                "verdict": mission_verdict,
                "council_decision": council_decision,
                "reviewer_packet_parsed": True,
            },
            executed_steps=executed_steps,
            escalation_reason=escalation_reason,
            evidence={
                "council_runtime_status": runtime_result.status,
                "run_id": runtime_result.decision_payload.get("run_id"),
                "usage": {"total": 0},
            },
        )

```

### FILE: `runtime/tests/orchestration/council/test_compiler.py`

```python
from __future__ import annotations

import pytest

from runtime.orchestration.council.compiler import compile_council_run_plan
from runtime.orchestration.council.models import CouncilBlockedError
from runtime.orchestration.council.policy import load_council_policy


def _base_sections() -> dict:
    return {
        "objective": "Review candidate change.",
        "scope": {"surface": "runtime"},
        "constraints": ["deterministic outputs"],
        "artifacts": [{"id": "artifact-1"}],
    }


def test_compile_plan_m0_fast_success():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-1",
            "aur_type": "doc",
            "change_class": "hygiene",
            "blast_radius": "local",
            "reversibility": "easy",
            "uncertainty": "low",
            "touches": ["docs_only"],
            "safety_critical": False,
        },
        "sections": _base_sections(),
    }
    plan = compile_council_run_plan(ccp=ccp, policy=policy)
    assert plan.mode == "M0_FAST"
    assert plan.topology == "MONO"
    assert plan.required_seats == ("L1UnifiedReviewer",)
    assert plan.cochair_required is False


def test_compile_plan_m2_triggered_by_runtime_core():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-2",
            "aur_type": "code",
            "change_class": "amend",
            "blast_radius": "module",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["runtime_core"],
            "safety_critical": False,
        },
        "sections": _base_sections(),
    }
    plan = compile_council_run_plan(ccp=ccp, policy=policy)
    assert plan.mode == "M2_FULL"
    assert plan.topology == "HYBRID"
    assert "Chair" in plan.required_seats
    assert "RiskAdversarial" in plan.required_seats


def test_compile_plan_blocks_on_unknown_enum():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-3",
            "aur_type": "code",
            "change_class": "hygiene",
            "blast_radius": "local",
            "reversibility": "easy",
            "uncertainty": "low",
            "touches": ["nonexistent_surface"],
            "safety_critical": False,
        },
        "sections": _base_sections(),
    }
    with pytest.raises(CouncilBlockedError) as exc:
        compile_council_run_plan(ccp=ccp, policy=policy)
    assert exc.value.category == "unknown_enum_value"


def test_compile_plan_must_independence_blocks_without_override():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-4",
            "aur_type": "code",
            "change_class": "amend",
            "blast_radius": "system",
            "reversibility": "hard",
            "uncertainty": "high",
            "touches": ["runtime_core"],
            "safety_critical": True,
            "model_plan_v1": {
                "primary": "claude-sonnet-4-5",
                "independent": "claude-haiku-4-5",
            },
        },
        "sections": _base_sections(),
    }
    with pytest.raises(CouncilBlockedError) as exc:
        compile_council_run_plan(ccp=ccp, policy=policy)
    assert exc.value.category == "independence_unsatisfied"


def test_compile_plan_must_independence_with_emergency_override():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-5",
            "aur_type": "code",
            "change_class": "amend",
            "blast_radius": "system",
            "reversibility": "hard",
            "uncertainty": "high",
            "touches": ["runtime_core"],
            "safety_critical": True,
            "model_plan_v1": {
                "primary": "claude-sonnet-4-5",
                "independent": "claude-haiku-4-5",
            },
            "override": {"emergency_ceo": True, "rationale": "break-glass"},
        },
        "sections": _base_sections(),
    }
    plan = compile_council_run_plan(ccp=ccp, policy=policy)
    assert plan.mode == "M2_FULL"
    assert plan.independence_required == "must"
    assert plan.compliance_flags["ceo_override"] is True
    assert plan.compliance_flags["compliance_status"] == "non-compliant-ceo-authorized"


def test_compile_plan_bootstrap_limit_blocks():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-6",
            "aur_type": "doc",
            "change_class": "hygiene",
            "blast_radius": "local",
            "reversibility": "easy",
            "uncertainty": "low",
            "touches": ["docs_only"],
            "safety_critical": False,
            "bootstrap": {"used": True, "consecutive_count": 3},
        },
        "sections": _base_sections(),
    }
    with pytest.raises(CouncilBlockedError) as exc:
        compile_council_run_plan(ccp=ccp, policy=policy)
    assert exc.value.category == "bootstrap_limit_exceeded"

```

### FILE: `runtime/tests/orchestration/council/test_schema_gate.py`

```python
from __future__ import annotations

from runtime.orchestration.council.policy import load_council_policy
from runtime.orchestration.council.schema_gate import validate_seat_output


def _valid_output() -> dict:
    return {
        "verdict": "Accept",
        "key_findings": ["- Deterministic behavior preserved"],
        "risks": ["- No major risk identified"],
        "fixes": ["- Add one integration test"],
        "confidence": "high",
        "assumptions": ["environment has git"],
        "operator_view": "Safe and simple.",
        "complexity_budget": {
            "net_human_steps": 1,
            "new_surfaces_introduced": 0,
            "surfaces_removed": 0,
            "mechanized": "yes",
            "trade_statement": "n/a",
        },
    }


def test_schema_gate_accepts_valid_output_and_labels_assumptions():
    policy = load_council_policy()
    result = validate_seat_output(_valid_output(), policy)
    assert result.valid is True
    assert result.rejected is False
    assert result.normalized_output is not None
    assert result.normalized_output["key_findings"][0].endswith("[ASSUMPTION]")
    assert any("ASSUMPTION" in warning for warning in result.warnings)


def test_schema_gate_rejects_missing_section():
    policy = load_council_policy()
    payload = _valid_output()
    payload.pop("operator_view")
    result = validate_seat_output(payload, policy)
    assert result.valid is False
    assert result.rejected is True
    assert "Missing required section: operator_view" in result.errors


def test_schema_gate_rejects_invalid_verdict():
    policy = load_council_policy()
    payload = _valid_output()
    payload["verdict"] = "PASS"
    result = validate_seat_output(payload, policy)
    assert result.valid is False
    assert result.rejected is True
    assert any("Invalid verdict" in msg for msg in result.errors)


def test_schema_gate_flags_complexity_budget_without_trade_statement():
    policy = load_council_policy()
    payload = _valid_output()
    payload["complexity_budget"]["mechanized"] = "no"
    payload["complexity_budget"]["trade_statement"] = "none"
    result = validate_seat_output(payload, policy)
    assert result.valid is True
    assert any("complexity_budget has net-positive" in msg for msg in result.warnings)

```

### FILE: `runtime/tests/orchestration/council/test_fsm.py`

```python
from __future__ import annotations

from runtime.orchestration.council.fsm import CouncilFSM
from runtime.orchestration.council.policy import load_council_policy


def _valid_seat_output(verify_ledger: bool = False) -> dict:
    return {
        "verdict": "Accept",
        "key_findings": ["- Finding with no citation"],
        "risks": ["- Minimal"],
        "fixes": ["- Add regression test"],
        "confidence": "high",
        "assumptions": ["test fixture controls runtime"],
        "operator_view": "Looks safe.",
        "complexity_budget": {
            "net_human_steps": 0,
            "new_surfaces_introduced": 0,
            "surfaces_removed": 0,
            "mechanized": "yes",
            "trade_statement": "none",
        },
        "contradiction_ledger_verified": verify_ledger,
    }


def _m1_ccp() -> dict:
    return {
        "header": {
            "aur_id": "AUR-FSM-1",
            "aur_type": "code",
            "change_class": "amend",
            "blast_radius": "module",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["tests"],
            "safety_critical": False,
        },
        "sections": {
            "objective": "Run M1 council review.",
            "scope": {"surface": "runtime"},
            "constraints": ["deterministic behavior"],
            "artifacts": [{"id": "artifact-x"}],
        },
    }


def test_fsm_m1_happy_path_complete():
    policy = load_council_policy()

    def seat_executor(seat, ccp, plan, retry_count):
        return _valid_seat_output(verify_ledger=(seat == "CoChair"))

    fsm = CouncilFSM(policy=policy, seat_executor=seat_executor)
    result = fsm.run(_m1_ccp())

    assert result.status == "complete"
    assert result.decision_payload["status"] == "COMPLETE"
    assert result.decision_payload["verdict"] == "Accept"
    assert result.run_log["execution"]["mode"] == "M1_STANDARD"
    assert result.run_log["state_transitions"][-1]["to_state"] == "TERMINAL_COMPLETE"


def test_fsm_blocks_when_cochair_does_not_verify_contradiction_ledger():
    policy = load_council_policy()

    def seat_executor(seat, ccp, plan, retry_count):
        # CoChair intentionally omits contradiction ledger verification.
        return _valid_seat_output(verify_ledger=False)

    fsm = CouncilFSM(policy=policy, seat_executor=seat_executor)
    result = fsm.run(_m1_ccp())

    assert result.status == "blocked"
    assert result.decision_payload["reason"] == "cochair_challenge_failed"


def test_fsm_retries_schema_rejects_and_recovers():
    policy = load_council_policy()
    calls = {"Chair": 0, "CoChair": 0}

    def seat_executor(seat, ccp, plan, retry_count):
        calls[seat] += 1
        if seat == "Chair" and retry_count < 2:
            return {"verdict": "Accept"}  # Missing required sections -> reject.
        return _valid_seat_output(verify_ledger=(seat == "CoChair"))

    fsm = CouncilFSM(policy=policy, seat_executor=seat_executor)
    result = fsm.run(_m1_ccp())

    assert result.status == "complete"
    chair_out = result.run_log["seat_outputs"]["Chair"]
    assert chair_out["retries_used"] == 2
    assert calls["Chair"] == 3

```

### FILE: `runtime/tests/orchestration/missions/test_review_council_runtime.py`

```python
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from runtime.orchestration.council.models import CouncilRuntimeResult
from runtime.orchestration.missions.base import MissionContext
from runtime.orchestration.missions.review import ReviewMission


def _context(tmp_path: Path) -> MissionContext:
    return MissionContext(
        repo_root=tmp_path,
        baseline_commit="abc123",
        run_id="review-run-1",
        operation_executor=None,
    )


def _inputs() -> dict:
    return {
        "subject_packet": {"goal": "test"},
        "review_type": "build_review",
        "use_council_runtime": True,
    }


@patch("runtime.orchestration.missions.review.load_council_policy")
@patch("runtime.orchestration.missions.review.CouncilFSM")
def test_review_mission_opt_in_maps_protocol_verdict(MockFSM, mock_load_policy, tmp_path: Path):
    mock_policy = object()
    mock_load_policy.return_value = mock_policy

    runtime_result = CouncilRuntimeResult(
        status="complete",
        run_log={"synthesis": {"verdict": "Accept"}},
        decision_payload={"status": "COMPLETE", "verdict": "Accept", "run_id": "council-1"},
        block_report=None,
    )
    MockFSM.return_value.run.return_value = runtime_result

    mission = ReviewMission()
    result = mission.run(_context(tmp_path), _inputs())

    assert result.success is True
    assert result.outputs["verdict"] == "approved"
    assert "prepare_ccp" in result.executed_steps
    assert "execute_council_fsm" in result.executed_steps
    assert result.evidence["usage"]["total"] == 0


@patch("runtime.orchestration.missions.review.load_council_policy")
@patch("runtime.orchestration.missions.review.CouncilFSM")
def test_review_mission_opt_in_handles_blocked_runtime(MockFSM, mock_load_policy, tmp_path: Path):
    mock_policy = object()
    mock_load_policy.return_value = mock_policy

    runtime_result = CouncilRuntimeResult(
        status="blocked",
        run_log={"status": "blocked"},
        decision_payload={"status": "BLOCKED", "reason": "required_seats_missing"},
        block_report={"category": "required_seats_missing", "detail": "Chair failed"},
    )
    MockFSM.return_value.run.return_value = runtime_result

    mission = ReviewMission()
    result = mission.run(_context(tmp_path), _inputs())

    assert result.success is True
    assert result.outputs["verdict"] == "escalate"
    assert "Council runtime blocked" in (result.escalation_reason or "")

```
