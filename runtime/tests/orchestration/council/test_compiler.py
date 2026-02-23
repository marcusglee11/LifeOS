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


def test_compile_plan_should_independence_waiver():
    policy = load_council_policy()
    ccp = {
        "header": {
            "aur_id": "AUR-7",
            "aur_type": "code",
            "change_class": "amend",
            "blast_radius": "module",
            "reversibility": "moderate",
            "uncertainty": "medium",
            "touches": ["runtime_core"],
            "safety_critical": False,
            # Both models from the same family -> independence can't be satisfied.
            "model_plan_v1": {
                "primary": "claude-sonnet-4-5",
                "independent": "claude-haiku-4-5",
            },
        },
        "sections": _base_sections(),
    }
    plan = compile_council_run_plan(ccp=ccp, policy=policy)
    # Should independence triggers but same-family models -> waived.
    assert plan.independence_required == "should"
    assert plan.compliance_flags["independence_waived"] is True


def test_compile_plan_override_mode():
    policy = load_council_policy()
    # This CCP would normally resolve to M0_FAST.
    ccp = {
        "header": {
            "aur_id": "AUR-8",
            "aur_type": "doc",
            "change_class": "hygiene",
            "blast_radius": "local",
            "reversibility": "easy",
            "uncertainty": "low",
            "touches": ["docs_only"],
            "safety_critical": False,
            "override": {"mode": "M2_FULL", "rationale": "operator escalation"},
        },
        "sections": _base_sections(),
    }
    plan = compile_council_run_plan(ccp=ccp, policy=policy)
    assert plan.mode == "M2_FULL"
    assert plan.override_active is True


def test_compile_plan_blocks_on_missing_ccp_section():
    policy = load_council_policy()
    sections = _base_sections()
    sections.pop("constraints")
    ccp = {
        "header": {
            "aur_id": "AUR-9",
            "aur_type": "doc",
            "change_class": "hygiene",
            "blast_radius": "local",
            "reversibility": "easy",
            "uncertainty": "low",
            "touches": ["docs_only"],
            "safety_critical": False,
        },
        "sections": sections,
    }
    with pytest.raises(CouncilBlockedError) as exc:
        compile_council_run_plan(ccp=ccp, policy=policy)
    assert exc.value.category == "ccp_incomplete"
