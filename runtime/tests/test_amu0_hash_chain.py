"""Tests for CND-2: AMU0 Hash Chain"""
import unittest
import tempfile
import os

from runtime.amu0 import AMU0Lineage, compute_entry_hash


class TestAMU0HashChain(unittest.TestCase):
    """Test hash-chained lineage."""
    
    def test_append_creates_chain(self):
        """Appending entries creates valid chain."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lineage_path = os.path.join(tmpdir, "lineage.json")
            lineage = AMU0Lineage(lineage_path)
            
            # Add first entry
            e1 = lineage.append_entry(
                entry_id="E001",
                timestamp="2025-01-01T00:00:00Z",
                artefact_hash="abc123",
                attestation={"type": "test"}
            )
            self.assertIsNone(e1.parent_hash)
            
            # Add second entry
            e2 = lineage.append_entry(
                entry_id="E002",
                timestamp="2025-01-01T00:01:00Z",
                artefact_hash="def456",
                attestation={"type": "test"}
            )
            self.assertEqual(e2.parent_hash, e1.entry_hash)
    
    def test_chain_verification_passes(self):
        """Valid chain passes verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lineage_path = os.path.join(tmpdir, "lineage.json")
            lineage = AMU0Lineage(lineage_path)
            
            lineage.append_entry("E1", "2025-01-01T00:00:00Z", "h1", {})
            lineage.append_entry("E2", "2025-01-01T00:01:00Z", "h2", {})
            
            is_valid, errors = lineage.verify_chain()
            self.assertTrue(is_valid)
            self.assertEqual(errors, [])
    
    def test_tampered_chain_fails(self):
        """Tampered chain fails verification."""
        with tempfile.TemporaryDirectory() as tmpdir:
            lineage_path = os.path.join(tmpdir, "lineage.json")
            lineage = AMU0Lineage(lineage_path)
            
            lineage.append_entry("E1", "2025-01-01T00:00:00Z", "h1", {})
            
            # Tamper with entry
            lineage._entries[0].entry_hash = "TAMPERED"
            
            is_valid, errors = lineage.verify_chain()
            self.assertFalse(is_valid)
            self.assertTrue(len(errors) > 0)


if __name__ == '__main__':
    unittest.main()
