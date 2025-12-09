"""Tests for CND-3: Governance Surface Immutability"""
import unittest
import tempfile
import os
import json


class TestGovernanceSurfaceImmutable(unittest.TestCase):
    """Test governance surface validation."""
    
    def test_valid_surfaces_pass(self):
        """Unmodified surfaces pass validation."""
        from runtime.governance.surface_validator import validate_governance_surfaces
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create manifest
            manifest = {"surfaces": [], "immutable": True}
            manifest_path = os.path.join(tmpdir, "manifest.json")
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f)
            
            is_valid, errors = validate_governance_surfaces(tmpdir, manifest_path)
            self.assertTrue(is_valid)
    
    def test_missing_surface_fails(self):
        """Missing governance surface fails validation."""
        from runtime.governance.surface_validator import validate_governance_surfaces
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest = {
                "surfaces": [{"path": "missing.py", "protected": True}]
            }
            manifest_path = os.path.join(tmpdir, "manifest.json")
            with open(manifest_path, 'w') as f:
                json.dump(manifest, f)
            
            is_valid, errors = validate_governance_surfaces(tmpdir, manifest_path)
            self.assertFalse(is_valid)
            self.assertTrue(any("Missing" in e for e in errors))


if __name__ == '__main__':
    unittest.main()
