"""Tests for admin archive link ban validator."""
import os
import tempfile
from pathlib import Path

import pytest

from doc_steward.admin_archive_link_ban_validator import check_admin_archive_link_ban


def test_archive_link_ban_current_repo():
    """Test that the current repo passes archive link ban validation."""
    repo_root = os.getcwd()
    errors = check_admin_archive_link_ban(repo_root)
    assert not errors, f"Archive link ban validation failed: {errors}"


def test_archive_link_ban_active_doc_links_to_archive(tmp_path):
    """Test that active docs linking to archive are detected."""
    # Setup
    docs_dir = tmp_path / "docs"
    admin_dir = docs_dir / "11_admin"
    archive_dir = admin_dir / "archive" / "2026-02-14_test"
    archive_dir.mkdir(parents=True)

    # Create an archived file
    (archive_dir / "archived_doc.md").write_text("# Archived")

    # Create an active doc that links to archived file
    active_doc = docs_dir / "active_doc.md"
    active_doc.write_text("[link](./11_admin/archive/2026-02-14_test/archived_doc.md)")

    errors = check_admin_archive_link_ban(tmp_path)
    assert len(errors) == 1, f"Should detect 1 violation, got: {errors}"
    assert "active_doc.md" in errors[0]


def test_archive_link_ban_archived_files_can_link_freely(tmp_path):
    """Test that archived files can link to other archived files."""
    # Setup
    docs_dir = tmp_path / "docs"
    admin_dir = docs_dir / "11_admin"
    archive_dir = admin_dir / "archive" / "2026-02-14_test"
    archive_dir.mkdir(parents=True)

    # Create archived files that link to each other
    (archive_dir / "archived_doc1.md").write_text("# Archived 1")
    (archive_dir / "archived_doc2.md").write_text("[link](archived_doc1.md)")

    errors = check_admin_archive_link_ban(tmp_path)
    assert not errors, f"Archived files should be able to link freely, got: {errors}"


def test_archive_link_ban_admin_readme_can_link_to_archive_readme(tmp_path):
    """Test that docs/11_admin/README.md can link to archive README."""
    # Setup
    docs_dir = tmp_path / "docs"
    admin_dir = docs_dir / "11_admin"
    archive_dir = admin_dir / "archive" / "2026-02-14_test"
    archive_dir.mkdir(parents=True)

    # Create archive README
    (archive_dir / "README.md").write_text("# Archive README")

    # Create admin README that links to archive README
    admin_readme = admin_dir / "README.md"
    admin_readme.write_text("[archive](./archive/2026-02-14_test/README.md)")

    errors = check_admin_archive_link_ban(tmp_path)
    assert not errors, f"Admin README should be able to link to archive README, got: {errors}"


def test_archive_link_ban_admin_readme_cannot_link_to_archived_file(tmp_path):
    """Test that docs/11_admin/README.md cannot link to individual archived files."""
    # Setup
    docs_dir = tmp_path / "docs"
    admin_dir = docs_dir / "11_admin"
    archive_dir = admin_dir / "archive" / "2026-02-14_test"
    archive_dir.mkdir(parents=True)

    # Create an archived file
    (archive_dir / "archived_doc.md").write_text("# Archived")

    # Create admin README that links to individual archived file (not allowed)
    admin_readme = admin_dir / "README.md"
    admin_readme.write_text("[link](./archive/2026-02-14_test/archived_doc.md)")

    errors = check_admin_archive_link_ban(tmp_path)
    assert len(errors) == 1, f"Should detect 1 violation, got: {errors}"
    assert "README.md" in errors[0]


def test_archive_link_ban_external_links_ignored(tmp_path):
    """Test that external links (http/https) are ignored."""
    # Setup
    docs_dir = tmp_path / "docs"
    admin_dir = docs_dir / "11_admin"
    archive_dir = admin_dir / "archive" / "2026-02-14_test"
    archive_dir.mkdir(parents=True)

    # Create active doc with external link
    active_doc = docs_dir / "active_doc.md"
    active_doc.write_text("[link](https://example.com/archive/file.md)")

    errors = check_admin_archive_link_ban(tmp_path)
    assert not errors, f"External links should be ignored, got: {errors}"


def test_archive_link_ban_fragment_identifiers_handled(tmp_path):
    """Test that fragment identifiers in links are handled correctly."""
    # Setup
    docs_dir = tmp_path / "docs"
    admin_dir = docs_dir / "11_admin"
    archive_dir = admin_dir / "archive" / "2026-02-14_test"
    archive_dir.mkdir(parents=True)

    # Create an archived file
    (archive_dir / "archived_doc.md").write_text("# Archived")

    # Create active doc that links to archived file with fragment
    active_doc = docs_dir / "active_doc.md"
    active_doc.write_text("[link](./11_admin/archive/2026-02-14_test/archived_doc.md#section)")

    errors = check_admin_archive_link_ban(tmp_path)
    assert len(errors) == 1, f"Should detect 1 violation (fragment should be stripped), got: {errors}"
