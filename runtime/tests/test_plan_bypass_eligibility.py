"""
Tests for Plan Bypass Eligibility (Art. XVIII §5)

Verifies that ConfigurableLoopPolicy correctly determines
when loop retries can proceed without Plan approval.
"""

import pytest
from runtime.orchestration.loop.configurable_policy import ConfigurableLoopPolicy
from runtime.orchestration.loop.ledger import AttemptLedger, AttemptRecord
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
            },
            "global_bypass_limit": 5,
            "default_per_class_limit": 3,
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


_USE_DEFAULT_PBI = object()


def _mk_record(
    *,
    attempt_id: int,
    failure_class: str | None,
    applied: object,
    plan_bypass_info: object = _USE_DEFAULT_PBI,
) -> AttemptRecord:
    if plan_bypass_info is _USE_DEFAULT_PBI:
        plan_bypass_info = {"applied": applied, "rule_id": "loop.lint_error"}
    return AttemptRecord(
        attempt_id=attempt_id,
        timestamp="2026-02-01T00:00:00Z",
        run_id="run-budget",
        policy_hash="p",
        input_hash="i",
        actions_taken=[],
        diff_hash=None,
        changed_files=["src/file.py"],
        evidence_hashes={},
        success=False,
        failure_class=failure_class,
        terminal_reason=None,
        next_action="retry",
        rationale="test",
        plan_bypass_info=plan_bypass_info,
    )


def _mk_ledger(tmp_path, records: list[AttemptRecord]) -> AttemptLedger:
    ledger = AttemptLedger(tmp_path / "attempt_ledger.jsonl")
    ledger.history = records
    return ledger


class TestBudgetEnforcement:
    def test_budget_denies_when_per_class_limit_exhausted(self, policy_with_bypass, tmp_path):
        ledger = _mk_ledger(
            tmp_path,
            [
                _mk_record(attempt_id=1, failure_class="lint_error", applied=True),
                _mk_record(attempt_id=2, failure_class="LINT_ERROR", applied=True),
                _mk_record(attempt_id=3, failure_class="lint_error", applied=True),
            ],
        )
        decision = policy_with_bypass.evaluate_plan_bypass(
            failure_class_key="lint_error",
            proposed_patch={"files_touched": 1, "total_line_delta": 1, "files": ["src/file.py"]},
            protected_path_registry=[],
            ledger=ledger,
        )
        assert decision["eligible"] is False
        assert "per-class bypass budget exhausted" in decision["decision_reason"].lower()
        assert decision["budget"]["per_class_remaining"] == 0
        assert decision["budget"]["global_remaining"] == 2

    def test_budget_denies_when_global_limit_exhausted(self, policy_with_bypass, tmp_path):
        ledger = _mk_ledger(
            tmp_path,
            [
                _mk_record(attempt_id=1, failure_class="lint_error", applied=True),
                _mk_record(attempt_id=2, failure_class="typo", applied=True),
                _mk_record(attempt_id=3, failure_class="formatting_error", applied=True),
                _mk_record(attempt_id=4, failure_class="test_flake", applied=True),
                _mk_record(attempt_id=5, failure_class="typo", applied=True),
            ],
        )
        decision = policy_with_bypass.evaluate_plan_bypass(
            failure_class_key="lint_error",
            proposed_patch={"files_touched": 1, "total_line_delta": 1, "files": ["src/file.py"]},
            protected_path_registry=[],
            ledger=ledger,
        )
        assert decision["eligible"] is False
        assert "global bypass budget exhausted" in decision["decision_reason"].lower()
        assert decision["budget"]["global_remaining"] == 0
        assert decision["budget"]["per_class_remaining"] == 2

    def test_budget_allows_when_under_limits(self, policy_with_bypass, tmp_path):
        ledger = _mk_ledger(
            tmp_path,
            [
                _mk_record(attempt_id=1, failure_class="lint_error", applied=True),
                _mk_record(attempt_id=2, failure_class="typo", applied=True),
            ],
        )
        decision = policy_with_bypass.evaluate_plan_bypass(
            failure_class_key="lint_error",
            proposed_patch={"files_touched": 1, "total_line_delta": 1, "files": ["src/file.py"]},
            protected_path_registry=[],
            ledger=ledger,
        )
        assert decision["eligible"] is True
        assert decision["decision_reason"] == "Eligible"
        assert decision["budget"]["per_class_remaining"] == 2
        assert decision["budget"]["global_remaining"] == 3

    def test_budget_allows_on_fresh_empty_ledger(self, policy_with_bypass, tmp_path):
        ledger = _mk_ledger(tmp_path, [])
        decision = policy_with_bypass.evaluate_plan_bypass(
            failure_class_key="lint_error",
            proposed_patch={"files_touched": 1, "total_line_delta": 1, "files": ["src/file.py"]},
            protected_path_registry=[],
            ledger=ledger,
        )
        assert decision["eligible"] is True
        assert decision["budget"]["per_class_remaining"] == 3
        assert decision["budget"]["global_remaining"] == 5

    def test_budget_counts_only_applied_true_entries(self, policy_with_bypass, tmp_path):
        ledger = _mk_ledger(
            tmp_path,
            [
                _mk_record(attempt_id=1, failure_class="lint_error", applied=False),
                _mk_record(attempt_id=2, failure_class="lint_error", applied=True),
                _mk_record(attempt_id=3, failure_class="lint_error", applied=True, plan_bypass_info=None),
                _mk_record(attempt_id=4, failure_class="lint_error", applied=True, plan_bypass_info="bad-shape"),
            ],
        )
        decision = policy_with_bypass.evaluate_plan_bypass(
            failure_class_key="lint_error",
            proposed_patch={"files_touched": 1, "total_line_delta": 1, "files": ["src/file.py"]},
            protected_path_registry=[],
            ledger=ledger,
        )
        assert decision["eligible"] is True
        assert decision["budget"]["per_class_remaining"] == 2
        assert decision["budget"]["global_remaining"] == 4

    def test_budget_decision_includes_remaining_fields(self, policy_with_bypass, tmp_path):
        ledger = _mk_ledger(
            tmp_path,
            [_mk_record(attempt_id=1, failure_class="lint_error", applied=True)],
        )
        decision = policy_with_bypass.evaluate_plan_bypass(
            failure_class_key="lint_error",
            proposed_patch={"files_touched": 1, "total_line_delta": 1, "files": ["src/file.py"]},
            protected_path_registry=[],
            ledger=ledger,
        )
        assert "budget" in decision
        assert "per_class_remaining" in decision["budget"]
        assert "global_remaining" in decision["budget"]
