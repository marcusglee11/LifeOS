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

_LEGACY_VERDICT_ALIASES = {
    "Go with Fixes": "Revise",
}

_ASSUMPTION_TAG_RE = re.compile(r"\[ASSUMPTION[^\]]*\]", re.IGNORECASE)
_CWE_TOKEN_RE = re.compile(r"\bCWE-\d+\b", re.IGNORECASE)


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


def _text_has_citation(text: str) -> bool:
    return "REF:" in text or bool(_CWE_TOKEN_RE.search(text))


def _text_has_assumption_tag(text: str) -> bool:
    return bool(_ASSUMPTION_TAG_RE.search(text))


def _claim_text_fields(item: Mapping[str, Any]) -> list[str]:
    fields = ("claim", "text", "statement", "rationale", "summary")
    values: list[str] = []
    for field_name in fields:
        value = item.get(field_name)
        if isinstance(value, str) and value.strip():
            values.append(value)
    return values


def _claim_has_citation(item: Any) -> bool:
    if isinstance(item, str):
        return _text_has_citation(item)
    if not isinstance(item, Mapping):
        return False
    ref = item.get("ref")
    if isinstance(ref, str) and _text_has_citation(ref):
        return True
    for key in ("refs", "evidence_refs"):
        refs = item.get(key)
        if not isinstance(refs, list):
            continue
        for ref_item in refs:
            if isinstance(ref_item, str) and _text_has_citation(ref_item):
                return True
    return any(_text_has_citation(value) for value in _claim_text_fields(item))


def _claim_is_assumption(item: Any) -> bool:
    if isinstance(item, str):
        return _text_has_assumption_tag(item)
    if not isinstance(item, Mapping):
        return False
    if bool(item.get("assumption", False)):
        return True
    for key in ("refs", "evidence_refs"):
        refs = item.get(key)
        if not isinstance(refs, list):
            continue
        for ref_item in refs:
            if isinstance(ref_item, str) and "ASSUMPTION:" in ref_item.upper():
                return True
    return any(_text_has_assumption_tag(value) for value in _claim_text_fields(item))


def _assumption_has_resolution_hint(item: Any) -> bool:
    if isinstance(item, Mapping):
        for field_name in ("evidence_needed", "resolve_with", "resolution_evidence"):
            value = item.get(field_name)
            if isinstance(value, str) and value.strip():
                return True
    text = str(item).lower()
    return "evidence" in text or "resolve" in text


def _validate_claim_grounding(
    output: dict[str, Any],
    errors: list[str],
    warnings: list[str],
) -> tuple[int, int, int]:
    total_claims = 0
    cited_claims = 0
    assumption_only_claims = 0

    for section in ("key_findings", "risks", "fixes"):
        claims = output.get(section)
        if not isinstance(claims, list):
            errors.append(f"{section} must be a list of claims.")
            continue
        for idx, item in enumerate(claims):
            if not isinstance(item, (str, Mapping)):
                errors.append(f"{section}[{idx}] must be a string or object claim.")
                continue

            has_citation = _claim_has_citation(item)
            is_assumption = _claim_is_assumption(item)
            if not has_citation and not is_assumption:
                errors.append(
                    f"{section}[{idx}] missing grounding token: include REF: citation "
                    "or [ASSUMPTION] label."
                )
                continue

            total_claims += 1
            if has_citation:
                cited_claims += 1
            if is_assumption and not has_citation:
                assumption_only_claims += 1
                if not _assumption_has_resolution_hint(item):
                    warnings.append(
                        f"{section}[{idx}] assumption should state resolving evidence."
                    )

    return total_claims, cited_claims, assumption_only_claims


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


def _normalize_legacy_verdict(
    output: dict[str, Any],
    field_name: str,
    allowed_verdicts: set[str],
    warnings: list[str],
) -> str | None:
    value = output.get(field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    mapped = _LEGACY_VERDICT_ALIASES.get(value)
    if mapped and mapped in allowed_verdicts:
        output[field_name] = mapped
        warnings.append(
            f"Normalized legacy verdict alias '{value}' to '{mapped}' for {field_name}."
        )
        return mapped
    return value


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

    allowed_verdicts = set(policy.enums.get("verdict", []))
    verdict = _normalize_legacy_verdict(
        normalized,
        field_name="verdict",
        allowed_verdicts=allowed_verdicts,
        warnings=warnings,
    )
    if verdict not in allowed_verdicts:
        errors.append(
            f"Invalid verdict '{verdict}'. Allowed values: {sorted(allowed_verdicts)}"
        )

    if policy.schema_gate_require_explicit_claim_grounding:
        (
            total_claims,
            cited_claims,
            assumption_only_claims,
        ) = _validate_claim_grounding(normalized, errors, warnings)

        if total_claims > 0:
            max_assumption_ratio = policy.schema_gate_max_assumption_ratio
            assumption_ratio = assumption_only_claims / total_claims
            if assumption_ratio > max_assumption_ratio:
                errors.append(
                    "Assumption-heavy output rejected: "
                    f"{assumption_only_claims}/{total_claims} assumption-only claims "
                    f"(ratio={assumption_ratio:.2f}) exceeds max={max_assumption_ratio:.2f}."
                )

        if verdict == "Accept" and policy.schema_gate_accept_requires_ref_balance:
            if cited_claims == 0:
                errors.append(
                    "Accept verdict requires at least one REF/CWE-cited material claim."
                )
            if assumption_only_claims > 0 and assumption_only_claims >= cited_claims:
                errors.append(
                    "Accept verdict requires cited claims to outnumber assumption-only claims."
                )

        if assumption_only_claims > 0:
            assumptions = normalized.get("assumptions")
            if not isinstance(assumptions, list) or not any(
                isinstance(item, str) and item.strip() for item in assumptions
            ):
                errors.append(
                    "assumptions must enumerate evidence gaps when assumption-backed claims are used."
                )

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
        verdict_rec = _normalize_legacy_verdict(
            output,
            field_name="verdict_recommendation",
            allowed_verdicts=_VALID_VERDICTS_V2,
            warnings=warnings,
        )
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

    verdict = _normalize_legacy_verdict(
        output,
        field_name="verdict",
        allowed_verdicts=_VALID_VERDICTS_V2,
        warnings=warnings,
    )
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
