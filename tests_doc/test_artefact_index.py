"""Tests for artefact index validator."""
import json
import tempfile
from pathlib import Path

import pytest

from doc_steward.artefact_index_validator import check_artefact_index


def test_artefact_index_no_index_is_ok(tmp_path):
    """Test that directories without ARTEFACT_INDEX.json are not checked."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create some files but no index
    (docs_path / "some_file.md").write_text("test")

    errors = check_artefact_index(tmp_path)
    assert not errors, f"Missing index should not be an error when not checking specific dir, got: {errors}"


def test_artefact_index_missing_meta_section(tmp_path):
    """Test that missing 'meta' section is detected."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create index without meta
    index_data = {"artefacts": {}}
    (docs_path / "ARTEFACT_INDEX.json").write_text(json.dumps(index_data))

    errors = check_artefact_index(tmp_path)
    assert any("meta" in err.lower() for err in errors), \
        f"Should detect missing 'meta' section, got: {errors}"


def test_artefact_index_missing_artefacts_section(tmp_path):
    """Test that missing 'artefacts' section is detected."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create index without artefacts
    index_data = {"meta": {"version": "1.0"}}
    (docs_path / "ARTEFACT_INDEX.json").write_text(json.dumps(index_data))

    errors = check_artefact_index(tmp_path)
    assert any("artefacts" in err.lower() for err in errors), \
        f"Should detect missing 'artefacts' section, got: {errors}"


def test_artefact_index_referenced_path_not_exists(tmp_path):
    """Test that referenced paths that don't exist are detected."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create index referencing non-existent file
    index_data = {
        "meta": {"version": "1.0"},
        "artefacts": {
            "test_doc": "docs/02_protocols/nonexistent.md"
        }
    }
    (docs_path / "ARTEFACT_INDEX.json").write_text(json.dumps(index_data))

    errors = check_artefact_index(tmp_path)
    assert any("nonexistent.md" in err and "does not exist" in err for err in errors), \
        f"Should detect non-existent referenced path, got: {errors}"


def test_artefact_index_orphan_active_file(tmp_path):
    """Test that active files not in index are detected."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create index
    index_data = {
        "meta": {"version": "1.0"},
        "artefacts": {}
    }
    (docs_path / "ARTEFACT_INDEX.json").write_text(json.dumps(index_data))

    # Create orphan file (not indexed, not exempt)
    (docs_path / "orphan.md").write_text("test")

    errors = check_artefact_index(tmp_path)
    assert any("orphan.md" in err and "not in index" in err for err in errors), \
        f"Should detect orphan active file, got: {errors}"


def test_artefact_index_readme_is_exempt(tmp_path):
    """Test that README.md is exempt from orphan check."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create index
    index_data = {
        "meta": {"version": "1.0"},
        "artefacts": {}
    }
    (docs_path / "ARTEFACT_INDEX.json").write_text(json.dumps(index_data))

    # Create README.md (should be exempt)
    (docs_path / "README.md").write_text("test")

    errors = check_artefact_index(tmp_path)
    assert not errors, f"README.md should be exempt, got: {errors}"


def test_artefact_index_supersession_chain_valid(tmp_path):
    """Test that valid supersession chains pass."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create actual files
    (docs_path / "doc_v1.0.md").write_text("test")
    (docs_path / "doc_v1.1.md").write_text("test")

    # Create index with valid supersession chain (list format)
    index_data = {
        "meta": {"version": "1.0"},
        "artefacts": [
            {
                "path": "docs/02_protocols/doc_v1.0.md",
                "superseded_by": "docs/02_protocols/doc_v1.1.md"
            },
            {
                "path": "docs/02_protocols/doc_v1.1.md",
                "supersedes": "docs/02_protocols/doc_v1.0.md"
            }
        ]
    }
    (docs_path / "ARTEFACT_INDEX.json").write_text(json.dumps(index_data))

    errors = check_artefact_index(tmp_path)
    assert not errors, f"Valid supersession chain should pass, got: {errors}"


def test_artefact_index_supersession_chain_broken(tmp_path):
    """Test that broken supersession chains are detected."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create one file but reference non-existent superseding doc
    (docs_path / "doc_v1.0.md").write_text("test")

    # Create index with broken chain
    index_data = {
        "meta": {"version": "1.0"},
        "artefacts": [
            {
                "path": "docs/02_protocols/doc_v1.0.md",
                "superseded_by": "docs/02_protocols/nonexistent_v1.1.md"
            }
        ]
    }
    (docs_path / "ARTEFACT_INDEX.json").write_text(json.dumps(index_data))

    errors = check_artefact_index(tmp_path)
    assert any("nonexistent_v1.1.md" in err and "non-indexed" in err for err in errors), \
        f"Should detect broken supersession chain, got: {errors}"


def test_artefact_index_valid_minimal(tmp_path):
    """Test that a minimal valid index passes."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create minimal valid index
    index_data = {
        "meta": {"version": "1.0"},
        "artefacts": {}
    }
    (docs_path / "ARTEFACT_INDEX.json").write_text(json.dumps(index_data))

    errors = check_artefact_index(tmp_path)
    assert not errors, f"Minimal valid index should pass, got: {errors}"


def test_artefact_index_invalid_json(tmp_path):
    """Test that invalid JSON is detected."""
    docs_path = tmp_path / "docs" / "02_protocols"
    docs_path.mkdir(parents=True)

    # Create invalid JSON
    (docs_path / "ARTEFACT_INDEX.json").write_text("{invalid json")

    errors = check_artefact_index(tmp_path)
    assert any("Invalid JSON" in err for err in errors), \
        f"Should detect invalid JSON, got: {errors}"
