"""Tests for CND-5: Safety Halt Procedure"""
import unittest
import tempfile
import os
import json

from runtime.safety.halt import find_last_good_snapshot, rollback_to_snapshot


class TestSafetyHaltProcedure(unittest.TestCase):
    """Test halt and rollback functionality."""
    
    def test_find_last_good_snapshot(self):
        """Find last good snapshot in AMU0 root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create snapshot directory
            snapshot_dir = os.path.join(tmpdir, "snapshots", "snap_001")
            os.makedirs(snapshot_dir)
            with open(os.path.join(snapshot_dir, "amu0_manifest.json"), 'w') as f:
                json.dump({"version": "1.0"}, f)
            
            result = find_last_good_snapshot(tmpdir)
            self.assertIsNotNone(result)
            self.assertIn("snap_001", result)
    
    def test_find_no_snapshot(self):
        """No snapshot found returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = find_last_good_snapshot(tmpdir)
            self.assertIsNone(result)
    
    def test_rollback_to_snapshot(self):
        """Rollback restores snapshot to current state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create snapshot
            snapshot = os.path.join(tmpdir, "snapshot")
            os.makedirs(snapshot)
            with open(os.path.join(snapshot, "data.json"), 'w') as f:
                json.dump({"state": "good"}, f)
            
            # Create current state
            current = os.path.join(tmpdir, "current")
            os.makedirs(current)
            with open(os.path.join(current, "data.json"), 'w') as f:
                json.dump({"state": "bad"}, f)
            
            # Rollback
            result = rollback_to_snapshot(current, snapshot)
            self.assertTrue(result)
            
            # Verify
            with open(os.path.join(current, "data.json"), 'r') as f:
                data = json.load(f)
            self.assertEqual(data["state"], "good")


if __name__ == '__main__':
    unittest.main()
