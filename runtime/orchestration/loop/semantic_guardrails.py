"""
Semantic Guardrails - Heuristic classifier for meaningful vs. trivial changes.

Loads thresholds from config/policy/semantic_guardrails.yaml and applies
heuristic checks to determine whether a code diff is semantically meaningful
or trivial. Used by the build loop to flag questionable diffs for extra review.

Fail-closed: missing or corrupt config raises SemanticGuardrailsConfigError.
Never silently passes on config failure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional
import yaml


class SemanticGuardrailsConfigError(Exception):
    """Raised when the guardrails config is missing, unreadable, or invalid."""


@dataclass(frozen=True)
class GuardrailsConfig:
    """Loaded and validated semantic guardrails configuration."""

    min_line_change_for_semantic_review: int
    max_symbol_renames_per_cycle: int
    require_test_for_new_functions: bool
    require_test_for_deleted_functions: bool
    docstring_required_for_public_api: bool
    min_extensions_for_cross_concern: int
    min_test_ratio_for_production_change: float

    def __post_init__(self) -> None:
        if self.min_line_change_for_semantic_review < 0:
            raise ValueError("min_line_change_for_semantic_review must be non-negative")
        if self.max_symbol_renames_per_cycle < 0:
            raise ValueError("max_symbol_renames_per_cycle must be non-negative")
        if not (0.0 <= self.min_test_ratio_for_production_change <= 1.0):
            raise ValueError("min_test_ratio_for_production_change must be in [0.0, 1.0]")


@dataclass(frozen=True)
class DiffStats:
    """Statistics describing a code diff."""

    total_lines_changed: int
    test_lines_changed: int
    symbol_renames: int
    new_functions: int
    deleted_functions: int
    file_extensions: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class GuardrailResult:
    """Result of a semantic guardrail check."""

    meaningful: bool
    reason: str
    flags: tuple[str, ...] = field(default_factory=tuple)


_REQUIRED_KEYS = {
    "min_line_change_for_semantic_review": int,
    "max_symbol_renames_per_cycle": int,
    "require_test_for_new_functions": bool,
    "require_test_for_deleted_functions": bool,
    "docstring_required_for_public_api": bool,
}

_OPTIONAL_KEYS_WITH_DEFAULTS: dict[str, Any] = {
    "min_extensions_for_cross_concern": 2,
    "min_test_ratio_for_production_change": 0.2,
}


def load_guardrails_config(config_path: Path) -> GuardrailsConfig:
    """
    Load semantic guardrails config from YAML.

    Args:
        config_path: Path to the semantic_guardrails.yaml file.

    Returns:
        GuardrailsConfig with validated values.

    Raises:
        SemanticGuardrailsConfigError: If file missing, unreadable, or invalid.
    """
    if not config_path.exists():
        raise SemanticGuardrailsConfigError(
            f"Semantic guardrails config not found: {config_path}"
        )

    try:
        with open(config_path, "r") as f:
            raw = yaml.safe_load(f)
    except OSError as e:
        raise SemanticGuardrailsConfigError(
            f"Failed to read guardrails config: {e}"
        ) from e
    except yaml.YAMLError as e:
        raise SemanticGuardrailsConfigError(
            f"Invalid YAML in guardrails config: {e}"
        ) from e

    if not isinstance(raw, dict):
        raise SemanticGuardrailsConfigError(
            f"Guardrails config must be a YAML mapping, got: {type(raw).__name__}"
        )

    missing = [k for k in _REQUIRED_KEYS if k not in raw]
    if missing:
        raise SemanticGuardrailsConfigError(
            f"Missing required keys in guardrails config: {sorted(missing)}"
        )

    try:
        return GuardrailsConfig(
            min_line_change_for_semantic_review=int(raw["min_line_change_for_semantic_review"]),
            max_symbol_renames_per_cycle=int(raw["max_symbol_renames_per_cycle"]),
            require_test_for_new_functions=bool(raw["require_test_for_new_functions"]),
            require_test_for_deleted_functions=bool(raw["require_test_for_deleted_functions"]),
            docstring_required_for_public_api=bool(raw["docstring_required_for_public_api"]),
            min_extensions_for_cross_concern=int(
                raw.get("min_extensions_for_cross_concern",
                        _OPTIONAL_KEYS_WITH_DEFAULTS["min_extensions_for_cross_concern"])
            ),
            min_test_ratio_for_production_change=float(
                raw.get("min_test_ratio_for_production_change",
                        _OPTIONAL_KEYS_WITH_DEFAULTS["min_test_ratio_for_production_change"])
            ),
        )
    except (ValueError, TypeError) as e:
        raise SemanticGuardrailsConfigError(
            f"Invalid value in guardrails config: {e}"
        ) from e


def check_diff(config: GuardrailsConfig, diff: DiffStats) -> GuardrailResult:
    """
    Apply heuristic guardrail checks to a diff.

    Args:
        config: Loaded guardrails configuration.
        diff: Statistics about the diff to evaluate.

    Returns:
        GuardrailResult indicating whether the diff is meaningful.
    """
    flags: list[str] = []

    # Trivial if below minimum line threshold
    if diff.total_lines_changed < config.min_line_change_for_semantic_review:
        return GuardrailResult(
            meaningful=False,
            reason="below_min_line_threshold",
            flags=tuple(flags),
        )

    # Flag excessive symbol renames
    if diff.symbol_renames > config.max_symbol_renames_per_cycle:
        flags.append("excessive_symbol_renames")

    # Flag missing tests for new functions
    if config.require_test_for_new_functions and diff.new_functions > 0:
        test_ratio = (
            diff.test_lines_changed / diff.total_lines_changed
            if diff.total_lines_changed > 0 else 0.0
        )
        if test_ratio < config.min_test_ratio_for_production_change:
            flags.append("missing_tests_for_new_functions")

    # Flag missing test removal for deleted functions
    if config.require_test_for_deleted_functions and diff.deleted_functions > 0:
        if diff.test_lines_changed == 0:
            flags.append("deleted_functions_without_test_update")

    # Cross-concern flag (informational)
    if len(diff.file_extensions) >= config.min_extensions_for_cross_concern:
        flags.append("cross_concern_diff")

    reason = "meaningful_with_flags" if flags else "meaningful"
    return GuardrailResult(
        meaningful=True,
        reason=reason,
        flags=tuple(flags),
    )
