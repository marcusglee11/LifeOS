"""Tests for admin structure validator."""
import os
import tempfile
from pathlib import Path

import pytest

from doc_steward.admin_structure_validator import check_admin_structure


def test_admin_structure_valid_current_repo():
    """Test that the current repo passes admin structure validation."""
    repo_root = os.getcwd()
    errors = check_admin_structure(repo_root)
    assert not errors, f"Admin structure validation failed: {errors}"


def test_admin_structure_missing_required_file(tmp_path):
    """Test that missing required files are detected."""
    admin_dir = tmp_path / "docs" / "11_admin"
    admin_dir.mkdir(parents=True)

    # Create only some required files (missing DECISIONS.md)
    (admin_dir / "LIFEOS_STATE.md").write_text("test")
    (admin_dir / "BACKLOG.md").write_text("test")
    (admin_dir / "INBOX.md").write_text("test")

    errors = check_admin_structure(tmp_path)
    assert any("DECISIONS.md" in err for err in errors), \
        f"Should detect missing DECISIONS.md, got: {errors}"


def test_admin_structure_unexpected_file_at_root(tmp_path):
    """Test that unexpected files at root are detected."""
    admin_dir = tmp_path / "docs" / "11_admin"
    admin_dir.mkdir(parents=True)

    # Create required files
    (admin_dir / "LIFEOS_STATE.md").write_text("test")
    (admin_dir / "BACKLOG.md").write_text("test")
    (admin_dir / "INBOX.md").write_text("test")
    (admin_dir / "DECISIONS.md").write_text("test")

    # Add unexpected file
    (admin_dir / "UNEXPECTED_FILE.md").write_text("test")

    errors = check_admin_structure(tmp_path)
    assert any("UNEXPECTED_FILE.md" in err for err in errors), \
        f"Should detect unexpected file, got: {errors}"


def test_admin_structure_unexpected_subdirectory(tmp_path):
    """Test that unexpected subdirectories are detected."""
    admin_dir = tmp_path / "docs" / "11_admin"
    admin_dir.mkdir(parents=True)

    # Create required files
    (admin_dir / "LIFEOS_STATE.md").write_text("test")
    (admin_dir / "BACKLOG.md").write_text("test")
    (admin_dir / "INBOX.md").write_text("test")
    (admin_dir / "DECISIONS.md").write_text("test")

    # Add unexpected subdirectory
    unexpected_dir = admin_dir / "unexpected_subdir"
    unexpected_dir.mkdir()

    errors = check_admin_structure(tmp_path)
    assert any("unexpected_subdir" in err for err in errors), \
        f"Should detect unexpected subdirectory, got: {errors}"


def test_admin_structure_invalid_build_summary_filename(tmp_path):
    """Test that invalid build summary filenames are detected."""
    admin_dir = tmp_path / "docs" / "11_admin"
    admin_dir.mkdir(parents=True)

    # Create required files
    (admin_dir / "LIFEOS_STATE.md").write_text("test")
    (admin_dir / "BACKLOG.md").write_text("test")
    (admin_dir / "INBOX.md").write_text("test")
    (admin_dir / "DECISIONS.md").write_text("test")

    # Create build_summaries with invalid filename
    build_summaries = admin_dir / "build_summaries"
    build_summaries.mkdir()
    (build_summaries / "invalid_name.md").write_text("test")

    errors = check_admin_structure(tmp_path)
    assert any("invalid_name.md" in err for err in errors), \
        f"Should detect invalid build summary filename, got: {errors}"


def test_admin_structure_valid_build_summary_filename(tmp_path):
    """Test that valid build summary filenames pass."""
    admin_dir = tmp_path / "docs" / "11_admin"
    admin_dir.mkdir(parents=True)

    # Create required files
    (admin_dir / "LIFEOS_STATE.md").write_text("test")
    (admin_dir / "BACKLOG.md").write_text("test")
    (admin_dir / "INBOX.md").write_text("test")
    (admin_dir / "DECISIONS.md").write_text("test")

    # Create build_summaries with valid filename
    build_summaries = admin_dir / "build_summaries"
    build_summaries.mkdir()
    (build_summaries / "E2E_Spine_Proof_Build_Summary_2026-02-14.md").write_text("test")

    errors = check_admin_structure(tmp_path)
    assert not errors, f"Valid build summary should pass, got: {errors}"


def test_admin_structure_archive_subdir_missing_readme(tmp_path):
    """Test that archive subdirs without README.md are detected."""
    admin_dir = tmp_path / "docs" / "11_admin"
    admin_dir.mkdir(parents=True)

    # Create required files
    (admin_dir / "LIFEOS_STATE.md").write_text("test")
    (admin_dir / "BACKLOG.md").write_text("test")
    (admin_dir / "INBOX.md").write_text("test")
    (admin_dir / "DECISIONS.md").write_text("test")

    # Create archive subdir without README.md
    archive = admin_dir / "archive"
    archive.mkdir()
    archive_subdir = archive / "2026-02-14_test"
    archive_subdir.mkdir()

    errors = check_admin_structure(tmp_path)
    assert any("README.md" in err and "2026-02-14_test" in err for err in errors), \
        f"Should detect missing README.md in archive subdir, got: {errors}"


def test_admin_structure_invalid_archive_subdir_name(tmp_path):
    """Test that invalid archive subdir names are detected."""
    admin_dir = tmp_path / "docs" / "11_admin"
    admin_dir.mkdir(parents=True)

    # Create required files
    (admin_dir / "LIFEOS_STATE.md").write_text("test")
    (admin_dir / "BACKLOG.md").write_text("test")
    (admin_dir / "INBOX.md").write_text("test")
    (admin_dir / "DECISIONS.md").write_text("test")

    # Create archive subdir with invalid name
    archive = admin_dir / "archive"
    archive.mkdir()
    invalid_subdir = archive / "invalid-name"  # Should be YYYY-MM-DD_topic
    invalid_subdir.mkdir()

    errors = check_admin_structure(tmp_path)
    assert any("invalid-name" in err for err in errors), \
        f"Should detect invalid archive subdir name, got: {errors}"
