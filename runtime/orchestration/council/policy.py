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
    def schema_gate_require_explicit_claim_grounding(self) -> bool:
        gate = self.raw.get("schema_gate", {})
        return bool(gate.get("require_explicit_claim_grounding", True))

    @property
    def schema_gate_max_assumption_ratio(self) -> float:
        gate = self.raw.get("schema_gate", {})
        raw_value = gate.get("max_assumption_ratio", 0.5)
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            return 0.5
        if value < 0.0:
            return 0.0
        if value > 1.0:
            return 1.0
        return value

    @property
    def schema_gate_accept_requires_ref_balance(self) -> bool:
        gate = self.raw.get("schema_gate", {})
        return bool(gate.get("accept_requires_ref_balance", True))

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
        triggers = self.raw.get("independence", {}).get("must_conditions", {}).get("triggers", [])
        return tuple(str(s) for s in triggers)

    def independence_should_triggers(self) -> tuple[str, ...]:
        triggers = self.raw.get("independence", {}).get("should_conditions", {}).get("triggers", [])
        return tuple(str(s) for s in triggers)

    @property
    def bootstrap_policy(self) -> Mapping[str, Any]:
        return self.raw.get("bootstrap", {})

    # v2.2.1 tier accessors

    @property
    def tier_default(self) -> str:
        return str(self.raw.get("tiers", {}).get("default", "T1"))

    def tier_t3_triggers(self) -> tuple[str, ...]:
        entries = self.raw.get("tiers", {}).get("T3_triggers", [])
        return tuple(str(s) for s in entries)

    def tier_t2_triggers(self) -> tuple[str, ...]:
        entries = self.raw.get("tiers", {}).get("T2_triggers", [])
        return tuple(str(s) for s in entries)

    def tier_t0_conditions(self) -> tuple[str, ...]:
        entries = self.raw.get("tiers", {}).get("T0_conditions", [])
        return tuple(str(s) for s in entries)

    # v2.2.1 lens accessors

    def lenses_for_tier(self, tier: str) -> tuple[str, ...]:
        """Return catalog of all available lenses for the tier."""
        catalog = self.raw.get("lenses", {}).get("catalog", [])
        return tuple(str(s) for s in catalog)

    def mandatory_lenses_for_tier(self, tier: str) -> tuple[str, ...]:
        config = self.raw.get("lenses", {}).get("tier_config", {}).get(tier, {})
        return tuple(str(s) for s in config.get("mandatory", []))

    def waivable_lenses_for_tier(self, tier: str) -> tuple[str, ...]:
        config = self.raw.get("lenses", {}).get("tier_config", {}).get(tier, {})
        return tuple(str(s) for s in config.get("waivable", []))

    def min_lenses_for_tier(self, tier: str) -> int:
        config = self.raw.get("lenses", {}).get("tier_config", {}).get(tier, {})
        return int(config.get("min_lenses", 0))

    def max_lenses_for_tier(self, tier: str) -> int:
        config = self.raw.get("lenses", {}).get("tier_config", {}).get(tier, {})
        return int(config.get("max_lenses", 0))

    @property
    def lens_catalog(self) -> tuple[str, ...]:
        catalog = self.raw.get("lenses", {}).get("catalog", [])
        return tuple(str(s) for s in catalog)

    @property
    def padding_priority(self) -> tuple[str, ...]:
        priority = self.raw.get("lenses", {}).get("padding_priority", [])
        return tuple(str(s) for s in priority)


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
