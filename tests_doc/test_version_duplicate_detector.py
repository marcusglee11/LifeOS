"""Tests for version duplicate detector."""
import json
import tempfile
from pathlib import Path

import pytest

from doc_steward.version_duplicate_detector import (
    scan_version_duplicates,
    check_version_duplicates_with_lineage,
)


def test_version_duplicate_scan_no_duplicates(tmp_path):
    """Test that no duplicates are reported when only one version exists."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create single versioned file
    (docs_path / "doc_v1.0.md").write_text("test")

    duplicates = scan_version_duplicates(tmp_path)
    assert not duplicates, f"Should find no duplicates, got: {duplicates}"


def test_version_duplicate_scan_finds_duplicates(tmp_path):
    """Test that version duplicates are detected."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create duplicate versions
    (docs_path / "doc_v1.0.md").write_text("test")
    (docs_path / "doc_v1.1.md").write_text("test")

    duplicates = scan_version_duplicates(tmp_path)
    assert "doc" in duplicates, f"Should find 'doc' duplicate group, got: {duplicates}"
    assert len(duplicates["doc"]) == 2, f"Should find 2 files in group, got: {duplicates}"


def test_version_duplicate_scan_ignores_archives(tmp_path):
    """Test that archived versions are not reported as duplicates."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create active version
    (docs_path / "doc_v1.1.md").write_text("test")

    # Create archived version (should be ignored)
    archive_dir = docs_path / "archive" / "2026-02_test"
    archive_dir.mkdir(parents=True)
    (archive_dir / "doc_v1.0.md").write_text("test")

    duplicates = scan_version_duplicates(tmp_path)
    assert not duplicates, f"Archived versions should not count as duplicates, got: {duplicates}"


def test_version_duplicate_scan_multiple_groups(tmp_path):
    """Test that multiple duplicate groups are detected."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create multiple duplicate groups
    (docs_path / "doc_a_v1.0.md").write_text("test")
    (docs_path / "doc_a_v1.1.md").write_text("test")

    (docs_path / "doc_b_v1.0.md").write_text("test")
    (docs_path / "doc_b_v2.0.md").write_text("test")

    duplicates = scan_version_duplicates(tmp_path)
    assert len(duplicates) == 2, f"Should find 2 duplicate groups, got: {duplicates}"
    assert "doc_a" in duplicates and "doc_b" in duplicates


def test_version_duplicate_report_format(tmp_path):
    """Test that the report format is correct."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create duplicate versions
    (docs_path / "test_doc_v1.0.md").write_text("test")
    (docs_path / "test_doc_v1.1.md").write_text("test")

    report = check_version_duplicates_with_lineage(tmp_path)

    # Report should be a list of strings
    assert isinstance(report, list)
    assert len(report) > 0

    # Should contain group information
    report_text = "\n".join(report)
    assert "test_doc" in report_text.lower() or "Base:" in report_text


def test_version_duplicate_report_no_duplicates(tmp_path):
    """Test that report indicates no duplicates when none found."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    (docs_path / "doc_v1.0.md").write_text("test")

    report = check_version_duplicates_with_lineage(tmp_path)
    report_text = "\n".join(report)

    assert "no" in report_text.lower() and "duplicate" in report_text.lower()


def test_version_duplicate_lineage_warning(tmp_path):
    """Test that missing lineage in ARTEFACT_INDEX is warned."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create duplicate versions
    (docs_path / "doc_v1.0.md").write_text("test")
    (docs_path / "doc_v1.1.md").write_text("test")

    # Create index without lineage
    index_data = {
        "meta": {"version": "1.0"},
        "artefacts": {
            "doc_v10": "docs/02_protocols/doc_v1.0.md",
            "doc_v11": "docs/02_protocols/doc_v1.1.md"
        }
    }
    (docs_path / "ARTEFACT_INDEX.json").write_text(json.dumps(index_data))

    report = check_version_duplicates_with_lineage(tmp_path)
    report_text = "\n".join(report)

    # Should warn about missing lineage
    assert "lineage" in report_text.lower() or "WARNING" in report_text
