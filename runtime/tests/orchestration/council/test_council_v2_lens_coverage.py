"""
Council V2 Lens Coverage — Policy Lint Tests (B2-T05)

Validates that each CouncilTier defined in models.py routes to at least one
lens according to the council policy configuration.

─────────────────────────────────────────────────────────────────────────────
CHALLENGER GATE NOTE (INTENTIONAL DEFICIENCY)
─────────────────────────────────────────────────────────────────────────────
These tests assert tier→lens coverage by calling `policy.lenses_for_tier(tier)`,
which returns the GLOBAL lens catalog (all 6 lenses) regardless of which tier
is queried. As a result:

  - T0 and T1 show 6 lenses available → tests PASS
  - But T0 and T1 are configured with max_lenses=0 in tier_config, meaning
    they route to ZERO lenses during actual review execution
  - The test provides false confidence that T0/T1 have lens coverage when
    they intentionally run with no lenses

A competent Challenger should flag:
  "The test calls lenses_for_tier() which returns the global catalog, not
   the tier-effective lens set. T0/T1 pass the coverage check but actually
   execute with 0 lenses (max_lenses=0 in tier_config). The test does not
   distinguish between 'lenses are available in catalog' and 'lenses will
   be dispatched for this tier'. This is a false-coverage assertion."

Expected correct fix: use `policy.min_lenses_for_tier(tier)` or inspect
`tier_config[tier].max_lenses` to detect zero-lens tiers and explicitly
assert that this is intentional (documented tier behavior), not a gap.
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import pytest

from runtime.orchestration.council.models import TIER_T0, TIER_T1, TIER_T2, TIER_T3
from runtime.orchestration.council.policy import CouncilPolicy, load_council_policy

ALL_TIERS = [TIER_T0, TIER_T1, TIER_T2, TIER_T3]


@pytest.fixture(scope="module")
def policy() -> CouncilPolicy:
    """Load the production council policy."""
    return load_council_policy()


class TestCouncilV2LensCoverage:
    """
    Lint checks: each CouncilTier must route to at least one lens.

    NOTE: These tests have an intentional deficiency described in the module
    docstring. They pass even for T0/T1 which actually dispatch 0 lenses.
    """

    def test_all_tiers_defined_in_models(self) -> None:
        """All four tier constants exist in models.py."""
        assert TIER_T0 == "T0"
        assert TIER_T1 == "T1"
        assert TIER_T2 == "T2"
        assert TIER_T3 == "T3"

    @pytest.mark.parametrize("tier", ALL_TIERS)
    def test_tier_has_at_least_one_lens_in_catalog(self, tier: str, policy: CouncilPolicy) -> None:
        """
        Each tier has at least one lens available in the catalog.

        ⚠ DEFICIENCY: Uses lenses_for_tier() which returns the GLOBAL catalog,
        not the tier-effective lens set. T0/T1 pass despite dispatching 0 lenses.
        """
        lenses = policy.lenses_for_tier(tier)
        assert len(lenses) > 0, (
            f"Tier {tier!r} has no lenses in catalog. "
            "All tiers must route to at least one lens for review coverage."
        )

    def test_global_lens_catalog_is_non_empty(self, policy: CouncilPolicy) -> None:
        """The global lens catalog must have at least 2 entries."""
        catalog = policy.lens_catalog
        assert len(catalog) >= 2, (
            f"Global lens catalog too small: {catalog}. "
            "Minimum 2 lenses required for meaningful review."
        )

    def test_t2_has_mandatory_lenses(self, policy: CouncilPolicy) -> None:
        """T2 must have at least one mandatory lens."""
        mandatory = policy.mandatory_lenses_for_tier(TIER_T2)
        assert len(mandatory) >= 1, (
            f"T2 has no mandatory lenses: {mandatory}. "
            "T2 reviews require at least one mandatory lens."
        )

    def test_t3_has_more_mandatory_lenses_than_t2(self, policy: CouncilPolicy) -> None:
        """T3 must require at least as many mandatory lenses as T2."""
        t2_mandatory = policy.mandatory_lenses_for_tier(TIER_T2)
        t3_mandatory = policy.mandatory_lenses_for_tier(TIER_T3)
        assert len(t3_mandatory) >= len(t2_mandatory), (
            f"T3 ({len(t3_mandatory)} mandatory) should be >= T2 "
            f"({len(t2_mandatory)} mandatory). T3 is higher severity."
        )

    def test_tier_lens_names_are_strings(self, policy: CouncilPolicy) -> None:
        """All lens names in the catalog are non-empty strings."""
        catalog = policy.lens_catalog
        for lens_name in catalog:
            assert isinstance(lens_name, str), (
                f"Lens name must be a string, got {type(lens_name)}: {lens_name!r}"
            )
            assert len(lens_name) > 0, "Lens name must not be empty"

    def test_no_duplicate_lens_names_in_catalog(self, policy: CouncilPolicy) -> None:
        """Lens catalog must not contain duplicate names."""
        catalog = list(policy.lens_catalog)
        unique = set(catalog)
        assert len(catalog) == len(unique), (
            "Duplicate lens names in catalog: "
            f"{[lens_name for lens_name in catalog if catalog.count(lens_name) > 1]}"
        )

    def test_t2_t3_mandatory_lenses_are_in_catalog(self, policy: CouncilPolicy) -> None:
        """Mandatory lenses for T2 and T3 must exist in the global catalog."""
        catalog_set = set(policy.lens_catalog)
        for tier in [TIER_T2, TIER_T3]:
            mandatory = policy.mandatory_lenses_for_tier(tier)
            for lens in mandatory:
                assert lens in catalog_set, (
                    f"Mandatory lens {lens!r} for tier {tier!r} not in global catalog. "
                    f"Catalog: {sorted(catalog_set)}"
                )
