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
