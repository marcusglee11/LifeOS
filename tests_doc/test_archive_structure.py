"""Tests for archive structure validator."""
import tempfile
from pathlib import Path

import pytest

from doc_steward.archive_structure_validator import check_archive_structure


def test_archive_structure_no_99_archive_is_ok(tmp_path):
    """Test that missing docs/99_archive/ is not an error (optional)."""
    errors = check_archive_structure(tmp_path)
    assert not errors, f"Missing 99_archive should not be an error, got: {errors}"


def test_archive_structure_unexpected_file_at_root(tmp_path):
    """Test that unexpected files at root are detected."""
    archive_dir = tmp_path / "docs" / "99_archive"
    archive_dir.mkdir(parents=True)

    # Create allowed README.md
    (archive_dir / "README.md").write_text("test")

    # Create unexpected file
    (archive_dir / "UNEXPECTED.md").write_text("test")

    errors = check_archive_structure(tmp_path)
    assert any("UNEXPECTED.md" in err and "only README.md allowed" in err for err in errors), \
        f"Should detect unexpected file at root, got: {errors}"


def test_archive_structure_invalid_subdir_name(tmp_path):
    """Test that invalid archive subdir names are detected."""
    archive_dir = tmp_path / "docs" / "99_archive"
    archive_dir.mkdir(parents=True)

    # Create invalid archive subdir name
    (archive_dir / "BadFormat").mkdir()
    (archive_dir / "BadFormat" / "README.md").write_text("test")

    errors = check_archive_structure(tmp_path)
    assert any("BadFormat" in err and "must match" in err for err in errors), \
        f"Should detect invalid archive subdir name, got: {errors}"


def test_archive_structure_missing_readme(tmp_path):
    """Test that archive subdirs without README.md are detected."""
    archive_dir = tmp_path / "docs" / "99_archive"
    archive_dir.mkdir(parents=True)

    # Create valid-named archive subdir but no README
    (archive_dir / "2026-02_test").mkdir()

    errors = check_archive_structure(tmp_path)
    assert any("README.md" in err and "2026-02_test" in err for err in errors), \
        f"Should detect missing README.md in archive subdir, got: {errors}"


def test_archive_structure_depth_exceeded(tmp_path):
    """Test that archive subdirs with nested subdirs are detected."""
    archive_dir = tmp_path / "docs" / "99_archive"
    archive_dir.mkdir(parents=True)

    # Create valid archive subdir with README
    dated_subdir = archive_dir / "2026-02-14_historical"
    dated_subdir.mkdir()
    (dated_subdir / "README.md").write_text("test")

    # Create nested subdir (exceeds max depth)
    (dated_subdir / "nested_dir").mkdir()

    errors = check_archive_structure(tmp_path)
    assert any("depth exceeds" in err and "nested_dir" in err for err in errors), \
        f"Should detect archive depth violation, got: {errors}"


def test_archive_structure_valid_minimal(tmp_path):
    """Test that a minimal valid structure passes."""
    archive_dir = tmp_path / "docs" / "99_archive"
    archive_dir.mkdir(parents=True)

    # Create minimal required structure
    (archive_dir / "README.md").write_text("Disposition index")

    errors = check_archive_structure(tmp_path)
    assert not errors, f"Minimal valid structure should pass, got: {errors}"


def test_archive_structure_valid_with_dated_subdirs(tmp_path):
    """Test that valid dated subdirs pass."""
    archive_dir = tmp_path / "docs" / "99_archive"
    archive_dir.mkdir(parents=True)

    (archive_dir / "README.md").write_text("Disposition index")

    # Create valid dated subdirs (both formats)
    subdir1 = archive_dir / "2026-02_test"
    subdir1.mkdir()
    (subdir1 / "README.md").write_text("test")

    subdir2 = archive_dir / "2026-02-14_another_test"
    subdir2.mkdir()
    (subdir2 / "README.md").write_text("test")

    errors = check_archive_structure(tmp_path)
    assert not errors, f"Valid dated subdirs should pass, got: {errors}"
