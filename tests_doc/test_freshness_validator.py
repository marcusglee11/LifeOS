"""Tests for freshness validator."""
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import pytest

from doc_steward.freshness_validator import check_freshness, get_freshness_mode


def test_freshness_mode_off_by_default():
    """Test that freshness mode defaults to 'off'."""
    with mock.patch.dict(os.environ, {}, clear=True):
        assert get_freshness_mode() == "off"


def test_freshness_mode_from_env():
    """Test that freshness mode can be set via env var."""
    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "warn"}):
        assert get_freshness_mode() == "warn"

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        assert get_freshness_mode() == "block"


def test_freshness_mode_invalid_defaults_to_off():
    """Test that invalid freshness mode defaults to 'off'."""
    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "invalid"}):
        assert get_freshness_mode() == "off"


def test_freshness_check_off_mode_returns_empty(tmp_path):
    """Test that off mode returns no warnings or errors."""
    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "off"}):
        warnings, errors = check_freshness(tmp_path)
        assert warnings == []
        assert errors == []


def test_freshness_check_missing_status_file_warn_mode(tmp_path):
    """Test that missing status file generates warning in warn mode."""
    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "warn"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(warnings) == 1
        assert "missing" in warnings[0].lower()
        assert errors == []


def test_freshness_check_missing_status_file_block_mode(tmp_path):
    """Test that missing status file generates error in block mode."""
    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(errors) == 1
        assert "missing" in errors[0].lower()


def test_freshness_check_fresh_status_file(tmp_path):
    """Test that a fresh status file passes."""
    # Create a fresh status file (current time)
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"
    status_file.write_text(json.dumps({"contradictions": []}))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        warnings, errors = check_freshness(tmp_path)
        assert warnings == []
        assert errors == []


def test_freshness_check_stale_status_file_warn_mode(tmp_path):
    """Test that a stale status file generates warning in warn mode."""
    # Create a stale status file (26 hours old)
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"
    status_file.write_text(json.dumps({"contradictions": []}))

    # Set file mtime to 26 hours ago
    stale_time = datetime.now(timezone.utc) - timedelta(hours=26)
    os.utime(status_file, (stale_time.timestamp(), stale_time.timestamp()))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "warn"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(warnings) == 1
        assert "stale" in warnings[0].lower()
        assert errors == []


def test_freshness_check_stale_status_file_block_mode(tmp_path):
    """Test that a stale status file generates error in block mode."""
    # Create a stale status file (26 hours old)
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"
    status_file.write_text(json.dumps({"contradictions": []}))

    # Set file mtime to 26 hours ago
    stale_time = datetime.now(timezone.utc) - timedelta(hours=26)
    os.utime(status_file, (stale_time.timestamp(), stale_time.timestamp()))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(errors) == 1
        assert "stale" in errors[0].lower()


def test_freshness_check_contradictions_warn_severity(tmp_path):
    """Test that contradictions with 'warn' severity generate warnings."""
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"

    status_data = {
        "contradictions": [
            {
                "id": "C1",
                "severity": "warn",
                "message": "Test warning",
                "refs": ["ref1.md"]
            }
        ]
    }
    status_file.write_text(json.dumps(status_data))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "warn"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(warnings) == 1
        assert "C1" in warnings[0]
        assert "Test warning" in warnings[0]
        assert errors == []


def test_freshness_check_contradictions_block_severity_warn_mode(tmp_path):
    """Test that contradictions with 'block' severity generate warnings in warn mode."""
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"

    status_data = {
        "contradictions": [
            {
                "id": "C1",
                "severity": "block",
                "message": "Test blocking issue",
                "refs": ["ref1.md"]
            }
        ]
    }
    status_file.write_text(json.dumps(status_data))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "warn"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(warnings) == 1
        assert "C1" in warnings[0]
        assert errors == []


def test_freshness_check_contradictions_block_severity_block_mode(tmp_path):
    """Test that contradictions with 'block' severity generate errors in block mode."""
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"

    status_data = {
        "contradictions": [
            {
                "id": "C1",
                "severity": "block",
                "message": "Test blocking issue",
                "refs": ["ref1.md", "ref2.md"]
            }
        ]
    }
    status_file.write_text(json.dumps(status_data))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(errors) == 1
        assert "C1" in errors[0]
        assert "Test blocking issue" in errors[0]
        assert "ref1.md" in errors[0]


def test_freshness_check_missing_contradictions_field(tmp_path):
    """Test that missing contradictions field is treated as empty (backward compatibility)."""
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"

    # Status file without contradictions field
    status_file.write_text(json.dumps({}))

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        warnings, errors = check_freshness(tmp_path)
        # Should not error on missing field
        assert errors == []


def test_freshness_check_invalid_json(tmp_path):
    """Test that invalid JSON generates appropriate error/warning."""
    status_dir = tmp_path / "artifacts" / "status"
    status_dir.mkdir(parents=True)
    status_file = status_dir / "runtime_status.json"
    status_file.write_text("invalid json{")

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "warn"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(warnings) == 1
        assert "parse" in warnings[0].lower()

    with mock.patch.dict(os.environ, {"LIFEOS_DOC_FRESHNESS_MODE": "block"}):
        warnings, errors = check_freshness(tmp_path)
        assert len(errors) == 1
        assert "parse" in errors[0].lower()
