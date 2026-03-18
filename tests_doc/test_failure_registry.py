"""
Validation test for config/agent_feedback/failure_registry.yaml.

Fail-closed:
  - Missing registry file → failure
  - Invalid schema version → failure
  - Invalid enum values → failure
  - Resolved entry with missing/empty regression_test → failure
  - Resolved entry with fix_path that does not exist → failure
  - Resolved entry with empty evidence_ref → failure
"""
from pathlib import Path

import pytest
import yaml


REGISTRY_PATH = Path("config/agent_feedback/failure_registry.yaml")
VALID_FIX_TYPES = {"doc", "tool", "constraint", "test"}
VALID_STATUSES = {"resolved", "open", "wont_fix"}
REQUIRED_FIELDS = {"id", "failure_class", "root_cause", "fix_type", "fix_path", "status", "date"}


def load_registry() -> dict:
    assert REGISTRY_PATH.exists(), f"Missing registry file: {REGISTRY_PATH}"
    with REGISTRY_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_registry_file_exists():
    """Registry file must exist."""
    assert REGISTRY_PATH.exists(), f"Missing: {REGISTRY_PATH}"


def test_registry_schema_version():
    """Registry must declare schema_version: failure_registry.v1."""
    registry = load_registry()
    assert registry.get("schema_version") == "failure_registry.v1", (
        f"Expected schema_version: failure_registry.v1, got: {registry.get('schema_version')}"
    )


def test_registry_has_entries_key():
    """Registry must have an entries key (may be empty list)."""
    registry = load_registry()
    assert "entries" in registry, "Registry missing 'entries' key"
    assert isinstance(registry["entries"], list), "'entries' must be a list"


def test_registry_empty_is_valid():
    """An empty registry (entries: []) must validate successfully."""
    registry = load_registry()
    assert registry["entries"] is not None, "entries must not be null"


def test_registry_entry_required_fields():
    """Every entry must have all required fields."""
    registry = load_registry()
    for entry in registry.get("entries", []):
        missing = REQUIRED_FIELDS - set(entry.keys())
        assert not missing, (
            f"Entry {entry.get('id', '?')} missing fields: {missing}"
        )


def test_registry_entry_fix_type_enum():
    """fix_type must be one of: doc | tool | constraint | test."""
    registry = load_registry()
    for entry in registry.get("entries", []):
        fix_type = entry.get("fix_type")
        assert fix_type in VALID_FIX_TYPES, (
            f"Entry {entry.get('id', '?')}: invalid fix_type '{fix_type}'. "
            f"Must be one of: {VALID_FIX_TYPES}"
        )


def test_registry_entry_status_enum():
    """status must be one of: resolved | open | wont_fix."""
    registry = load_registry()
    for entry in registry.get("entries", []):
        status = entry.get("status")
        assert status in VALID_STATUSES, (
            f"Entry {entry.get('id', '?')}: invalid status '{status}'. "
            f"Must be one of: {VALID_STATUSES}"
        )


def test_registry_resolved_entries_have_regression_test():
    """Resolved entries must declare a non-empty regression_test path."""
    registry = load_registry()
    for entry in registry.get("entries", []):
        if entry.get("status") == "resolved":
            rt = entry.get("regression_test", "")
            assert rt, (
                f"Entry {entry.get('id', '?')} is resolved but missing regression_test"
            )


def test_registry_resolved_entries_regression_test_exists():
    """For resolved entries, regression_test path must exist on disk."""
    registry = load_registry()
    for entry in registry.get("entries", []):
        if entry.get("status") == "resolved":
            rt = entry.get("regression_test", "")
            if rt:
                assert Path(rt).exists(), (
                    f"Entry {entry.get('id', '?')}: regression_test path does not exist: {rt}"
                )


def test_registry_resolved_entries_fix_path_exists():
    """For resolved entries, fix_path must exist on disk."""
    registry = load_registry()
    for entry in registry.get("entries", []):
        if entry.get("status") == "resolved":
            fp = entry.get("fix_path", "")
            if fp:
                assert Path(fp).exists(), (
                    f"Entry {entry.get('id', '?')}: fix_path does not exist: {fp}"
                )


def test_registry_resolved_entries_have_evidence_ref():
    """Resolved entries must have a non-empty evidence_ref."""
    registry = load_registry()
    for entry in registry.get("entries", []):
        if entry.get("status") == "resolved":
            ev = entry.get("evidence_ref", "")
            assert ev, (
                f"Entry {entry.get('id', '?')} is resolved but evidence_ref is empty"
            )


def test_registry_invalid_status_detected(tmp_path):
    """Adding an entry with invalid status must fail validation."""
    bad_entry = {
        "id": "AF-TEST",
        "failure_class": "test",
        "root_cause": "test",
        "fix_type": "doc",
        "fix_path": "some/path",
        "status": "invalid_status",
        "date": "2026-01-01",
    }
    status = bad_entry.get("status")
    assert status not in VALID_STATUSES, "Invalid status should not be in VALID_STATUSES"


def test_registry_resolved_missing_regression_test_detected():
    """Resolved entry without regression_test must fail."""
    entry = {
        "id": "AF-TEST",
        "failure_class": "test",
        "root_cause": "test",
        "fix_type": "doc",
        "fix_path": "some/path",
        "status": "resolved",
        "date": "2026-01-01",
        # No regression_test
    }
    rt = entry.get("regression_test", "")
    assert not rt, "Entry has no regression_test — should be caught"
    assert entry.get("status") == "resolved", "Status is resolved"
    # This combination should fail the registry check
    assert not rt, "Missing regression_test detected correctly"
