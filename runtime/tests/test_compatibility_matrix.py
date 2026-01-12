"""
Tier-2 Compatibility & Versioning Matrix Tests.
"""
import json
import os
import pytest


from runtime.api import TIER2_INTERFACE_VERSION
from runtime.util.deprecation import warn_deprecated
import runtime.config.flags as flags

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "interface_v1")

def test_interface_version_constant():
    """Verify authoritative interface version is exposed and semantic."""
    assert TIER2_INTERFACE_VERSION is not None
    assert isinstance(TIER2_INTERFACE_VERSION, str)
    parts = TIER2_INTERFACE_VERSION.split(".")
    assert len(parts) == 3, "Must be MAJOR.MINOR.PATCH"
    assert all(p.isdigit() for p in parts)

def test_schema_version_fixture_v1():
    """Verify v1 fixture can be loaded and has correct schema version."""
    fixture_path = os.path.join(FIXTURE_DIR, "test_run_result_v1.json")
    with open(fixture_path, "r") as f:
        data = json.load(f)
    
    assert "schema_version" in data
    assert data["schema_version"] == "test_run_result@1"
    assert data["passed"] is True

def test_deprecation_warning_emission():
    """Test deterministic deprecation warning logic."""
    events = []
    
    def mock_emit(payload):
        events.append(payload)

    # force enable warnings for test
    # In a real scenario we'd use flags.DEBUG_DEPRECATION_WARNINGS, 
    # but the utility accepts the emit function directly which is enough to test structure.
    
    warn_deprecated(
        surface="old_feature",
        replacement="new_feature",
        removal_target="2.0.0",
        interface_version="1.0.0",
        first_seen_at="mission_start+1",
        emit_event_fn=mock_emit
    )
    
    assert len(events) == 0, "Should not emit when flag is False (default)"

    # Enable flag and retry
    flags.DEBUG_DEPRECATION_WARNINGS = True
    try:
        warn_deprecated(
            surface="old_feature",
            replacement="new_feature",
            removal_target="2.0.0",
            interface_version="1.0.0",
            first_seen_at="mission_start+2",
            emit_event_fn=mock_emit
        )
        assert len(events) == 1
        evt = events[0]
        assert evt["event_type"] == "deprecation_warning"
        assert evt["deprecated_surface"] == "old_feature"
        assert evt["replacement_surface"] == "new_feature"
        assert evt["removal_target_version"] == "2.0.0"
        assert evt["first_seen_at"] == "mission_start+2"
    finally:
        flags.DEBUG_DEPRECATION_WARNINGS = False
        
def test_scenario_result_fixture_v1():
    """Verify scenario v1 fixture compatibility."""
    fixture_path = os.path.join(FIXTURE_DIR, "scenario_result_v1.json")
    with open(fixture_path, "r") as f:
        data = json.load(f)
        
    assert data["schema_version"] == "scenario_result@1"
    assert "mission_results" in data

