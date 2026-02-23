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
