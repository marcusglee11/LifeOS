"""
v2.2.1 compiler tests: tier routing (A3) + lens selection (A3) + independence (A4).
All 26 tests. Written BEFORE implementation (TDD).
"""

from __future__ import annotations

import pytest

from runtime.orchestration.council.compiler import (
    _select_lenses,
    compile_council_run_plan_v2,
)
from runtime.orchestration.council.models import CouncilBlockedError
from runtime.orchestration.council.policy import load_council_policy


def _base_sections():
    return {
        "objective": "Review candidate change.",
        "scope": {"surface": "runtime"},
        "constraints": ["deterministic outputs"],
        "artifacts": [{"id": "artifact-1"}],
    }


def _base_header(**kwargs):
    defaults = {
        "aur_id": "AUR-TEST",
        "aur_type": "code",
        "change_class": "amend",
        "blast_radius": "local",
        "reversibility": "moderate",
        "uncertainty": "medium",
        "touches": ["tests"],
        "safety_critical": False,
    }
    defaults.update(kwargs)
    return defaults


def _make_ccp(**header_kwargs):
    return {"header": _base_header(**header_kwargs), "sections": _base_sections()}


# ---------------------------------------------------------------------------
# A3: Tier routing tests
# ---------------------------------------------------------------------------


def test_tier_t0_from_docs_only():
    policy = load_council_policy()
    ccp = _make_ccp(
        aur_type="doc",
        change_class="hygiene",
        blast_radius="local",
        reversibility="easy",
        uncertainty="low",
        touches=["docs_only"],
        safety_critical=False,
    )
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["tier"] == "T0"


def test_tier_t1_default():
    policy = load_council_policy()
    ccp = _make_ccp()
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["tier"] == "T1"


def test_tier_t2_from_runtime_core():
    policy = load_council_policy()
    ccp = _make_ccp(touches=["runtime_core"])
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["tier"] == "T2"


def test_tier_t3_from_governance():
    policy = load_council_policy()
    ccp = _make_ccp(touches=["governance_protocol"])
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["tier"] == "T3"


def test_tier_t3_from_safety_critical():
    policy = load_council_policy()
    ccp = _make_ccp(safety_critical=True)
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["tier"] == "T3"


def test_tier_override():
    policy = load_council_policy()
    ccp = _make_ccp()
    ccp["header"]["override"] = {"tier": "T3", "rationale": "manual escalation"}
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["tier"] == "T3"
    assert result["core"]["override_active"] is True


def test_tier_t0_strictness_blocks_moderate():
    policy = load_council_policy()
    ccp = {
        "header": _base_header(
            aur_type="doc",
            change_class="hygiene",
            blast_radius="local",
            reversibility="moderate",
            uncertainty="low",
            touches=["docs_only"],
            safety_critical=False,
        ),
        "sections": _base_sections(),
    }
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["tier"] != "T0"


# ---------------------------------------------------------------------------
# A3: Lens selection tests
# ---------------------------------------------------------------------------


def test_lenses_t0_none():
    policy = load_council_policy()
    ccp = _make_ccp(
        aur_type="doc",
        change_class="hygiene",
        blast_radius="local",
        reversibility="easy",
        uncertainty="low",
        touches=["docs_only"],
        safety_critical=False,
    )
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["tier"] == "T0"
    assert len(result["core"]["required_lenses"]) == 0


def test_lenses_t1_none():
    policy = load_council_policy()
    ccp = _make_ccp()
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["tier"] == "T1"
    assert len(result["core"]["required_lenses"]) == 0


def test_lenses_t2_selected():
    policy = load_council_policy()
    ccp = _make_ccp(touches=["runtime_core"])
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["tier"] == "T2"
    lenses = result["core"]["required_lenses"]
    assert 2 <= len(lenses) <= 3


def test_lenses_t3_selected():
    policy = load_council_policy()
    ccp = _make_ccp(touches=["governance_protocol"])
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["tier"] == "T3"
    lenses = result["core"]["required_lenses"]
    assert 3 <= len(lenses) <= 4


def test_lens_padding_deterministic():
    policy = load_council_policy()
    ccp = _make_ccp(touches=["runtime_core"])
    result1 = compile_council_run_plan_v2(ccp, policy)
    result2 = compile_council_run_plan_v2(ccp, policy)
    assert result1["core"]["required_lenses"] == result2["core"]["required_lenses"]


def test_lens_padding_no_duplicates():
    policy = load_council_policy()
    ccp = _make_ccp(touches=["governance_protocol"])
    result = compile_council_run_plan_v2(ccp, policy)
    lenses = result["core"]["required_lenses"]
    assert len(lenses) == len(set(lenses))


def test_lens_catalog_exhaustion_blocks():
    from unittest.mock import patch

    policy = load_council_policy()
    with patch.object(type(policy), "lens_catalog", property(lambda self: ("Risk",))):
        with patch.object(type(policy), "padding_priority", property(lambda self: ("Risk",))):
            with pytest.raises(CouncilBlockedError) as exc:
                _select_lenses("T3", policy)
            assert "POLICY_LENS_CATALOG_INSUFFICIENT" in exc.value.category


def test_lens_mandatory_waivable_annotated():
    policy = load_council_policy()
    ccp = _make_ccp(touches=["runtime_core"])
    result = compile_council_run_plan_v2(ccp, policy)
    assert "Risk" in result["core"]["mandatory_lenses"]
    required = set(result["core"]["required_lenses"])
    mandatory = set(result["core"]["mandatory_lenses"])
    waivable = set(result["core"]["waivable_lenses"])
    assert required == mandatory | waivable


def test_run_type_defaults_review():
    policy = load_council_policy()
    ccp = _make_ccp()
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["run_type"] == "review"


def test_run_type_advisory_compiles():
    policy = load_council_policy()
    ccp = _make_ccp()
    ccp["header"]["run_type"] = "advisory"
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["run_type"] == "advisory"


def test_same_ccp_same_plan_hash():
    from runtime.governance.HASH_POLICY_v1 import hash_json

    policy = load_council_policy()
    ccp = _make_ccp(touches=["runtime_core"])
    result1 = compile_council_run_plan_v2(ccp, policy)
    result2 = compile_council_run_plan_v2(ccp, policy)
    core1 = dict(result1["core"])
    core2 = dict(result2["core"])
    assert hash_json(core1) == hash_json(core2)


# ---------------------------------------------------------------------------
# A4: Independence tests
# ---------------------------------------------------------------------------


def test_independence_must_satisfied():
    policy = load_council_policy()
    ccp = _make_ccp(
        safety_critical=True,
        model_plan_v1={"primary": "claude-sonnet-4-5", "independent": "opencode/glm-5-free"},
    )
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["independence_required"] == "must"
    assert result["core"]["independence_satisfied"] is True


def test_independence_must_blocks_same_family():
    policy = load_council_policy()
    ccp = _make_ccp(
        safety_critical=True,
        model_plan_v1={"primary": "claude-sonnet-4-5", "independent": "claude-haiku-4-5"},
    )
    with pytest.raises(CouncilBlockedError) as exc:
        compile_council_run_plan_v2(ccp, policy)
    assert exc.value.category == "independence_unsatisfied"


def test_independence_must_emergency_override():
    policy = load_council_policy()
    ccp = _make_ccp(
        safety_critical=True,
        model_plan_v1={"primary": "claude-sonnet-4-5", "independent": "claude-haiku-4-5"},
    )
    ccp["header"]["override"] = {"emergency_ceo": True, "rationale": "break-glass"}
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["compliance_flags"]["ceo_override"] is True


def test_independence_should_satisfied():
    policy = load_council_policy()
    ccp = _make_ccp(
        touches=["runtime_core"],
        model_plan_v1={"primary": "claude-sonnet-4-5", "independent": "opencode/glm-5-free"},
    )
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["independence_required"] == "should"


def test_independence_should_unsatisfied_flags():
    policy = load_council_policy()
    ccp = _make_ccp(
        touches=["runtime_core"],
        model_plan_v1={"primary": "claude-sonnet-4-5", "independent": "claude-haiku-4-5"},
    )
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["independence_required"] == "should"
    assert result["core"]["compliance_flags"].get("independence_waived") is True


def test_independence_should_explicit_not_emergent():
    policy = load_council_policy()
    ccp = _make_ccp(touches=["runtime_core"])
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["independence_required"] in {"should", "none"}


def test_independence_none_no_flags():
    policy = load_council_policy()
    ccp = _make_ccp()
    result = compile_council_run_plan_v2(ccp, policy)
    assert result["core"]["independence_required"] == "none"
    assert not result["core"]["compliance_flags"].get("independence_waived", False)


def test_independence_truth_table_availability():
    policy = load_council_policy()
    ccp1 = _make_ccp(
        safety_critical=True,
        model_plan_v1={"primary": "claude-sonnet-4-5", "independent": "opencode/glm-5-free"},
    )
    r1 = compile_council_run_plan_v2(ccp1, policy)
    assert r1["core"]["independence_satisfied"] is True

    ccp2 = _make_ccp(
        safety_critical=True,
        model_plan_v1={"primary": "claude-sonnet-4-5", "independent": "claude-haiku-4-5"},
    )
    with pytest.raises(CouncilBlockedError):
        compile_council_run_plan_v2(ccp2, policy)

    ccp3 = _make_ccp()
    r3 = compile_council_run_plan_v2(ccp3, policy)
    assert r3["core"]["independence_required"] == "none"
