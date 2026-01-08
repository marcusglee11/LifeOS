"""Tests for gate_check schema validation."""

import pytest

from runtime.orchestration.validation import gate_check, GateValidationError


class TestGateCheckSchemaValidation:
    """Tests for schema-based validation."""
    
    def test_valid_build_packet(self):
        """Valid BUILD_PACKET should pass validation."""
        payload = {
            "goal": "Build the thing",
            "scope": {"area": "tests"},
        }
        # Should not raise
        result = gate_check(payload, "build_packet.yaml")
        assert result is None
    
    def test_valid_review_packet(self):
        """Valid REVIEW_PACKET should pass validation."""
        payload = {
            "outcome": "success",
            "artifacts_produced": ["file.py"],
        }
        result = gate_check(payload, "review_packet.yaml")
        assert result is None
    
    def test_valid_mission(self):
        """Valid mission definition should pass validation."""
        payload = {
            "id": "mission-001",
            "name": "Test Mission",
            "type": "build",
            "steps": [],
        }
        result = gate_check(payload, "mission.yaml")
        assert result is None


class TestNegativeCases:
    """Negative tests: validation rejection cases."""
    
    def test_reject_missing_required_field(self):
        """NEGATIVE: Missing required field should be rejected."""
        payload = {
            # Missing "goal" which is required for build_packet
            "scope": {"area": "tests"},
        }
        with pytest.raises(GateValidationError, match="goal"):
            gate_check(payload, "build_packet.yaml")
    
    def test_reject_wrong_type(self):
        """NEGATIVE: Wrong type for field should be rejected."""
        payload = {
            "id": "mission-001",
            "name": "Test",
            "type": "build",
            "steps": "not-a-list",  # Should be array
        }
        with pytest.raises(GateValidationError, match="steps"):
            gate_check(payload, "mission.yaml")
    
    def test_reject_unknown_schema(self):
        """NEGATIVE: Unknown schema name should be rejected."""
        with pytest.raises(GateValidationError, match="Schema not found"):
            gate_check({}, "nonexistent_schema.yaml")
    
    def test_reject_empty_required_string(self):
        """NEGATIVE: Empty string for required field should be rejected."""
        payload = {
            "id": "",  # Empty string
            "name": "Test",
            "type": "build",
            "steps": [],
        }
        with pytest.raises(GateValidationError):
            gate_check(payload, "mission.yaml")


class TestEvidenceGeneration:
    """Tests for validation evidence."""
    
    def test_error_path_included(self):
        """Error messages should include JSON path to invalid field."""
        payload = {
            "id": "m1",
            "name": "Test",
            "type": "build",
            "steps": [{"invalid": "step"}],
        }
        try:
            gate_check(payload, "mission.yaml")
        except GateValidationError as e:
            # Error message should reference the path
            error_msg = str(e)
            assert "steps" in error_msg or "<root>" in error_msg
