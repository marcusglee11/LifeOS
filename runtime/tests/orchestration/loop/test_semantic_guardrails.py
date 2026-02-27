"""
Tests for SemanticGuardrails (B2-T02).

Tests load_guardrails_config() and check_diff() with:
- Valid config loads from real config/policy/semantic_guardrails.yaml (exercises F2)
- Missing config raises SemanticGuardrailsConfigError (fail-closed)
- Invalid YAML raises SemanticGuardrailsConfigError
- Missing required keys raises SemanticGuardrailsConfigError
- Trivial diff (below min lines) classified as not meaningful
- Meaningful diff with no flags
- Diff flagged for missing tests on new functions
- Diff flagged for excessive symbol renames
- Cross-concern flag fires on multi-extension diff
"""
from __future__ import annotations

import textwrap
import pytest
from pathlib import Path

from runtime.orchestration.loop.semantic_guardrails import (
    GuardrailsConfig,
    DiffStats,
    GuardrailResult,
    SemanticGuardrailsConfigError,
    check_diff,
    load_guardrails_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(**overrides: object) -> GuardrailsConfig:
    """Build a minimal valid GuardrailsConfig with optional overrides."""
    defaults = dict(
        min_line_change_for_semantic_review=5,
        max_symbol_renames_per_cycle=10,
        require_test_for_new_functions=True,
        require_test_for_deleted_functions=True,
        docstring_required_for_public_api=False,
        min_extensions_for_cross_concern=2,
        min_test_ratio_for_production_change=0.2,
    )
    defaults.update(overrides)
    return GuardrailsConfig(**defaults)


def _make_diff(**overrides: object) -> DiffStats:
    """Build a minimal DiffStats with optional overrides."""
    defaults = dict(
        total_lines_changed=20,
        test_lines_changed=5,
        symbol_renames=0,
        new_functions=0,
        deleted_functions=0,
        file_extensions=frozenset({".py"}),
    )
    defaults.update(overrides)
    return DiffStats(**defaults)


# ---------------------------------------------------------------------------
# Config loading tests
# ---------------------------------------------------------------------------

class TestLoadGuardrailsConfig:
    """Tests for load_guardrails_config()."""

    def test_loads_real_config(self) -> None:
        """
        Loads config/policy/semantic_guardrails.yaml — exercises F2 fix
        (config/** in default allowed_paths).
        """
        repo_root = Path(__file__).parents[4]  # runtime/tests/orchestration/loop -> repo root
        config_path = repo_root / "config" / "policy" / "semantic_guardrails.yaml"
        assert config_path.exists(), (
            f"F2 fix check: {config_path} not found. "
            "Either the file was not created or config/** is not in allowed_paths."
        )
        config = load_guardrails_config(config_path)
        assert config.min_line_change_for_semantic_review >= 0
        assert config.max_symbol_renames_per_cycle >= 0
        assert isinstance(config.require_test_for_new_functions, bool)
        assert isinstance(config.require_test_for_deleted_functions, bool)
        assert isinstance(config.docstring_required_for_public_api, bool)

    def test_missing_config_raises(self, tmp_path: Path) -> None:
        """Missing config file raises SemanticGuardrailsConfigError (fail-closed)."""
        with pytest.raises(SemanticGuardrailsConfigError, match="not found"):
            load_guardrails_config(tmp_path / "nonexistent.yaml")

    def test_invalid_yaml_raises(self, tmp_path: Path) -> None:
        """Corrupt YAML raises SemanticGuardrailsConfigError."""
        bad = tmp_path / "bad.yaml"
        bad.write_text("key: [unclosed")
        with pytest.raises(SemanticGuardrailsConfigError, match="Invalid YAML"):
            load_guardrails_config(bad)

    def test_missing_required_keys_raises(self, tmp_path: Path) -> None:
        """Config with missing required keys raises SemanticGuardrailsConfigError."""
        incomplete = tmp_path / "incomplete.yaml"
        incomplete.write_text("schema_version: '1.0'\nmin_line_change_for_semantic_review: 5\n")
        with pytest.raises(SemanticGuardrailsConfigError, match="Missing required keys"):
            load_guardrails_config(incomplete)

    def test_non_mapping_yaml_raises(self, tmp_path: Path) -> None:
        """YAML that is not a mapping raises SemanticGuardrailsConfigError."""
        bad = tmp_path / "list.yaml"
        bad.write_text("- item1\n- item2\n")
        with pytest.raises(SemanticGuardrailsConfigError, match="must be a YAML mapping"):
            load_guardrails_config(bad)

    def test_valid_minimal_config(self, tmp_path: Path) -> None:
        """Minimal valid YAML loads without error."""
        minimal = tmp_path / "minimal.yaml"
        minimal.write_text(textwrap.dedent("""\
            min_line_change_for_semantic_review: 5
            max_symbol_renames_per_cycle: 10
            require_test_for_new_functions: true
            require_test_for_deleted_functions: false
            docstring_required_for_public_api: false
        """))
        config = load_guardrails_config(minimal)
        assert config.min_line_change_for_semantic_review == 5
        assert config.max_symbol_renames_per_cycle == 10
        assert config.require_test_for_new_functions is True
        assert config.require_test_for_deleted_functions is False
        # Optional keys get defaults
        assert config.min_extensions_for_cross_concern == 2
        assert config.min_test_ratio_for_production_change == pytest.approx(0.2)

    def test_string_bool_values_are_rejected(self, tmp_path: Path) -> None:
        """Quoted boolean-like strings are rejected (strict bool required)."""
        bad_types = tmp_path / "bad_types.yaml"
        bad_types.write_text(textwrap.dedent("""\
            min_line_change_for_semantic_review: 5
            max_symbol_renames_per_cycle: 10
            require_test_for_new_functions: "false"
            require_test_for_deleted_functions: true
            docstring_required_for_public_api: false
        """))
        with pytest.raises(SemanticGuardrailsConfigError, match="must be bool"):
            load_guardrails_config(bad_types)

    def test_bool_for_integer_field_is_rejected(self, tmp_path: Path) -> None:
        """Boolean values are rejected for integer fields."""
        bad_types = tmp_path / "bool_for_int.yaml"
        bad_types.write_text(textwrap.dedent("""\
            min_line_change_for_semantic_review: true
            max_symbol_renames_per_cycle: 10
            require_test_for_new_functions: true
            require_test_for_deleted_functions: true
            docstring_required_for_public_api: false
        """))
        with pytest.raises(SemanticGuardrailsConfigError, match="must be int"):
            load_guardrails_config(bad_types)


# ---------------------------------------------------------------------------
# check_diff heuristic tests
# ---------------------------------------------------------------------------

class TestCheckDiff:
    """Tests for check_diff()."""

    def test_below_min_line_threshold_is_trivial(self) -> None:
        """Diff with fewer lines than min threshold → not meaningful."""
        config = _make_config(min_line_change_for_semantic_review=5)
        diff = _make_diff(total_lines_changed=4)
        result = check_diff(config, diff)
        assert result.meaningful is False
        assert result.reason == "below_min_line_threshold"

    def test_above_min_threshold_no_flags_is_meaningful(self) -> None:
        """Diff above threshold with no issues → meaningful, no flags."""
        config = _make_config()
        diff = _make_diff(
            total_lines_changed=20,
            test_lines_changed=5,
            symbol_renames=2,
            new_functions=0,
        )
        result = check_diff(config, diff)
        assert result.meaningful is True
        assert result.reason == "meaningful"
        assert len(result.flags) == 0

    def test_excessive_symbol_renames_flagged(self) -> None:
        """Symbol renames exceeding max → flag excessive_symbol_renames."""
        config = _make_config(max_symbol_renames_per_cycle=10)
        diff = _make_diff(symbol_renames=15, total_lines_changed=30)
        result = check_diff(config, diff)
        assert result.meaningful is True
        assert "excessive_symbol_renames" in result.flags

    def test_new_functions_without_tests_flagged(self) -> None:
        """New functions with low test ratio → missing_tests_for_new_functions."""
        config = _make_config(
            require_test_for_new_functions=True,
            min_test_ratio_for_production_change=0.2,
        )
        diff = _make_diff(
            total_lines_changed=50,
            test_lines_changed=0,  # 0% test coverage
            new_functions=2,
        )
        result = check_diff(config, diff)
        assert result.meaningful is True
        assert "missing_tests_for_new_functions" in result.flags

    def test_new_functions_with_sufficient_tests_not_flagged(self) -> None:
        """New functions with adequate test ratio → no flag."""
        config = _make_config(
            require_test_for_new_functions=True,
            min_test_ratio_for_production_change=0.2,
        )
        diff = _make_diff(
            total_lines_changed=50,
            test_lines_changed=15,  # 30% test coverage
            new_functions=2,
        )
        result = check_diff(config, diff)
        assert "missing_tests_for_new_functions" not in result.flags

    def test_deleted_functions_without_test_update_flagged(self) -> None:
        """Deleted functions with zero test lines → flag."""
        config = _make_config(require_test_for_deleted_functions=True)
        diff = _make_diff(
            total_lines_changed=20,
            test_lines_changed=0,
            deleted_functions=1,
        )
        result = check_diff(config, diff)
        assert "deleted_functions_without_test_update" in result.flags

    def test_cross_concern_diff_flagged(self) -> None:
        """Diff touching multiple file types → cross_concern_diff flag."""
        config = _make_config(min_extensions_for_cross_concern=2)
        diff = _make_diff(
            total_lines_changed=30,
            file_extensions=frozenset({".py", ".yaml", ".md"}),
        )
        result = check_diff(config, diff)
        assert "cross_concern_diff" in result.flags

    def test_single_extension_diff_not_cross_concern(self) -> None:
        """Diff with single file type → no cross_concern_diff flag."""
        config = _make_config(min_extensions_for_cross_concern=2)
        diff = _make_diff(
            total_lines_changed=30,
            file_extensions=frozenset({".py"}),
        )
        result = check_diff(config, diff)
        assert "cross_concern_diff" not in result.flags

    def test_multiple_flags_accumulate(self) -> None:
        """Multiple violations result in multiple flags in one result."""
        config = _make_config(
            max_symbol_renames_per_cycle=5,
            require_test_for_new_functions=True,
            min_test_ratio_for_production_change=0.2,
            min_extensions_for_cross_concern=2,
        )
        diff = _make_diff(
            total_lines_changed=40,
            test_lines_changed=0,
            symbol_renames=10,
            new_functions=3,
            file_extensions=frozenset({".py", ".yaml"}),
        )
        result = check_diff(config, diff)
        assert result.meaningful is True
        assert "excessive_symbol_renames" in result.flags
        assert "missing_tests_for_new_functions" in result.flags
        assert "cross_concern_diff" in result.flags

    def test_exactly_at_min_line_threshold_is_meaningful(self) -> None:
        """Diff exactly at threshold is meaningful (boundary condition)."""
        config = _make_config(min_line_change_for_semantic_review=5)
        diff = _make_diff(total_lines_changed=5)
        result = check_diff(config, diff)
        assert result.meaningful is True
