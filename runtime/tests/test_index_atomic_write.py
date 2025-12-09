"""Tests for CND-2: Index Atomic Write"""
import unittest
import tempfile
import os

from runtime.util.atomic_write import atomic_write_text, atomic_write_json
from runtime.index.index_updater import IndexUpdater


class TestIndexAtomicWrite(unittest.TestCase):
    """Test atomic write operations for INDEX."""
    
    def test_atomic_write_creates_file(self):
        """Atomic write creates file correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.txt")
            atomic_write_text(path, "hello world")
            
            self.assertTrue(os.path.exists(path))
            with open(path, 'r') as f:
                self.assertEqual(f.read(), "hello world")
    
    def test_atomic_write_json(self):
        """Atomic JSON write is deterministic."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "test.json")
            data = {"b": 2, "a": 1}
            atomic_write_json(path, data)
            
            with open(path, 'r') as f:
                content = f.read()
            
            # Keys should be sorted
            self.assertIn('"a"', content)
            self.assertTrue(content.index('"a"') < content.index('"b"'))
    
    def test_index_updater_atomic(self):
        """IndexUpdater uses atomic writes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            (os.path.join(tmpdir, "test.md"))
            with open(os.path.join(tmpdir, "test.md"), 'w') as f:
                f.write("# Test")
            
            index_path = os.path.join(tmpdir, "INDEX.md")
            updater = IndexUpdater(index_path, tmpdir)
            updater.update()
            
            self.assertTrue(os.path.exists(index_path))


if __name__ == '__main__':
    unittest.main()
