"""Tests for protocols structure validator."""
import tempfile
from pathlib import Path

import pytest

from doc_steward.protocols_structure_validator import check_protocols_structure


def test_protocols_structure_missing_required_subdir(tmp_path):
    """Test that missing required subdirectories are detected."""
    protocols_dir = tmp_path / "docs" / "02_protocols"
    protocols_dir.mkdir(parents=True)

    # Create only some required subdirs
    (protocols_dir / "templates").mkdir()
    (protocols_dir / "ARTEFACT_INDEX.json").write_text("{}")

    errors = check_protocols_structure(tmp_path)
    assert any("schemas" in err for err in errors), \
        f"Should detect missing schemas/, got: {errors}"
    assert any("archive" in err for err in errors), \
        f"Should detect missing archive/, got: {errors}"


def test_protocols_structure_missing_required_file(tmp_path):
    """Test that missing ARTEFACT_INDEX.json is detected."""
    protocols_dir = tmp_path / "docs" / "02_protocols"
    protocols_dir.mkdir(parents=True)

    # Create required subdirs but not the index file
    (protocols_dir / "templates").mkdir()
    (protocols_dir / "schemas").mkdir()
    (protocols_dir / "archive").mkdir()

    errors = check_protocols_structure(tmp_path)
    assert any("ARTEFACT_INDEX.json" in err for err in errors), \
        f"Should detect missing ARTEFACT_INDEX.json, got: {errors}"


def test_protocols_structure_invalid_archive_subdir_name(tmp_path):
    """Test that invalid archive subdir names are detected."""
    protocols_dir = tmp_path / "docs" / "02_protocols"
    protocols_dir.mkdir(parents=True)

    # Create required structure
    (protocols_dir / "templates").mkdir()
    (protocols_dir / "schemas").mkdir()
    (protocols_dir / "ARTEFACT_INDEX.json").write_text("{}")

    archive_dir = protocols_dir / "archive"
    archive_dir.mkdir()

    # Create invalid archive subdir name
    (archive_dir / "bad-name-format").mkdir()
    (archive_dir / "bad-name-format" / "README.md").write_text("test")

    errors = check_protocols_structure(tmp_path)
    assert any("bad-name-format" in err and "must match" in err for err in errors), \
        f"Should detect invalid archive subdir name, got: {errors}"


def test_protocols_structure_archive_missing_readme(tmp_path):
    """Test that archive subdirs without README.md are detected."""
    protocols_dir = tmp_path / "docs" / "02_protocols"
    protocols_dir.mkdir(parents=True)

    # Create required structure
    (protocols_dir / "templates").mkdir()
    (protocols_dir / "schemas").mkdir()
    (protocols_dir / "ARTEFACT_INDEX.json").write_text("{}")

    archive_dir = protocols_dir / "archive"
    archive_dir.mkdir()

    # Create valid-named archive subdir but no README
    (archive_dir / "2026-02_test").mkdir()

    errors = check_protocols_structure(tmp_path)
    assert any("README.md" in err and "2026-02_test" in err for err in errors), \
        f"Should detect missing README.md in archive subdir, got: {errors}"


def test_protocols_structure_archive_depth_exceeded(tmp_path):
    """Test that archive subdirs with nested subdirs are detected."""
    protocols_dir = tmp_path / "docs" / "02_protocols"
    protocols_dir.mkdir(parents=True)

    # Create required structure
    (protocols_dir / "templates").mkdir()
    (protocols_dir / "schemas").mkdir()
    (protocols_dir / "ARTEFACT_INDEX.json").write_text("{}")

    archive_dir = protocols_dir / "archive"
    archive_dir.mkdir()

    # Create valid archive subdir with README
    dated_subdir = archive_dir / "2026-02_test"
    dated_subdir.mkdir()
    (dated_subdir / "README.md").write_text("test")

    # Create nested subdir (exceeds max depth)
    (dated_subdir / "nested").mkdir()

    errors = check_protocols_structure(tmp_path)
    assert any("depth exceeds" in err and "nested" in err for err in errors), \
        f"Should detect archive depth violation, got: {errors}"


def test_protocols_structure_valid_minimal(tmp_path):
    """Test that a minimal valid structure passes."""
    protocols_dir = tmp_path / "docs" / "02_protocols"
    protocols_dir.mkdir(parents=True)

    # Create minimal required structure
    (protocols_dir / "templates").mkdir()
    (protocols_dir / "schemas").mkdir()
    (protocols_dir / "ARTEFACT_INDEX.json").write_text('{"meta": {}, "artefacts": {}}')

    archive_dir = protocols_dir / "archive"
    archive_dir.mkdir()

    errors = check_protocols_structure(tmp_path)
    assert not errors, f"Minimal valid structure should pass, got: {errors}"


def test_protocols_structure_unexpected_subdir(tmp_path):
    """Test that unexpected subdirectories are NOT reported as structure errors.

    Note: Unexpected subdirs are allowed; only missing required subdirs are errors.
    Root file allowance is index-centric (enforced by artefact_index_validator).
    """
    protocols_dir = tmp_path / "docs" / "02_protocols"
    protocols_dir.mkdir(parents=True)

    # Create required structure
    (protocols_dir / "templates").mkdir()
    (protocols_dir / "schemas").mkdir()
    (protocols_dir / "archive").mkdir()
    (protocols_dir / "ARTEFACT_INDEX.json").write_text('{"meta": {}, "artefacts": {}}')

    # Add unexpected subdir
    (protocols_dir / "unexpected_dir").mkdir()

    errors = check_protocols_structure(tmp_path)
    # Structure validator only checks for required dirs and archive structure
    # Unexpected subdirs are not structure violations per §8.1
    assert not errors, f"Unexpected subdir should not cause structure error, got: {errors}"
