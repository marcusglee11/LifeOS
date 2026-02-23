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
        primary, _, _ = resolve_model_auto("council_reviewer", config=config)
        independent, _, _ = resolve_model_auto("council_reviewer_security", config=config)
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
        seat_role = seat_role_map.get(seat, "council_reviewer")
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
        if seat in {"RiskAdversarial", "Governance"} and independence_required in {"must", "should"}:
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


# ---------------------------------------------------------------------------
# v2.2.1 functions: tier routing, lens selection, run-plan compilation
# ---------------------------------------------------------------------------


def _resolve_default_models_v2() -> tuple[str, str]:
    """Resolve default primary and independent models for v2, ensuring different families."""
    primary_default = "claude-sonnet-4-5"
    independent_default = "opencode/glm-5-free"
    try:
        config = load_model_config()
        primary, _, _ = resolve_model_auto("council_reviewer", config=config)
        primary_default = primary
    except Exception:
        pass
    return primary_default, independent_default


def _resolve_tier(metadata: Mapping[str, Any], policy: CouncilPolicy) -> str:
    """Resolve T0/T1/T2/T3 tier from CCP metadata and policy."""
    # Check override first
    override = metadata.get("override", {})
    if isinstance(override, Mapping) and override.get("tier"):
        return str(override.get("tier"))
    # T3 checked first (highest rigor wins)
    if any(evaluate_expression(expr, metadata) for expr in policy.tier_t3_triggers()):
        return "T3"
    # Then T2
    if any(evaluate_expression(expr, metadata) for expr in policy.tier_t2_triggers()):
        return "T2"
    # Then T0 (all conditions must pass)
    if policy.tier_t0_conditions() and all(
        evaluate_expression(expr, metadata) for expr in policy.tier_t0_conditions()
    ):
        return "T0"
    # Default: T1
    return policy.tier_default


def _resolve_run_type(metadata: Mapping[str, Any]) -> str:
    """Extract run_type from CCP header, default 'review'."""
    run_type = metadata.get("run_type", "review")
    return str(run_type) if run_type in {"review", "advisory"} else "review"


def _select_lenses(tier: str, policy: CouncilPolicy) -> dict[str, Any]:
    """
    Select lenses deterministically for the tier.
    Returns dict with keys: required_lenses, mandatory_lenses, waivable_lenses, padded_lenses

    Selection is constrained to lenses present in policy.lens_catalog, enabling
    exhaustion detection when the catalog is too small to satisfy tier requirements.
    """
    min_count = policy.min_lenses_for_tier(tier)
    max_count = policy.max_lenses_for_tier(tier)

    if max_count == 0:
        # T0 or T1: no lenses
        return {
            "required_lenses": tuple(),
            "mandatory_lenses": tuple(),
            "waivable_lenses": tuple(),
            "padded_lenses": tuple(),
        }

    # Filter mandatory/waivable through current catalog (enables mock-based exhaustion testing)
    catalog_set = set(policy.lens_catalog)
    mandatory = [l for l in policy.mandatory_lenses_for_tier(tier) if l in catalog_set]
    waivable = [l for l in policy.waivable_lenses_for_tier(tier) if l in catalog_set]

    # Start with mandatory lenses
    selected = list(mandatory)

    # Add waivable lenses up to max_count (deterministic order)
    for lens in waivable:
        if len(selected) >= max_count:
            break
        if lens not in selected:
            selected.append(lens)

    # Pad using priority list if still below min_count (only lenses in catalog)
    padded: list[str] = []
    if len(selected) < min_count:
        for lens in policy.padding_priority:
            if len(selected) >= min_count:
                break
            if lens not in selected and lens in catalog_set:
                selected.append(lens)
                padded.append(lens)

    # Catalog exhaustion check
    if len(selected) < min_count:
        raise CouncilBlockedError(
            "POLICY_LENS_CATALOG_INSUFFICIENT",
            f"Cannot reach required {min_count} lenses for {tier}. "
            f"Catalog has {len(policy.lens_catalog)} lenses, selected {len(selected)}.",
        )

    required = tuple(sorted(selected))
    mandatory_base = set(policy.mandatory_lenses_for_tier(tier))
    mandatory_t = tuple(sorted(m for m in selected if m in mandatory_base))
    waivable_t = tuple(sorted(w for w in selected if w not in mandatory_base))

    return {
        "required_lenses": required,
        "mandatory_lenses": mandatory_t,
        "waivable_lenses": waivable_t,
        "padded_lenses": tuple(sorted(padded)),
    }


def _check_t0_strictness(
    metadata: Mapping[str, Any], tier: str, policy: CouncilPolicy
) -> None:
    """T0 strictness: must have reversibility=easy."""
    if tier != "T0":
        return
    reversibility = metadata.get("reversibility", "")
    if reversibility != "easy":
        raise CouncilBlockedError(
            "t0_strictness_violation",
            f"T0 requires reversibility=easy, got '{reversibility}'.",
        )


def _resolve_independence_required_v2(
    metadata: Mapping[str, Any], tier: str, policy: CouncilPolicy
) -> str:
    """Resolve independence requirement using tier-based semantics (v2.2.1)."""
    must_triggered = any(
        evaluate_expression(expr, metadata) for expr in policy.independence_must_triggers()
    )
    should_triggered = any(
        evaluate_expression(expr, metadata) for expr in policy.independence_should_triggers()
    )
    # MUST: if triggered AND high-rigor tier
    if must_triggered and tier in {"T2", "T3"}:
        return "must"
    if must_triggered:
        return "must"
    if should_triggered:
        return "should"
    return "none"


def _resolve_topology_v2(
    metadata: Mapping[str, Any], tier: str, independence_required: str
) -> str:
    """Resolve topology for v2.2.1 tier-based routing."""
    override = metadata.get("override", {})
    if isinstance(override, Mapping) and override.get("topology"):
        return str(override.get("topology"))
    if tier == "T0":
        return "MONO"
    if tier == "T1":
        return "HYBRID" if independence_required == "should" else "MONO"
    if tier in {"T2", "T3"}:
        independent_count = int(metadata.get("independent_seat_count", 1) or 1)
        return "DISTRIBUTED" if independent_count > 1 else "HYBRID"
    return "MONO"


def compile_council_run_plan_v2(
    ccp: Mapping[str, Any],
    policy: CouncilPolicy,
) -> dict[str, Any]:
    """
    Compile v2.2.1 CouncilRunPlanCore + CouncilRunMeta from CCP metadata and policy.
    Returns dict with 'core' and 'meta' keys.
    (Types will be CouncilRunPlanCore/Meta after A2 models.py merges.)
    """
    metadata = _normalize_metadata(ccp)
    _validate_required_sections(ccp, policy.required_ccp_sections)
    _validate_enum_fields(metadata, policy)

    tier = _resolve_tier(metadata, policy)
    run_type = _resolve_run_type(metadata)

    # T0 strictness check
    _check_t0_strictness(metadata, tier, policy)

    # Lens selection
    lens_info = _select_lenses(tier, policy)

    # Independence resolution (v2 uses tier semantics)
    independence_required = _resolve_independence_required_v2(metadata, tier, policy)

    # Topology
    topology = _resolve_topology_v2(metadata, tier, independence_required)

    # Required roles for tier (Chair always, Challenger for T1+)
    required_roles: tuple[str, ...] = ("Chair",) if tier == "T0" else ("Chair", "Challenger")

    # Model assignments (v2: inject v2 default models to ensure independent family diversity)
    all_roles = required_roles + lens_info["required_lenses"]
    seat_role_map = {
        role: policy.seat_role_map.get(role, "council_reviewer") for role in all_roles
    }
    # Build v2 metadata with fallback independent model if no model_plan provided
    v2_primary, v2_independent = _resolve_default_models_v2()
    model_plan_key = "model_plan_v1" if "model_plan_v1" in metadata else "model_plan"
    existing_plan = metadata.get(model_plan_key, {})
    if not isinstance(existing_plan, Mapping) or not existing_plan:
        # No explicit model plan: inject v2 defaults into a copy of metadata
        import copy as _copy
        metadata = _copy.copy(dict(metadata))
        metadata["model_plan_v1"] = {"primary": v2_primary, "independent": v2_independent}
    model_assignments = _assign_models(
        required_seats=all_roles,
        topology=topology,
        independence_required=independence_required,
        metadata=metadata,
        seat_role_map=seat_role_map,
    )

    # Independence satisfaction check
    independence_satisfied, independent_lenses, compliance_independence = _resolve_independence(
        metadata=metadata,
        policy=policy,
        required_seats=all_roles,
        assignments=model_assignments,
        independence_required=independence_required,
    )

    bootstrap_flags = _enforce_bootstrap(metadata, policy)
    override = metadata.get("override", {})
    override_active = isinstance(override, Mapping) and (
        bool(override.get("tier"))
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

    core_dict: dict[str, Any] = {
        "aur_id": aur_id,
        "tier": tier,
        "run_type": run_type,
        "topology": topology,
        "required_lenses": lens_info["required_lenses"],
        "model_assignments": dict(sorted(model_assignments.items())),
        "lens_role_map": dict(sorted(seat_role_map.items())),
        "independence_required": independence_required,
        "independence_satisfied": independence_satisfied,
        "independent_lenses": independent_lenses,
        "compliance_flags": compliance_flags,
        "override_active": override_active,
        "override_rationale": override_rationale,
        "challenger_required": tier != "T0",
        "contradiction_ledger_required": tier in {"T2", "T3"},
        "closure_gate_required": bool(metadata.get("closure_gate_required", True)),
        "mandatory_lenses": lens_info["mandatory_lenses"],
        "waivable_lenses": lens_info["waivable_lenses"],
        "padded_lenses": lens_info["padded_lenses"],
    }

    meta_dict: dict[str, Any] = {
        "run_id": run_id,
        "timestamp": timestamp,
        "plan_core_hash": "pending",  # Computed by caller with hash_json(core_dict)
    }

    return {"core": core_dict, "meta": meta_dict}
