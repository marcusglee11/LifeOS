"""Tests for global archive link ban validator."""
import tempfile
from pathlib import Path

import pytest

from doc_steward.global_archive_link_ban_validator import check_global_archive_link_ban


def test_archive_link_ban_no_docs_is_ok(tmp_path):
    """Test that missing docs/ directory is not an error."""
    errors = check_global_archive_link_ban(tmp_path)
    assert not errors, f"Missing docs/ should not be an error, got: {errors}"


def test_archive_link_ban_active_doc_linking_to_archive(tmp_path):
    """Test that active docs linking to archive are detected."""
    docs_path = tmp_path / "docs"
    docs_path.mkdir()

    # Create archive structure
    archive_dir = docs_path / "02_protocols" / "archive" / "2026-02_test"
    archive_dir.mkdir(parents=True)
    (archive_dir / "old_doc.md").write_text("archived content")

    # Create active doc that links to archive
    active_doc = docs_path / "02_protocols" / "active.md"
    active_doc.write_text("[Link to archived](archive/2026-02_test/old_doc.md)")

    errors = check_global_archive_link_ban(tmp_path)
    assert any("active.md" in err and "archive" in err for err in errors), \
        f"Should detect active doc linking to archive, got: {errors}"


def test_archive_link_ban_archived_doc_can_link_freely(tmp_path):
    """Test that archived docs can link to other archived docs."""
    docs_path = tmp_path / "docs"
    docs_path.mkdir()

    # Create archive structure
    archive_dir = docs_path / "02_protocols" / "archive" / "2026-02_test"
    archive_dir.mkdir(parents=True)
    (archive_dir / "old_doc.md").write_text("archived content")

    # Create another archived doc that links within archive
    (archive_dir / "another_doc.md").write_text("[Link to sibling](old_doc.md)")

    errors = check_global_archive_link_ban(tmp_path)
    assert not errors, f"Archived docs should be able to link freely, got: {errors}"


def test_archive_link_ban_directory_readme_to_archive_readme_ok(tmp_path):
    """Test that directory README can link to archive README."""
    docs_path = tmp_path / "docs"
    docs_path.mkdir()

    # Create archive structure
    protocols_dir = docs_path / "02_protocols"
    protocols_dir.mkdir()

    archive_dir = protocols_dir / "archive" / "2026-02_test"
    archive_dir.mkdir(parents=True)
    (archive_dir / "README.md").write_text("Disposition table")

    # Create directory README that links to archive README
    readme = protocols_dir / "README.md"
    readme.write_text("[Archive](archive/2026-02_test/README.md)")

    errors = check_global_archive_link_ban(tmp_path)
    assert not errors, f"Directory README linking to archive README should be allowed, got: {errors}"


def test_archive_link_ban_directory_readme_to_archived_file_blocked(tmp_path):
    """Test that directory README cannot link to individual archived files."""
    docs_path = tmp_path / "docs"
    docs_path.mkdir()

    # Create archive structure
    protocols_dir = docs_path / "02_protocols"
    protocols_dir.mkdir()

    archive_dir = protocols_dir / "archive" / "2026-02_test"
    archive_dir.mkdir(parents=True)
    (archive_dir / "old_file.md").write_text("archived content")

    # Create directory README that links to archived file (NOT README)
    readme = protocols_dir / "README.md"
    readme.write_text("[Link to archived file](archive/2026-02_test/old_file.md)")

    errors = check_global_archive_link_ban(tmp_path)
    assert any("README.md" in err and "archive" in err for err in errors), \
        f"Directory README should not link to archived files, got: {errors}"


def test_archive_link_ban_99_archive_blocked(tmp_path):
    """Test that active docs cannot link to docs/99_archive/."""
    docs_path = tmp_path / "docs"
    docs_path.mkdir()

    # Create 99_archive structure
    archive_99 = docs_path / "99_archive" / "2026-02_test"
    archive_99.mkdir(parents=True)
    (archive_99 / "old_doc.md").write_text("archived content")

    # Create active doc that links to 99_archive
    active_doc = docs_path / "02_protocols" / "active.md"
    active_doc.parent.mkdir(parents=True)
    active_doc.write_text("[Link to old archive](../99_archive/2026-02_test/old_doc.md)")

    errors = check_global_archive_link_ban(tmp_path)
    assert any("active.md" in err and "archive" in err for err in errors), \
        f"Should detect link to docs/99_archive/, got: {errors}"


def test_archive_link_ban_external_links_ok(tmp_path):
    """Test that external HTTP links are not affected."""
    docs_path = tmp_path / "docs"
    docs_path.mkdir()

    # Create active doc with external link
    active_doc = docs_path / "02_protocols" / "active.md"
    active_doc.parent.mkdir(parents=True)
    active_doc.write_text("[External link](https://example.com/archive/something.md)")

    errors = check_global_archive_link_ban(tmp_path)
    assert not errors, f"External links should be allowed, got: {errors}"
