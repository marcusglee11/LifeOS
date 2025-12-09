"""Tests for CND-3: Governance Override Protocol"""
import unittest
import tempfile
import os

from runtime.governance.override_protocol import (
    OverrideProtocol, OverrideRequest, OverrideProtocolError
)


class TestGovernanceOverrideProtocol(unittest.TestCase):
    """Test governance override protocol."""
    
    def test_prepare_request_no_write(self):
        """Preparing request does not write."""
        protocol = OverrideProtocol()
        
        request = protocol.prepare_override_request(
            request_id="REQ001",
            timestamp="2025-01-01T00:00:00Z",
            reason="Test override",
            target_surface="test/surface.py",
            requested_change_hash="abc123",
            human_approval={"approver": "test", "type": "approve"}
        )
        
        self.assertEqual(request.id, "REQ001")
        self.assertIn("REQ001", protocol.get_pending_requests())
    
    def test_apply_without_council_key_fails(self):
        """Apply without valid council key fails."""
        protocol = OverrideProtocol()
        
        request = protocol.prepare_override_request(
            "REQ002", "2025-01-01T00:00:00Z", "Test",
            "surface.py", "hash", {"approver": "test"}
        )
        
        with self.assertRaises(OverrideProtocolError):
            protocol.apply_override(request, "INVALID_KEY")
    
    def test_apply_with_council_key_succeeds(self):
        """Apply with valid council key succeeds."""
        protocol = OverrideProtocol()
        
        request = protocol.prepare_override_request(
            "REQ003", "2025-01-01T00:00:00Z", "Test",
            "surface.py", "hash", {"approver": "test"}
        )
        
        result = protocol.apply_override(request, "COUNCIL_TIER1_TEST_KEY")
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()
