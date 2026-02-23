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


# ---------------------------------------------------------------------------
# v2.2.1 Validators
# ---------------------------------------------------------------------------

_VALID_CONFIDENCES = {"low", "medium", "high"}
_VALID_EVIDENCE_STATUSES = {"evidenced", "speculative", "mixed"}
_VALID_VERDICTS_V2 = {"Accept", "Revise", "Reject"}
_TIERS_WITH_LEDGER = {"T2", "T3"}


def _make_result(errors: list[str], warnings: list[str], output: dict[str, Any]) -> SchemaGateResult:
    rejected = len(errors) > 0
    return SchemaGateResult(
        valid=not rejected,
        rejected=rejected,
        normalized_output=output,
        errors=errors,
        warnings=warnings,
    )


def _make_blocked(errors: list[str]) -> SchemaGateResult:
    return SchemaGateResult(
        valid=False,
        rejected=True,
        normalized_output=None,
        errors=errors,
        warnings=[],
    )


def validate_lens_output(
    raw: dict[str, Any] | str,
    policy: "CouncilPolicy",
    run_type: str,
    tier: str,
) -> SchemaGateResult:
    """
    Validate a lens output packet for the given run_type and tier.

    Review lenses: claims[] required (each claim needs claim_id).
    Advisory lenses: recommendations[] + evidence_status required.
    """
    output, parse_errors = _normalize_packet(raw)
    if output is None:
        return _make_blocked(parse_errors)

    errors: list[str] = list(parse_errors)
    warnings: list[str] = []

    # Common required fields
    for field_name in ("run_type", "lens_name", "confidence", "notes", "operator_view"):
        if field_name not in output or _is_empty(output.get(field_name)):
            errors.append(f"Missing required field: {field_name}")

    confidence = str(output.get("confidence", "")).lower()
    if confidence and confidence not in _VALID_CONFIDENCES:
        warnings.append(f"Unexpected confidence value: '{confidence}'")

    if run_type == "review":
        # claims required, each must have claim_id
        claims = output.get("claims")
        if claims is None or not isinstance(claims, list):
            errors.append("Missing required field: claims")
        else:
            for idx, claim in enumerate(claims):
                if not isinstance(claim, Mapping):
                    errors.append(f"claims[{idx}] must be an object")
                    continue
                if "claim_id" not in claim:
                    errors.append(f"claims[{idx}] missing claim_id")
        # verdict_recommendation must be valid if present
        verdict_rec = output.get("verdict_recommendation")
        if verdict_rec is not None and verdict_rec not in _VALID_VERDICTS_V2:
            errors.append(
                f"Invalid verdict_recommendation '{verdict_rec}'. "
                f"Allowed: {sorted(_VALID_VERDICTS_V2)}"
            )
    elif run_type == "advisory":
        # evidence_status required
        if "evidence_status" not in output or _is_empty(output.get("evidence_status")):
            errors.append("Missing required field: evidence_status")
        else:
            evs = str(output.get("evidence_status", "")).lower()
            if evs not in _VALID_EVIDENCE_STATUSES:
                errors.append(
                    f"Invalid evidence_status '{evs}'. "
                    f"Allowed: {sorted(_VALID_EVIDENCE_STATUSES)}"
                )
        # recommendations required (non-empty list)
        recs = output.get("recommendations")
        if not isinstance(recs, list) or len(recs) == 0:
            errors.append("Advisory lens must include non-empty recommendations[]")
    else:
        errors.append(f"Unknown run_type '{run_type}'")

    return _make_result(errors, warnings, output)


def _validate_ledger_entries(ledger: list[Any], errors: list[str]) -> None:
    for idx, entry in enumerate(ledger):
        if not isinstance(entry, dict):
            errors.append(f"contradiction_ledger[{idx}] must be an object")
            continue
        if "topic" not in entry:
            errors.append(f"contradiction_ledger[{idx}] missing topic")
        positions = entry.get("positions")
        if not isinstance(positions, dict) or len(positions) < 2:
            errors.append(
                f"contradiction_ledger[{idx}] positions must be a dict with >=2 lenses"
            )
        if "resolution" not in entry:
            errors.append(f"contradiction_ledger[{idx}] missing resolution")
        if "status" not in entry:
            errors.append(f"contradiction_ledger[{idx}] missing status")


def validate_synthesis_output(
    raw: dict[str, Any] | str,
    policy: "CouncilPolicy",
    tier: str,
    run_type: str,
) -> SchemaGateResult:
    """
    Validate a Chair synthesis output.

    All tiers: run_type, tier, verdict, fix_plan, complexity_budget, operator_view,
               coverage_degraded, waived_lenses.
    Review: evidence_summary required.
    T2/T3: contradiction_ledger required.
    """
    output, parse_errors = _normalize_packet(raw)
    if output is None:
        return _make_blocked(parse_errors)

    errors: list[str] = list(parse_errors)
    warnings: list[str] = []

    for field_name in ("run_type", "tier", "verdict", "fix_plan", "complexity_budget",
                       "operator_view", "coverage_degraded", "waived_lenses"):
        if field_name not in output:
            errors.append(f"Missing required field: {field_name}")

    verdict = output.get("verdict")
    if verdict is not None and verdict not in _VALID_VERDICTS_V2:
        errors.append(
            f"Invalid verdict '{verdict}'. Allowed: {sorted(_VALID_VERDICTS_V2)}"
        )

    if not isinstance(output.get("complexity_budget"), dict):
        errors.append("complexity_budget must be an object")

    if run_type == "review":
        if "evidence_summary" not in output:
            errors.append("Review synthesis missing evidence_summary")

    if tier in _TIERS_WITH_LEDGER:
        ledger = output.get("contradiction_ledger")
        if not isinstance(ledger, list):
            errors.append(
                f"Tier {tier} synthesis requires contradiction_ledger (list)"
            )
        else:
            _validate_ledger_entries(ledger, errors)

    return _make_result(errors, warnings, output)


def validate_challenger_output(
    raw: dict[str, Any] | str,
    policy: "CouncilPolicy",
    tier: str,
) -> SchemaGateResult:
    """
    Validate a Challenger output.

    All tiers: weakest_claim, stress_test, material_issue, issue_class,
               severity, required_action, notes.
    T2/T3: ledger_completeness_ok, missing_disagreements required.
    """
    output, parse_errors = _normalize_packet(raw)
    if output is None:
        return _make_blocked(parse_errors)

    errors: list[str] = list(parse_errors)
    warnings: list[str] = []

    for field_name in ("weakest_claim", "stress_test", "material_issue",
                       "issue_class", "severity", "required_action", "notes"):
        if field_name not in output:
            errors.append(f"Missing required field: {field_name}")

    if not isinstance(output.get("material_issue"), bool):
        errors.append("material_issue must be a boolean")

    if tier in _TIERS_WITH_LEDGER:
        if "ledger_completeness_ok" not in output:
            errors.append(f"Tier {tier} challenger requires ledger_completeness_ok")
        if "missing_disagreements" not in output:
            errors.append(f"Tier {tier} challenger requires missing_disagreements")

    return _make_result(errors, warnings, output)
