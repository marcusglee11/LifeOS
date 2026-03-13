"""Regression tests for scripts/generate_repo_map.py."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure repo root is importable
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from generate_repo_map import (
    GENERATOR_VERSION,
    _is_boilerplate_docstring,
    compute_stats,
    generate_repo_map,
    scan_dependency_edges,
    scan_runtime_packages,
    scan_source_test_mapping,
    scan_top_level_dirs,
)

FIXED_TS = "2026-01-01T00:00:00Z"


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


def test_determinism_with_fixed_timestamp() -> None:
    """Same repo state + same timestamp → byte-identical output."""
    out1 = generate_repo_map(REPO_ROOT, generated_at=FIXED_TS)
    out2 = generate_repo_map(REPO_ROOT, generated_at=FIXED_TS)
    assert out1 == out2, "Output must be byte-identical for same inputs"


# ---------------------------------------------------------------------------
# Header / provenance
# ---------------------------------------------------------------------------


def test_header_contains_required_fields() -> None:
    content = generate_repo_map(REPO_ROOT, generated_at=FIXED_TS)
    assert f"generator_version: {GENERATOR_VERSION}" in content
    assert "generated_from_ref:" in content
    assert "working_tree_dirty:" in content
    assert "generated_at:" in content
    assert "scan_scope:" in content
    assert "exclusions:" in content


def test_generated_at_is_injected_value() -> None:
    content = generate_repo_map(REPO_ROOT, generated_at=FIXED_TS)
    assert f"generated_at: {FIXED_TS}" in content


def test_working_tree_dirty_is_boolean_string() -> None:
    content = generate_repo_map(REPO_ROOT, generated_at=FIXED_TS)
    assert "working_tree_dirty: true" in content or "working_tree_dirty: false" in content


# ---------------------------------------------------------------------------
# Module coverage
# ---------------------------------------------------------------------------


def test_all_runtime_packages_covered() -> None:
    """Every runtime subdir with __init__.py appears in the inventory."""
    runtime_dir = REPO_ROOT / "runtime"
    expected_packages = set()
    for entry in runtime_dir.iterdir():
        if entry.is_dir() and (entry / "__init__.py").exists():
            name = entry.name
            if name not in ("__pycache__", "tests"):
                expected_packages.add(name)

    packages = scan_runtime_packages(REPO_ROOT, {})
    found = {p["name"] for p in packages if p["name"] != "tests"}

    missing = expected_packages - found
    assert not missing, f"Packages missing from inventory: {missing}"


def test_no_tests_package_in_inventory() -> None:
    """The 'tests' package should not appear as a runtime module."""
    content = generate_repo_map(REPO_ROOT, generated_at=FIXED_TS)
    assert "### runtime/tests/" not in content


# ---------------------------------------------------------------------------
# Output bounds
# ---------------------------------------------------------------------------


def test_output_is_non_empty() -> None:
    content = generate_repo_map(REPO_ROOT, generated_at=FIXED_TS)
    assert len(content) > 100


def test_output_line_count_within_target() -> None:
    """Output should be roughly 200-400 lines (design target, not hard gate)."""
    content = generate_repo_map(REPO_ROOT, generated_at=FIXED_TS)
    line_count = content.count("\n")
    # Allow some tolerance — this is a design target
    assert 100 < line_count < 600, f"Line count {line_count} outside expected range"


# ---------------------------------------------------------------------------
# Override precedence
# ---------------------------------------------------------------------------


def test_override_beats_docstring() -> None:
    """A curated override must replace the __init__.py docstring."""
    overrides = {"runtime/util": "Custom override purpose"}
    packages = scan_runtime_packages(REPO_ROOT, overrides)
    util_pkg = next((p for p in packages if p["name"] == "util"), None)
    assert util_pkg is not None
    assert util_pkg["purpose"] == "Custom override purpose"


def test_no_override_uses_docstring() -> None:
    """Without an override, purpose comes from docstring or dominant module."""
    packages = scan_runtime_packages(REPO_ROOT, {})
    # orchestration has a clear __init__.py docstring
    orch_pkg = next((p for p in packages if p["name"] == "orchestration"), None)
    assert orch_pkg is not None
    assert orch_pkg["purpose"] != "UNDOCUMENTED"


# ---------------------------------------------------------------------------
# Boilerplate detection
# ---------------------------------------------------------------------------


def test_boilerplate_docstring_detected() -> None:
    assert _is_boilerplate_docstring("runtime.amu0 package")
    assert _is_boilerplate_docstring("runtime.api package.")
    assert not _is_boilerplate_docstring("Validator suite v2.1a core package")
    assert not _is_boilerplate_docstring("Runtime Governance Package")


# ---------------------------------------------------------------------------
# Source-to-test mapping
# ---------------------------------------------------------------------------


def test_test_mappings_point_to_existing_paths() -> None:
    """Every emitted test mapping must reference an existing path."""
    packages = scan_runtime_packages(REPO_ROOT, {})
    mappings = scan_source_test_mapping(REPO_ROOT, packages)

    for m in mappings:
        test_paths = m["tests"].split()
        for tp in test_paths:
            full = REPO_ROOT / tp
            assert full.exists(), f"Test mapping target does not exist: {tp}"


# ---------------------------------------------------------------------------
# Dependency edges
# ---------------------------------------------------------------------------


def test_dependency_edges_are_internal_only() -> None:
    """All edges must be between runtime.* packages."""
    packages = scan_runtime_packages(REPO_ROOT, {})
    edges = scan_dependency_edges(REPO_ROOT, packages)

    for from_pkg, to_pkg in edges:
        assert from_pkg.startswith("runtime."), f"Non-runtime source: {from_pkg}"
        assert to_pkg.startswith("runtime."), f"Non-runtime target: {to_pkg}"


def test_dependency_edges_no_self_loops() -> None:
    """No package should depend on itself."""
    packages = scan_runtime_packages(REPO_ROOT, {})
    edges = scan_dependency_edges(REPO_ROOT, packages)

    for from_pkg, to_pkg in edges:
        assert from_pkg != to_pkg, f"Self-loop: {from_pkg}"


def test_dependency_edges_are_sorted() -> None:
    """Edges must be in sorted order for determinism."""
    packages = scan_runtime_packages(REPO_ROOT, {})
    edges = scan_dependency_edges(REPO_ROOT, packages)
    assert edges == sorted(edges)


def test_stats_exclude_tests_package() -> None:
    """compute_stats must not count the tests package in file/line totals."""
    packages = scan_runtime_packages(REPO_ROOT, {})
    stats = compute_stats(packages)

    tests_pkg = next((p for p in packages if p["name"] == "tests"), None)
    assert tests_pkg is not None, "tests package must exist in scan output"

    # Stats totals must not include the tests package
    non_test_files = sum(p["file_count"] for p in packages if p["name"] != "tests")
    non_test_lines = sum(p["line_count"] for p in packages if p["name"] != "tests")
    assert stats["total_files"] == non_test_files
    assert stats["total_lines"] == non_test_lines
    assert stats["total_packages"] == len([p for p in packages if p["name"] != "tests"])
