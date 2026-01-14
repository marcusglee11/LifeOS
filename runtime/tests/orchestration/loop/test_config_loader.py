"""
Unit tests for PolicyConfigLoader (Phase B.0)

Tests P0.1 (enum key normalization) and P0.2 (canonical hashing).
"""
import pytest
import tempfile
import hashlib
from pathlib import Path

from runtime.orchestration.loop.config_loader import PolicyConfigLoader, PolicyConfigError, PolicyConfig


# Valid config fixture (Phase B baseline)
VALID_CONFIG = """schema_version: "1.0"

policy_metadata:
  version: "phase_b_v1.0"
  effective_date: "2026-01-14"
  author: "COO"
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
  ineligible_failure_classes:
    - SYNTAX_ERROR
    - VALIDATION_ERROR
    - UNKNOWN
  escalation_triggers:
    - governance_surface_touched: true

progress_detection:
  no_progress_enabled: true
  no_progress_lookback: 1
  oscillation_enabled: true
  oscillation_lookback: 2
  cycle_detection_enabled: false
  cycle_lookback_max: 5

determinism:
  hash_algorithm: "sha256"
  hash_full_config: true
  policy_change_action: "ESCALATION_REQUESTED"
  policy_change_reason: "POLICY_CHANGED_MID_RUN"
"""


class TestConfigLoaderBasics:
    """Test basic loading and validation"""

    def test_valid_config_loads_successfully(self, tmp_path):
        """Valid config should load without errors"""
        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text(VALID_CONFIG, encoding='utf-8')

        loader = PolicyConfigLoader(config_file)
        config = loader.load()

        assert isinstance(config, PolicyConfig)
        assert config.schema_version == "1.0"
        assert config.policy_metadata["version"] == "phase_b_v1.0"
        assert config.budgets["max_attempts"] == 5
        assert "TEST_FAILURE" in config.failure_routing
        assert len(config.policy_hash_canonical) == 64  # SHA256 hex length
        assert len(config.policy_hash_bytes) == 64

    def test_missing_config_file_raises_error(self, tmp_path):
        """Missing config file should raise PolicyConfigError"""
        config_file = tmp_path / "nonexistent.yaml"

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match="not found"):
            loader.load()

    def test_invalid_yaml_raises_error(self, tmp_path):
        """Malformed YAML should raise PolicyConfigError"""
        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text("{ invalid yaml syntax: [", encoding='utf-8')

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match="YAML parsing failed"):
            loader.load()

    def test_invalid_schema_version_raises_error(self, tmp_path):
        """Unsupported schema version should raise PolicyConfigError"""
        invalid_config = VALID_CONFIG.replace('schema_version: "1.0"', 'schema_version: "2.0"')
        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text(invalid_config, encoding='utf-8')

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match="Unsupported schema version: 2.0"):
            loader.load()


class TestCanonicalHashing:
    """Test P0.2: Canonical hash computation (CRLF/LF-stable)"""

    def test_canonical_hash_crlf_vs_lf_identical(self, tmp_path):
        """CRLF and LF line endings should produce identical canonical hash"""
        # Create config with LF
        config_lf = tmp_path / "policy_lf.yaml"
        config_lf.write_text(VALID_CONFIG, encoding='utf-8')

        # Create config with CRLF
        config_crlf = tmp_path / "policy_crlf.yaml"
        crlf_content = VALID_CONFIG.replace('\n', '\r\n')
        config_crlf.write_text(crlf_content, encoding='utf-8', newline='')

        loader_lf = PolicyConfigLoader(config_lf)
        loader_crlf = PolicyConfigLoader(config_crlf)

        config_lf_obj = loader_lf.load()
        config_crlf_obj = loader_crlf.load()

        # Canonical hashes MUST be identical
        assert config_lf_obj.policy_hash_canonical == config_crlf_obj.policy_hash_canonical

        # Bytes hashes MAY differ (forensics)
        # (They should differ if the raw bytes are different)

    def test_canonical_hash_trailing_newline_normalized(self, tmp_path):
        """Configs with different trailing newlines should produce identical canonical hash"""
        # Config with one trailing newline
        config_one = tmp_path / "policy_one.yaml"
        config_one.write_text(VALID_CONFIG, encoding='utf-8')

        # Config with multiple trailing newlines
        config_multi = tmp_path / "policy_multi.yaml"
        config_multi.write_text(VALID_CONFIG + "\n\n\n", encoding='utf-8')

        # Config with no trailing newline
        config_none = tmp_path / "policy_none.yaml"
        config_none.write_text(VALID_CONFIG.rstrip('\n'), encoding='utf-8')

        loader_one = PolicyConfigLoader(config_one)
        loader_multi = PolicyConfigLoader(config_multi)
        loader_none = PolicyConfigLoader(config_none)

        hash_one = loader_one.load().policy_hash_canonical
        hash_multi = loader_multi.load().policy_hash_canonical
        hash_none = loader_none.load().policy_hash_canonical

        # All canonical hashes MUST be identical
        assert hash_one == hash_multi == hash_none

    def test_canonical_hash_changes_on_content_change(self, tmp_path):
        """Canonical hash should change when actual content changes"""
        config_orig = tmp_path / "policy_orig.yaml"
        config_orig.write_text(VALID_CONFIG, encoding='utf-8')

        # Modify content (change max_attempts)
        modified_config = VALID_CONFIG.replace("max_attempts: 5", "max_attempts: 10")
        config_mod = tmp_path / "policy_mod.yaml"
        config_mod.write_text(modified_config, encoding='utf-8')

        loader_orig = PolicyConfigLoader(config_orig)
        loader_mod = PolicyConfigLoader(config_mod)

        hash_orig = loader_orig.load().policy_hash_canonical
        hash_mod = loader_mod.load().policy_hash_canonical

        # Hashes MUST differ
        assert hash_orig != hash_mod


class TestEnumKeyNormalization:
    """Test P0.1: Enum MEMBER NAME validation (fail-closed)"""

    def test_value_form_key_rejected(self, tmp_path):
        """Value-form keys (e.g., 'test_failure') should be rejected"""
        invalid_config = VALID_CONFIG.replace(
            "TEST_FAILURE:",
            "test_failure:"  # Value form, INVALID
        )
        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text(invalid_config, encoding='utf-8')

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match="Invalid failure class key 'test_failure'"):
            loader.load()

    def test_mixed_case_key_rejected(self, tmp_path):
        """Mixed-case keys (e.g., 'Test_Failure') should be rejected"""
        invalid_config = VALID_CONFIG.replace(
            "TEST_FAILURE:",
            "Test_Failure:"  # Mixed case, INVALID
        )
        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text(invalid_config, encoding='utf-8')

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match="Invalid failure class key 'Test_Failure'"):
            loader.load()

    def test_unknown_failure_class_rejected(self, tmp_path):
        """Unknown failure class names should be rejected"""
        # Add a non-existent failure class
        invalid_config = VALID_CONFIG.replace(
            "failure_routing:",
            "failure_routing:\n  NONEXISTENT_CLASS:\n    default_action: \"RETRY\"\n"
        )
        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text(invalid_config, encoding='utf-8')

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match="Invalid failure class key 'NONEXISTENT_CLASS'"):
            loader.load()


class TestTotalityCheck:
    """Test P0.1: Routing table must be TOTAL (cover ALL failure classes)"""

    def test_incomplete_routing_rejected(self, tmp_path):
        """Routing table missing a failure class should be rejected"""
        # Remove UNKNOWN from routing
        incomplete_config = VALID_CONFIG
        lines = incomplete_config.split('\n')
        # Remove the UNKNOWN section (find and remove those lines)
        filtered_lines = []
        skip_next = False
        for line in lines:
            if line.strip().startswith("UNKNOWN:"):
                skip_next = True
                continue
            if skip_next:
                if line.strip().startswith("default_action:") or line.strip().startswith("terminal_"):
                    continue
                else:
                    skip_next = False
            filtered_lines.append(line)

        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text('\n'.join(filtered_lines), encoding='utf-8')

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match="Incomplete routing table. Missing entries for"):
            loader.load()


class TestRoutingValidation:
    """Test failure_routing validation"""

    def test_invalid_action_rejected(self, tmp_path):
        """Invalid default_action should be rejected"""
        invalid_config = VALID_CONFIG.replace(
            'default_action: "RETRY"',
            'default_action: "INVALID_ACTION"',
            1  # Only replace first occurrence
        )
        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text(invalid_config, encoding='utf-8')

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match="Invalid action.*Must be RETRY or TERMINATE"):
            loader.load()

    def test_terminate_without_outcome_rejected(self, tmp_path):
        """TERMINATE action without terminal_outcome should be rejected"""
        invalid_config = VALID_CONFIG.replace(
            """  SYNTAX_ERROR:
    default_action: "TERMINATE"
    terminal_outcome: "BLOCKED"
    terminal_reason: "CRITICAL_FAILURE"
  TIMEOUT:""",
            """  SYNTAX_ERROR:
    default_action: "TERMINATE"
  TIMEOUT:"""
        )
        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text(invalid_config, encoding='utf-8')

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match="TERMINATE action requires 'terminal_outcome'"):
            loader.load()

    def test_invalid_terminal_outcome_rejected(self, tmp_path):
        """Invalid terminal_outcome should be rejected"""
        invalid_config = VALID_CONFIG.replace(
            'terminal_outcome: "BLOCKED"',
            'terminal_outcome: "INVALID_OUTCOME"',
            1
        )
        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text(invalid_config, encoding='utf-8')

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match="Invalid terminal_outcome"):
            loader.load()


class TestRequiredSections:
    """Test required sections validation"""

    @pytest.mark.parametrize("missing_section", [
        "policy_metadata",
        "budgets",
        "failure_routing",
        "waiver_rules",
        "progress_detection",
        "determinism"
    ])
    def test_missing_required_section_rejected(self, tmp_path, missing_section):
        """Each required section must be present"""
        # Remove the section
        lines = VALID_CONFIG.split('\n')
        filtered_lines = []
        skip_section = False
        for line in lines:
            if line.strip().startswith(f"{missing_section}:"):
                skip_section = True
                continue
            if skip_section:
                # Skip until we hit a non-indented line (next section)
                if line and not line[0].isspace():
                    skip_section = False
                else:
                    continue
            filtered_lines.append(line)

        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text('\n'.join(filtered_lines), encoding='utf-8')

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match=f"Missing required section: {missing_section}"):
            loader.load()


class TestBudgetValidation:
    """Test budget validation"""

    def test_negative_retry_limit_rejected(self, tmp_path):
        """Negative retry limits should be rejected"""
        invalid_config = VALID_CONFIG.replace(
            "TEST_FAILURE: 3",
            "TEST_FAILURE: -1"
        )
        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text(invalid_config, encoding='utf-8')

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match="must be non-negative"):
            loader.load()

    def test_non_integer_retry_limit_rejected(self, tmp_path):
        """Non-integer retry limits should be rejected"""
        invalid_config = VALID_CONFIG.replace(
            "TEST_FAILURE: 3",
            "TEST_FAILURE: 3.5"
        )
        config_file = tmp_path / "policy_v1.0.yaml"
        config_file.write_text(invalid_config, encoding='utf-8')

        loader = PolicyConfigLoader(config_file)

        with pytest.raises(PolicyConfigError, match="must be an integer"):
            loader.load()


# Summary: 17 tests covering all P0.1/P0.2 requirements
