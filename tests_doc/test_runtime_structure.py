"""Tests for runtime structure validator."""
import tempfile
from pathlib import Path

import pytest

from doc_steward.runtime_structure_validator import check_runtime_structure


def test_runtime_structure_missing_required_subdir(tmp_path):
    """Test that missing required subdirectories are detected."""
    runtime_dir = tmp_path / "docs" / "03_runtime"
    runtime_dir.mkdir(parents=True)

    # Create only some required subdirs
    (runtime_dir / "fixpacks").mkdir()
    (runtime_dir / "policy").mkdir()
    (runtime_dir / "ARTEFACT_INDEX.json").write_text("{}")

    errors = check_runtime_structure(tmp_path)
    assert any("templates" in err for err in errors), \
        f"Should detect missing templates/, got: {errors}"
    assert any("archive" in err for err in errors), \
        f"Should detect missing archive/, got: {errors}"


def test_runtime_structure_missing_required_file(tmp_path):
    """Test that missing ARTEFACT_INDEX.json is detected."""
    runtime_dir = tmp_path / "docs" / "03_runtime"
    runtime_dir.mkdir(parents=True)

    # Create required subdirs but not the index file
    (runtime_dir / "fixpacks").mkdir()
    (runtime_dir / "policy").mkdir()
    (runtime_dir / "templates").mkdir()
    (runtime_dir / "archive").mkdir()

    errors = check_runtime_structure(tmp_path)
    assert any("ARTEFACT_INDEX.json" in err for err in errors), \
        f"Should detect missing ARTEFACT_INDEX.json, got: {errors}"


def test_runtime_structure_invalid_archive_subdir_name(tmp_path):
    """Test that invalid archive subdir names are detected."""
    runtime_dir = tmp_path / "docs" / "03_runtime"
    runtime_dir.mkdir(parents=True)

    # Create required structure
    (runtime_dir / "fixpacks").mkdir()
    (runtime_dir / "policy").mkdir()
    (runtime_dir / "templates").mkdir()
    (runtime_dir / "ARTEFACT_INDEX.json").write_text("{}")

    archive_dir = runtime_dir / "archive"
    archive_dir.mkdir()

    # Create invalid archive subdir name
    (archive_dir / "InvalidName").mkdir()
    (archive_dir / "InvalidName" / "README.md").write_text("test")

    errors = check_runtime_structure(tmp_path)
    assert any("InvalidName" in err and "must match" in err for err in errors), \
        f"Should detect invalid archive subdir name, got: {errors}"


def test_runtime_structure_archive_missing_readme(tmp_path):
    """Test that archive subdirs without README.md are detected."""
    runtime_dir = tmp_path / "docs" / "03_runtime"
    runtime_dir.mkdir(parents=True)

    # Create required structure
    (runtime_dir / "fixpacks").mkdir()
    (runtime_dir / "policy").mkdir()
    (runtime_dir / "templates").mkdir()
    (runtime_dir / "ARTEFACT_INDEX.json").write_text("{}")

    archive_dir = runtime_dir / "archive"
    archive_dir.mkdir()

    # Create valid-named archive subdir but no README
    (archive_dir / "2026-02-14_test").mkdir()

    errors = check_runtime_structure(tmp_path)
    assert any("README.md" in err and "2026-02-14_test" in err for err in errors), \
        f"Should detect missing README.md in archive subdir, got: {errors}"


def test_runtime_structure_archive_depth_exceeded(tmp_path):
    """Test that archive subdirs with nested subdirs are detected."""
    runtime_dir = tmp_path / "docs" / "03_runtime"
    runtime_dir.mkdir(parents=True)

    # Create required structure
    (runtime_dir / "fixpacks").mkdir()
    (runtime_dir / "policy").mkdir()
    (runtime_dir / "templates").mkdir()
    (runtime_dir / "ARTEFACT_INDEX.json").write_text("{}")

    archive_dir = runtime_dir / "archive"
    archive_dir.mkdir()

    # Create valid archive subdir with README
    dated_subdir = archive_dir / "2026-02_completed"
    dated_subdir.mkdir()
    (dated_subdir / "README.md").write_text("test")

    # Create nested subdir (exceeds max depth)
    (dated_subdir / "deeply_nested").mkdir()

    errors = check_runtime_structure(tmp_path)
    assert any("depth exceeds" in err and "deeply_nested" in err for err in errors), \
        f"Should detect archive depth violation, got: {errors}"


def test_runtime_structure_valid_minimal(tmp_path):
    """Test that a minimal valid structure passes."""
    runtime_dir = tmp_path / "docs" / "03_runtime"
    runtime_dir.mkdir(parents=True)

    # Create minimal required structure
    (runtime_dir / "fixpacks").mkdir()
    (runtime_dir / "policy").mkdir()
    (runtime_dir / "templates").mkdir()
    (runtime_dir / "ARTEFACT_INDEX.json").write_text('{"meta": {}, "artefacts": {}}')

    archive_dir = runtime_dir / "archive"
    archive_dir.mkdir()

    errors = check_runtime_structure(tmp_path)
    assert not errors, f"Minimal valid structure should pass, got: {errors}"
