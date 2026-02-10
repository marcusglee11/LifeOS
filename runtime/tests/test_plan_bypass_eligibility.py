"""
Tests for Plan Bypass Eligibility (Art. XVIII §5)

Verifies that ConfigurableLoopPolicy correctly determines
when loop retries can proceed without Plan approval.
"""

import pytest
from runtime.orchestration.loop.configurable_policy import ConfigurableLoopPolicy
from runtime.orchestration.loop.taxonomy import FailureClass


@pytest.fixture
def policy_with_bypass():
    """Create a policy config with plan_bypass_eligible rules."""
    config = {
        "budgets": {
            "retry_limits": {
                "LINT_ERROR": 3,
                "TEST_FLAKE": 2,
                "TYPO": 3,
                "FORMATTING_ERROR": 3,
                "TEST_FAILURE": 3,
            }
        },
        "failure_routing": {
            "LINT_ERROR": {
                "default_action": "RETRY",
                "plan_bypass_eligible": True,
                "scope_limit": {"max_lines": 50, "max_files": 3},
            },
            "TEST_FLAKE": {
                "default_action": "RETRY",
                "plan_bypass_eligible": True,
                "scope_limit": {"max_lines": 50, "max_files": 3},
            },
            "TYPO": {
                "default_action": "RETRY",
                "plan_bypass_eligible": True,
                "scope_limit": {"max_lines": 50, "max_files": 3},
            },
            "FORMATTING_ERROR": {
                "default_action": "RETRY",
                "plan_bypass_eligible": True,
                "scope_limit": {"max_lines": 50, "max_files": 3},
            },
            "TEST_FAILURE": {
                "default_action": "RETRY",
                "plan_bypass_eligible": False,  # Not eligible
            },
            "SYNTAX_ERROR": {
                "default_action": "TERMINATE",
                "plan_bypass_eligible": False,
            },
        },
        "waiver_rules": {},
        "progress_detection": {},
    }
    return ConfigurableLoopPolicy(config)


class TestPlanBypassEligibility:
    """Test plan bypass eligibility determination."""

    def test_lint_error_eligible_within_scope(self, policy_with_bypass):
        """LINT_ERROR with small diff should be eligible."""
        eligible, reason = policy_with_bypass.is_plan_bypass_eligible(
            failure_class=FailureClass.LINT_ERROR,
            proposed_diff_lines=10,
            proposed_files=["src/foo.py", "src/bar.py"],
        )
        assert eligible is True
        assert "eligible" in reason.lower()

    def test_lint_error_exceeds_max_lines(self, policy_with_bypass):
        """LINT_ERROR exceeding max_lines should not be eligible."""
        eligible, reason = policy_with_bypass.is_plan_bypass_eligible(
            failure_class=FailureClass.LINT_ERROR,
            proposed_diff_lines=100,  # Exceeds 50
            proposed_files=["src/foo.py"],
        )
        assert eligible is False
        assert "max_lines" in reason.lower()

    def test_lint_error_exceeds_max_files(self, policy_with_bypass):
        """LINT_ERROR exceeding max_files should not be eligible."""
        eligible, reason = policy_with_bypass.is_plan_bypass_eligible(
            failure_class=FailureClass.LINT_ERROR,
            proposed_diff_lines=10,
            proposed_files=["a.py", "b.py", "c.py", "d.py"],  # Exceeds 3
        )
        assert eligible is False
        assert "max_files" in reason.lower()

    def test_lint_error_governance_path(self, policy_with_bypass):
        """LINT_ERROR touching governance path should not be eligible."""
        eligible, reason = policy_with_bypass.is_plan_bypass_eligible(
            failure_class=FailureClass.LINT_ERROR,
            proposed_diff_lines=10,
            proposed_files=["docs/01_governance/policy.md"],
        )
        assert eligible is False
        assert "governance" in reason.lower()

    def test_test_failure_not_eligible(self, policy_with_bypass):
        """TEST_FAILURE should never be eligible."""
        eligible, reason = policy_with_bypass.is_plan_bypass_eligible(
            failure_class=FailureClass.TEST_FAILURE,
            proposed_diff_lines=10,
            proposed_files=["src/foo.py"],
        )
        assert eligible is False
        assert "not plan_bypass_eligible" in reason.lower()

    def test_test_flake_eligible(self, policy_with_bypass):
        """TEST_FLAKE should be eligible within scope."""
        eligible, reason = policy_with_bypass.is_plan_bypass_eligible(
            failure_class=FailureClass.TEST_FLAKE,
            proposed_diff_lines=20,
            proposed_files=["src/test.py"],
        )
        assert eligible is True

    def test_typo_eligible(self, policy_with_bypass):
        """TYPO should be eligible within scope."""
        eligible, reason = policy_with_bypass.is_plan_bypass_eligible(
            failure_class=FailureClass.TYPO,
            proposed_diff_lines=5,
            proposed_files=["README.md"],
        )
        assert eligible is True

    def test_formatting_error_eligible(self, policy_with_bypass):
        """FORMATTING_ERROR should be eligible within scope."""
        eligible, reason = policy_with_bypass.is_plan_bypass_eligible(
            failure_class=FailureClass.FORMATTING_ERROR,
            proposed_diff_lines=30,
            proposed_files=["src/main.py", "src/utils.py"],
        )
        assert eligible is True

    def test_unknown_failure_class_not_eligible(self, policy_with_bypass):
        """Unknown failure class should not be eligible."""
        eligible, reason = policy_with_bypass.is_plan_bypass_eligible(
            failure_class=FailureClass.UNKNOWN,
            proposed_diff_lines=10,
            proposed_files=["src/foo.py"],
        )
        assert eligible is False

    def test_gemini_md_is_governance_path(self, policy_with_bypass):
        """GEMINI.md should be detected as governance path."""
        eligible, reason = policy_with_bypass.is_plan_bypass_eligible(
            failure_class=FailureClass.LINT_ERROR,
            proposed_diff_lines=10,
            proposed_files=["GEMINI.md"],
        )
        assert eligible is False
        assert "governance" in reason.lower()

    def test_constitution_pattern_is_governance(self, policy_with_bypass):
        """Constitution files should be detected as governance paths."""
        eligible, reason = policy_with_bypass.is_plan_bypass_eligible(
            failure_class=FailureClass.TYPO,
            proposed_diff_lines=5,
            proposed_files=["docs/MyConstitution_v1.0.md"],
        )
        assert eligible is False
        assert "governance" in reason.lower()

    def test_protocol_pattern_is_governance(self, policy_with_bypass):
        """Protocol files should be detected as governance paths."""
        eligible, reason = policy_with_bypass.is_plan_bypass_eligible(
            failure_class=FailureClass.TYPO,
            proposed_diff_lines=5,
            proposed_files=["docs/Some_Protocol_v1.0.md"],
        )
        assert eligible is False
        assert "governance" in reason.lower()


class TestGovernancePathDetection:
    """Test governance path detection helper."""

    def test_foundations_prefix(self, policy_with_bypass):
        """docs/00_foundations/ should be governance-controlled."""
        assert policy_with_bypass._is_governance_path("docs/00_foundations/constitution.md")

    def test_governance_prefix(self, policy_with_bypass):
        """docs/01_governance/ should be governance-controlled."""
        assert policy_with_bypass._is_governance_path("docs/01_governance/policy.md")

    def test_runtime_governance_prefix(self, policy_with_bypass):
        """runtime/governance/ should be governance-controlled."""
        assert policy_with_bypass._is_governance_path("runtime/governance/rules.py")

    def test_gemini_file(self, policy_with_bypass):
        """GEMINI.md should be governance-controlled."""
        assert policy_with_bypass._is_governance_path("GEMINI.md")

    def test_constitution_pattern(self, policy_with_bypass):
        """Files matching *Constitution*.md should be governance-controlled."""
        assert policy_with_bypass._is_governance_path("LifeOS_Constitution_v2.0.md")
        assert policy_with_bypass._is_governance_path("some/path/Constitution_Draft.md")

    def test_protocol_pattern(self, policy_with_bypass):
        """Files matching *Protocol*.md should be governance-controlled."""
        assert policy_with_bypass._is_governance_path("Build_Protocol_v1.0.md")
        assert policy_with_bypass._is_governance_path("docs/Protocol_Guide.md")

    def test_regular_file_not_governance(self, policy_with_bypass):
        """Regular files should not be governance-controlled."""
        assert not policy_with_bypass._is_governance_path("src/main.py")
        assert not policy_with_bypass._is_governance_path("README.md")
        assert not policy_with_bypass._is_governance_path("docs/03_specs/feature.md")
