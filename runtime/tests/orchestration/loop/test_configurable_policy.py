"""
Unit tests for ConfigurableLoopPolicy (Phase B.1)

Tests config-driven policy decisions, retry counting, waiver eligibility,
and escalation triggers.
"""
import pytest
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List

from runtime.orchestration.loop.configurable_policy import ConfigurableLoopPolicy
from runtime.orchestration.loop.config_loader import PolicyConfigLoader
from runtime.orchestration.loop.ledger import AttemptLedger
from runtime.orchestration.loop.taxonomy import FailureClass, TerminalOutcome, TerminalReason


@dataclass
class MockAttempt:
    """Mock attempt for testing"""
    attempt_id: str
    success: bool
    failure_class: Optional[str]
    diff_hash: Optional[str] = None
    diff_summary: Optional[str] = None


class MockLedger:
    """Mock ledger for testing"""
    def __init__(self, attempts: List[MockAttempt]):
        self.history = attempts


@pytest.fixture
def policy_config(tmp_path):
    """Create valid policy config for testing"""
    config_content = """schema_version: "1.0"

policy_metadata:
  version: "test_v1.0"
  effective_date: "2026-01-14"
  author: "test"
  description: "Test config"

budgets:
  max_attempts: 5
  max_tokens: 100000
  max_wall_clock_minutes: 30
  max_diff_lines_per_attempt: 300
  retry_limits:
    TEST_FAILURE: 3
    SYNTAX_ERROR: 0
    TIMEOUT: 1
    VALIDATION_ERROR: 0
    REVIEW_REJECTION: 3
    DEPENDENCY_ERROR: 2
    ENVIRONMENT_ERROR: 1
    TOOL_INVOCATION_ERROR: 1
    CONFIG_ERROR: 0
    GOVERNANCE_VIOLATION: 0
    UNKNOWN: 0

failure_routing:
  TEST_FAILURE:
    default_action: "RETRY"
    terminal_on_retry_exhausted: true
    terminal_outcome: "WAIVER_REQUESTED"
    terminal_reason: "MAX_RETRIES_EXCEEDED"
  SYNTAX_ERROR:
    default_action: "TERMINATE"
    terminal_outcome: "BLOCKED"
    terminal_reason: "CRITICAL_FAILURE"
  TIMEOUT:
    default_action: "RETRY"
    terminal_on_retry_exhausted: true
    terminal_outcome: "ESCALATION_REQUESTED"
    terminal_reason: "TIMEOUT_RETRY_LIMIT"
  VALIDATION_ERROR:
    default_action: "TERMINATE"
    terminal_outcome: "BLOCKED"
    terminal_reason: "CRITICAL_FAILURE"
  REVIEW_REJECTION:
    default_action: "RETRY"
    terminal_on_retry_exhausted: true
    terminal_outcome: "ESCALATION_REQUESTED"
    terminal_reason: "NON_CONVERGENCE"
  DEPENDENCY_ERROR:
    default_action: "RETRY"
    terminal_on_retry_exhausted: true
    terminal_outcome: "BLOCKED"
    terminal_reason: "DEPENDENCY_UNAVAILABLE"
  ENVIRONMENT_ERROR:
    default_action: "RETRY"
    terminal_on_retry_exhausted: true
    terminal_outcome: "ESCALATION_REQUESTED"
    terminal_reason: "ENVIRONMENT_ISSUE"
  TOOL_INVOCATION_ERROR:
    default_action: "RETRY"
    terminal_on_retry_exhausted: true
    terminal_outcome: "BLOCKED"
    terminal_reason: "CRITICAL_FAILURE"
  CONFIG_ERROR:
    default_action: "TERMINATE"
    terminal_outcome: "BLOCKED"
    terminal_reason: "CRITICAL_FAILURE"
  GOVERNANCE_VIOLATION:
    default_action: "TERMINATE"
    terminal_outcome: "ESCALATION_REQUESTED"
    terminal_reason: "GOVERNANCE_ESCALATION"
  UNKNOWN:
    default_action: "TERMINATE"
    terminal_outcome: "BLOCKED"
    terminal_reason: "UNKNOWN_FAILURE"

waiver_rules:
  eligible_failure_classes:
    - TEST_FAILURE
    - REVIEW_REJECTION
  ineligible_failure_classes:
    - SYNTAX_ERROR
    - VALIDATION_ERROR
    - UNKNOWN
  escalation_triggers:
    - governance_surface_touched: true
    - protected_path_modified: true

progress_detection:
  no_progress_enabled: true
  no_progress_lookback: 1
  oscillation_enabled: true
  oscillation_window_size: 3
  deadlock_threshold: 2

determinism:
  hash_algorithm: "sha256"
  hash_full_config: true
  policy_change_action: "ESCALATION_REQUESTED"
  policy_change_reason: "POLICY_CHANGED_MID_RUN"
  canonical_hashing_enabled: true
  line_ending_normalization: "LF"
"""
    config_file = tmp_path / "policy_test.yaml"
    config_file.write_text(config_content, encoding='utf-8')

    loader = PolicyConfigLoader(config_file)
    return loader.load()


class TestConfigurablePolicyBasics:
    """Test basic policy initialization and simple decisions"""

    def test_policy_initialization(self, policy_config):
        """Policy initializes with valid config"""
        policy = ConfigurableLoopPolicy(policy_config)
        assert policy.config == policy_config

    def test_start_of_run_returns_retry(self, policy_config):
        """Empty history returns RETRY with 'Start' reason"""
        policy = ConfigurableLoopPolicy(policy_config)
        ledger = MockLedger([])

        action, reason, override = policy.decide_next_action(ledger)

        assert action == "RETRY"
        assert "Start" in reason
        assert override is None

    def test_success_returns_terminate_pass(self, policy_config):
        """Successful attempt returns TERMINATE with PASS"""
        policy = ConfigurableLoopPolicy(policy_config)
        ledger = MockLedger([
            MockAttempt("A1", success=True, failure_class=None)
        ])

        action, reason, override = policy.decide_next_action(ledger)

        assert action == "TERMINATE"
        assert TerminalReason.PASS.value in reason
        assert override is None


class TestRetryLimitEnforcement:
    """Test retry limit enforcement from config"""

    def test_retry_within_limit(self, policy_config):
        """Failure within retry limit returns RETRY"""
        policy = ConfigurableLoopPolicy(policy_config)
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h1")
        ])

        action, reason, override = policy.decide_next_action(ledger)

        assert action == "RETRY"
        assert "TEST_FAILURE" in reason or "test_failure" in reason
        assert override is None

    def test_retry_limit_exhausted_waiver_eligible(self, policy_config):
        """Retry limit exhausted for waiver-eligible class returns WAIVER_REQUESTED"""
        policy = ConfigurableLoopPolicy(policy_config)
        # TEST_FAILURE has retry_limit=3, so 3 failures should exhaust it
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h1"),
            MockAttempt("A2", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h2"),
            MockAttempt("A3", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h3")
        ])

        action, reason, override = policy.decide_next_action(ledger)

        assert action == "TERMINATE"
        assert "waiver" in reason.lower() or "WAIVER" in reason
        assert override == "WAIVER_REQUESTED"

    def test_retry_limit_exhausted_not_waiver_eligible(self, policy_config):
        """Retry limit exhausted for non-waiver-eligible class returns configured terminal_outcome"""
        policy = ConfigurableLoopPolicy(policy_config)
        # TIMEOUT has retry_limit=1 and not waiver eligible, terminal_outcome=ESCALATION_REQUESTED
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.TIMEOUT.value, diff_hash="h1")
        ])

        action, reason, override = policy.decide_next_action(ledger)

        assert action == "TERMINATE"
        assert override == "ESCALATION_REQUESTED"

    def test_zero_retry_limit_immediate_terminate(self, policy_config):
        """Failure class with 0 retry limit terminates immediately"""
        policy = ConfigurableLoopPolicy(policy_config)
        # SYNTAX_ERROR has retry_limit=0 and default_action=TERMINATE
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.SYNTAX_ERROR.value)
        ])

        action, reason, override = policy.decide_next_action(ledger)

        assert action == "TERMINATE"
        assert override == "BLOCKED"


class TestRetryCountLogic:
    """Test retry counting logic"""

    def test_count_retries_consecutive_same_class(self, policy_config):
        """Counts only consecutive retries of same failure class"""
        policy = ConfigurableLoopPolicy(policy_config)
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h1"),
            MockAttempt("A2", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h2"),
            MockAttempt("A3", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h3")
        ])

        count = policy._count_retries_for_class(ledger, FailureClass.TEST_FAILURE)
        assert count == 3

    def test_count_retries_resets_on_different_class(self, policy_config):
        """Retry count resets when different failure class occurs"""
        policy = ConfigurableLoopPolicy(policy_config)
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h1"),
            MockAttempt("A2", success=False, failure_class=FailureClass.SYNTAX_ERROR.value, diff_hash="h2"),
            MockAttempt("A3", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h3")
        ])

        count = policy._count_retries_for_class(ledger, FailureClass.TEST_FAILURE)
        assert count == 1  # Only counts most recent TEST_FAILURE

    def test_count_retries_resets_on_success(self, policy_config):
        """Retry count resets when success occurs"""
        policy = ConfigurableLoopPolicy(policy_config)
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h1"),
            MockAttempt("A2", success=True, failure_class=None),
            MockAttempt("A3", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h3")
        ])

        count = policy._count_retries_for_class(ledger, FailureClass.TEST_FAILURE)
        assert count == 1  # Only counts after success


class TestWaiverEligibility:
    """Test waiver eligibility checks"""

    def test_explicit_eligible_class(self, policy_config):
        """Explicitly eligible failure class returns True"""
        policy = ConfigurableLoopPolicy(policy_config)

        eligible = policy._check_waiver_eligibility(FailureClass.TEST_FAILURE)
        assert eligible is True

    def test_explicit_ineligible_class(self, policy_config):
        """Explicitly ineligible failure class returns False"""
        policy = ConfigurableLoopPolicy(policy_config)

        eligible = policy._check_waiver_eligibility(FailureClass.SYNTAX_ERROR)
        assert eligible is False

    def test_unlisted_class_not_eligible(self, policy_config):
        """Unlisted failure class defaults to not eligible"""
        policy = ConfigurableLoopPolicy(policy_config)

        eligible = policy._check_waiver_eligibility(FailureClass.TIMEOUT)
        assert eligible is False


class TestEscalationTriggers:
    """Test escalation trigger detection"""

    def test_no_escalation_without_protected_paths(self, policy_config):
        """No escalation if protected paths not touched"""
        policy = ConfigurableLoopPolicy(policy_config)
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.TEST_FAILURE.value,
                       diff_summary="runtime/foo.py changed")
        ])

        escalation_needed = policy._check_escalation_triggers(ledger)
        assert escalation_needed is False

    def test_escalation_on_protected_path(self, policy_config):
        """Escalation required if protected path touched"""
        policy = ConfigurableLoopPolicy(policy_config)
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.TEST_FAILURE.value,
                       diff_summary="docs/01_governance/Constitution.md changed")
        ])

        escalation_needed = policy._check_escalation_triggers(ledger)
        assert escalation_needed is True

    def test_escalation_overrides_waiver(self, policy_config):
        """Escalation trigger overrides waiver eligibility"""
        policy = ConfigurableLoopPolicy(policy_config)
        # TEST_FAILURE is waiver-eligible, but touching protected path triggers escalation
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.TEST_FAILURE.value,
                       diff_summary="docs/00_foundations/file.md", diff_hash="h1"),
            MockAttempt("A2", success=False, failure_class=FailureClass.TEST_FAILURE.value,
                       diff_summary="docs/00_foundations/file.md", diff_hash="h2"),
            MockAttempt("A3", success=False, failure_class=FailureClass.TEST_FAILURE.value,
                       diff_summary="docs/00_foundations/file.md", diff_hash="h3")
        ])

        action, reason, override = policy.decide_next_action(ledger)

        assert action == "TERMINATE"
        assert override == "ESCALATION_REQUESTED"
        assert "escalation" in reason.lower() or "governance" in reason.lower()


class TestDeadlockOscillation:
    """Test deadlock and oscillation detection (Phase A logic preserved)"""

    def test_deadlock_detection(self, policy_config):
        """Identical diff hash triggers deadlock (NO_PROGRESS)"""
        policy = ConfigurableLoopPolicy(policy_config)
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h1"),
            MockAttempt("A2", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h1")
        ])

        action, reason, override = policy.decide_next_action(ledger)

        assert action == "TERMINATE"
        assert TerminalReason.NO_PROGRESS.value in reason

    def test_oscillation_detection(self, policy_config):
        """A -> B -> A pattern triggers oscillation"""
        policy = ConfigurableLoopPolicy(policy_config)
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h1"),
            MockAttempt("A2", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h2"),
            MockAttempt("A3", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash="h1")
        ])

        action, reason, override = policy.decide_next_action(ledger)

        assert action == "TERMINATE"
        assert TerminalReason.OSCILLATION_DETECTED.value in reason


class TestConfigDrivenRouting:
    """Test different routing behaviors from config"""

    def test_immediate_terminate_action(self, policy_config):
        """default_action=TERMINATE causes immediate termination"""
        policy = ConfigurableLoopPolicy(policy_config)
        # VALIDATION_ERROR has default_action=TERMINATE
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.VALIDATION_ERROR.value)
        ])

        action, reason, override = policy.decide_next_action(ledger)

        assert action == "TERMINATE"
        assert override == "BLOCKED"
        assert "immediate" in reason.lower() or "CRITICAL_FAILURE" in reason

    def test_retry_action_within_budget(self, policy_config):
        """default_action=RETRY allows retry within budget"""
        policy = ConfigurableLoopPolicy(policy_config)
        # REVIEW_REJECTION has default_action=RETRY, retry_limit=3
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.REVIEW_REJECTION.value, diff_hash="h1")
        ])

        action, reason, override = policy.decide_next_action(ledger)

        assert action == "RETRY"
        assert override is None


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_unknown_failure_class_string(self, policy_config):
        """Unknown failure class string treated as UNKNOWN"""
        policy = ConfigurableLoopPolicy(policy_config)
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class="invalid_class")
        ])

        action, reason, override = policy.decide_next_action(ledger)

        # UNKNOWN has retry_limit=0 and default_action=TERMINATE
        assert action == "TERMINATE"
        assert override == "BLOCKED"

    def test_empty_diff_hash_no_deadlock(self, policy_config):
        """Empty/None diff hashes don't trigger deadlock"""
        policy = ConfigurableLoopPolicy(policy_config)
        ledger = MockLedger([
            MockAttempt("A1", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash=None),
            MockAttempt("A2", success=False, failure_class=FailureClass.TEST_FAILURE.value, diff_hash=None)
        ])

        action, reason, override = policy.decide_next_action(ledger)

        # Should proceed with normal retry logic, not deadlock
        assert action == "RETRY"
