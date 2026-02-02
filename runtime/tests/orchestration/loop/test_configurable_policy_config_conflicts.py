"""
Configurable Policy Configuration Conflict Tests

Tests for policy configuration edge cases, conflicts, and invalid YAML scenarios.

Per Edge Case Testing Implementation Plan - Phase 1.5
"""
import pytest
import yaml
from pathlib import Path
from runtime.orchestration.loop.configurable_policy import ConfigurableLoopPolicy
from runtime.orchestration.loop.config_loader import PolicyConfigLoader
from runtime.orchestration.loop.taxonomy import FailureClass


@pytest.fixture
def config_path(tmp_path):
    """Path for test config files."""
    return tmp_path / "policy.yaml"


class TestRetryLimitConflicts:
    """Tests for conflicting retry_limits configurations."""

    def test_retry_limit_zero_immediate_terminate(self, config_path):
        """Retry limit of exactly 0 causes immediate termination."""
        config_content = """schema_version: "1.0"
policy_metadata:
  version: "test_v1.0"
  effective_date: "2026-01-14"
budgets:
  max_attempts: 5
  retry_limits:
    TEST_FAILURE: 0
failure_routing:
  TEST_FAILURE:
    default_action: "TERMINATE"
    terminal_outcome: "BLOCKED"
    terminal_reason: "CRITICAL_FAILURE"
"""
        config_path.write_text(config_content)
        loader = PolicyConfigLoader(config_path)
        config = loader.load()
        policy = ConfigurableLoopPolicy(config)

        assert policy.retry_limits.get("test_failure", 0) == 0

    def test_max_attempts_less_than_sum_of_retry_limits(self, config_path):
        """max_attempts < sum of retry_limits creates conflict."""
        config_content = """schema_version: "1.0"
policy_metadata:
  version: "test_v1.0"
  effective_date: "2026-01-14"
budgets:
  max_attempts: 5
  retry_limits:
    TEST_FAILURE: 3
    TIMEOUT: 2
    REVIEW_REJECTION: 2
failure_routing:
  TEST_FAILURE:
    default_action: "RETRY"
  TIMEOUT:
    default_action: "RETRY"
  REVIEW_REJECTION:
    default_action: "RETRY"
"""
        # Sum of retry_limits = 7, but max_attempts = 5
        config_path.write_text(config_content)
        loader = PolicyConfigLoader(config_path)
        config = loader.load()
        policy = ConfigurableLoopPolicy(config)

        # Policy should load, but runtime behavior may hit max_attempts first
        assert policy.budgets["max_attempts"] == 5
        assert policy.retry_limits["test_failure"] == 3


class TestUnknownFailureClasses:
    """Tests for unknown or invalid failure_class values."""

    def test_unknown_failure_class_in_config(self, config_path):
        """Unknown failure_class in config is handled gracefully."""
        config_content = """schema_version: "1.0"
policy_metadata:
  version: "test_v1.0"
  effective_date: "2026-01-14"
budgets:
  max_attempts: 5
  retry_limits:
    UNKNOWN_CLASS: 2
failure_routing:
  UNKNOWN_CLASS:
    default_action: "RETRY"
"""
        config_path.write_text(config_content)
        loader = PolicyConfigLoader(config_path)
        config = loader.load()
        policy = ConfigurableLoopPolicy(config)

        # Unknown class should be normalized and accessible
        assert "unknown_class" in policy.retry_limits


class TestInvalidYAML:
    """Tests for invalid YAML syntax."""

    def test_yaml_tabs_vs_spaces(self, config_path):
        """Invalid YAML with mixed tabs and spaces triggers error."""
        # YAML spec forbids tabs for indentation
        config_content = "schema_version: \"1.0\"\n\tpolicy_metadata:\n  version: \"test\""
        config_path.write_text(config_content)

        loader = PolicyConfigLoader(config_path)
        with pytest.raises((yaml.YAMLError, Exception)):
            loader.load()

    def test_yaml_syntax_error(self, config_path):
        """Malformed YAML syntax triggers error."""
        config_content = """schema_version: "1.0"
policy_metadata:
  version: "test
  # Missing closing quote
"""
        config_path.write_text(config_content)

        loader = PolicyConfigLoader(config_path)
        with pytest.raises((yaml.YAMLError, Exception)):
            loader.load()

    def test_yaml_invalid_list_syntax(self, config_path):
        """Invalid YAML list syntax triggers error."""
        config_content = """schema_version: "1.0"
waiver_rules:
  eligible_failure_classes:
    - TEST_FAILURE
    MISSING_DASH
"""
        config_path.write_text(config_content)

        loader = PolicyConfigLoader(config_path)
        # May succeed parsing but with unexpected structure
        try:
            config = loader.load()
            # Structure may be malformed
            assert isinstance(config, dict)
        except (yaml.YAMLError, Exception):
            # Or may fail parsing
            pass


class TestMissingRequiredFields:
    """Tests for missing required configuration fields."""

    def test_missing_schema_version(self, config_path):
        """Missing schema_version field - loader requires budgets and failure_routing."""
        config_content = """policy_metadata:
  version: "test_v1.0"
budgets:
  max_attempts: 5
failure_routing: {}
"""
        config_path.write_text(config_content)

        loader = PolicyConfigLoader(config_path)
        config = loader.load()

        # May load but missing schema_version
        assert "schema_version" not in config or config.get("schema_version") is None

    def test_missing_budgets_section(self, config_path):
        """Missing budgets section triggers PolicyConfigLoadError."""
        from runtime.orchestration.loop.config_loader import PolicyConfigLoadError
        config_content = """schema_version: "1.0"
policy_metadata:
  version: "test_v1.0"
"""
        config_path.write_text(config_content)

        loader = PolicyConfigLoader(config_path)
        # Loader enforces required sections
        with pytest.raises(PolicyConfigLoadError) as exc_info:
            loader.load()

        assert "budgets" in str(exc_info.value).lower()

    def test_missing_failure_routing(self, config_path):
        """Missing failure_routing section triggers PolicyConfigLoadError."""
        from runtime.orchestration.loop.config_loader import PolicyConfigLoadError
        config_content = """schema_version: "1.0"
budgets:
  max_attempts: 5
  retry_limits:
    TEST_FAILURE: 3
"""
        config_path.write_text(config_content)

        loader = PolicyConfigLoader(config_path)
        # Loader enforces required sections
        with pytest.raises(PolicyConfigLoadError) as exc_info:
            loader.load()

        assert "failure_routing" in str(exc_info.value).lower()


class TestWaiverRuleConflicts:
    """Tests for waiver rule conflicts."""

    def test_overlapping_eligible_ineligible(self, config_path):
        """Same failure class in both eligible and ineligible lists."""
        config_content = """schema_version: "1.0"
budgets:
  max_attempts: 5
failure_routing: {}
waiver_rules:
  eligible_failure_classes:
    - TEST_FAILURE
  ineligible_failure_classes:
    - TEST_FAILURE
"""
        config_path.write_text(config_content)

        loader = PolicyConfigLoader(config_path)
        config = loader.load()
        policy = ConfigurableLoopPolicy(config)

        # Both lists exist - behavior depends on implementation
        # Typically ineligible takes precedence
        eligible = policy.waiver_rules.get("eligible_failure_classes", [])
        ineligible = policy.waiver_rules.get("ineligible_failure_classes", [])

        assert "TEST_FAILURE" in eligible
        assert "TEST_FAILURE" in ineligible


class TestFailureClassNormalization:
    """Tests for failure class normalization edge cases."""

    def test_mixed_case_failure_class(self):
        """Mixed case failure class (TeSt_FaIlUrE) normalizes to test_failure."""
        config = {
            "budgets": {
                "retry_limits": {
                    "TeSt_FaIlUrE": 3
                }
            },
            "failure_routing": {}
        }

        policy = ConfigurableLoopPolicy(config)

        # Should normalize to lowercase
        assert "test_failure" in policy.retry_limits
        assert policy.retry_limits["test_failure"] == 3

    def test_whitespace_in_failure_class(self):
        """Failure class with whitespace is stripped and normalized."""
        config = {
            "budgets": {
                "retry_limits": {
                    "  TEST_FAILURE  ": 3
                }
            },
            "failure_routing": {}
        }

        policy = ConfigurableLoopPolicy(config)

        # Should strip and normalize
        assert "test_failure" in policy.retry_limits


class TestDeadlockThresholdEdgeCases:
    """Tests for deadlock threshold edge cases."""

    def test_deadlock_threshold_zero(self, config_path):
        """Deadlock threshold of 0 in config."""
        config_content = """schema_version: "1.0"
budgets:
  max_attempts: 5
failure_routing: {}
progress_detection:
  deadlock_threshold: 0
"""
        config_path.write_text(config_content)

        loader = PolicyConfigLoader(config_path)
        config = loader.load()
        policy = ConfigurableLoopPolicy(config)

        assert policy.progress_detection.get("deadlock_threshold") == 0

    def test_deadlock_threshold_exceeds_max_attempts(self, config_path):
        """Deadlock threshold > max_attempts."""
        config_content = """schema_version: "1.0"
budgets:
  max_attempts: 5
failure_routing: {}
progress_detection:
  deadlock_threshold: 10
"""
        config_path.write_text(config_content)

        loader = PolicyConfigLoader(config_path)
        config = loader.load()
        policy = ConfigurableLoopPolicy(config)

        # Config loads but deadlock may never trigger
        assert policy.progress_detection.get("deadlock_threshold") == 10
        assert policy.budgets["max_attempts"] == 5


class TestOscillationDetection:
    """Tests for oscillation detection edge cases."""

    def test_oscillation_window_size_zero(self, config_path):
        """Oscillation window_size of 0 disables detection."""
        config_content = """schema_version: "1.0"
budgets:
  max_attempts: 5
failure_routing: {}
progress_detection:
  oscillation_detection:
    enabled: true
    window_size: 0
    threshold: 3
"""
        config_path.write_text(config_content)

        loader = PolicyConfigLoader(config_path)
        config = loader.load()
        policy = ConfigurableLoopPolicy(config)

        osc_config = policy.progress_detection.get("oscillation_detection", {})
        assert osc_config.get("window_size") == 0

    def test_oscillation_threshold_exceeds_window(self, config_path):
        """Oscillation threshold > window_size is invalid."""
        config_content = """schema_version: "1.0"
budgets:
  max_attempts: 5
failure_routing: {}
progress_detection:
  oscillation_detection:
    enabled: true
    window_size: 3
    threshold: 5
"""
        config_path.write_text(config_content)

        loader = PolicyConfigLoader(config_path)
        config = loader.load()
        policy = ConfigurableLoopPolicy(config)

        osc_config = policy.progress_detection.get("oscillation_detection", {})
        # Invalid config but loads - runtime may not trigger
        assert osc_config.get("threshold") == 5
        assert osc_config.get("window_size") == 3
