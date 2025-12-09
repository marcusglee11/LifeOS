"""
FP-3.3: DAP Write Gateway Tests
Tests for boundary checks, naming enforcement, and index coherence.
"""
import unittest
import tempfile
import os
import shutil
from runtime.dap_gateway import DAPWriteGateway, DAPWriteError
from runtime.index.indexer import IndexReconciler


class TestDAPWriteGateway(unittest.TestCase):
    """
    3.3-FP: Tests for DAP Write Gateway.
    """
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.allowed_dir = os.path.join(self.temp_dir, "allowed")
        self.protected_dir = os.path.join(self.temp_dir, "protected")
        os.makedirs(self.allowed_dir)
        os.makedirs(self.protected_dir)
        
        self.gateway = DAPWriteGateway(
            allowed_roots=[self.allowed_dir],
            protected_paths=[self.protected_dir]
        )
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    # ========== Boundary Tests ==========
    
    def test_write_in_allowed_root(self):
        """Write within allowed root succeeds."""
        target = os.path.join(self.allowed_dir, "test_v1.0.md")
        self.gateway.write(target, "content")
        
        self.assertTrue(os.path.exists(target))
        with open(target, 'r') as f:
            self.assertEqual(f.read(), "content")
    
    def test_write_outside_boundary_raises(self):
        """Write outside allowed boundaries raises DAPWriteError."""
        target = os.path.join(self.temp_dir, "outside_v1.0.md")
        
        with self.assertRaises(DAPWriteError) as ctx:
            self.gateway.write(target, "content")
        
        self.assertIn("outside allowed boundaries", str(ctx.exception))
    
    def test_write_to_protected_raises(self):
        """Write to protected path raises DAPWriteError."""
        target = os.path.join(self.protected_dir, "protected_v1.0.md")
        
        with self.assertRaises(DAPWriteError) as ctx:
            self.gateway.write(target, "content")
        
        self.assertIn("protected path", str(ctx.exception))
    
    # ========== Validation Tests ==========
    
    def test_validate_without_write(self):
        """validate_write checks without writing."""
        target = os.path.join(self.allowed_dir, "test_v1.0.md")
        
        # Should not raise
        self.gateway.validate_write(target, "content")
        
        # File should not exist
        self.assertFalse(os.path.exists(target))
    
    def test_is_protected(self):
        """is_protected correctly identifies protected paths."""
        protected = os.path.join(self.protected_dir, "file.md")
        allowed = os.path.join(self.allowed_dir, "file.md")
        
        self.assertTrue(self.gateway.is_protected(protected))
        self.assertFalse(self.gateway.is_protected(allowed))
    
    def test_is_in_boundary(self):
        """is_in_boundary correctly identifies allowed paths."""
        allowed = os.path.join(self.allowed_dir, "file.md")
        outside = os.path.join(self.temp_dir, "file.md")
        
        self.assertTrue(self.gateway.is_in_boundary(allowed))
        self.assertFalse(self.gateway.is_in_boundary(outside))
    
    # ========== Binary Write Tests ==========
    
    def test_write_binary(self):
        """Binary write works correctly."""
        target = os.path.join(self.allowed_dir, "binary.bin")
        content = b"\x00\x01\x02\xff"
        
        self.gateway.write_binary(target, content)
        
        with open(target, 'rb') as f:
            self.assertEqual(f.read(), content)
    
    # ========== Naming Tests ==========
    
    def test_generate_versioned_name(self):
        """generate_versioned_name produces correct format."""
        name = DAPWriteGateway.generate_versioned_name("Document", 1, 0, "md")
        self.assertEqual(name, "Document_v1.0.md")
        
        name = DAPWriteGateway.generate_versioned_name("Config", 2, 3, "yaml")
        self.assertEqual(name, "Config_v2.3.yaml")
    
    # ========== Index Queue Tests ==========
    
    def test_pending_index_updates(self):
        """Writes queue index updates."""
        target = os.path.join(self.allowed_dir, "test_v1.0.md")
        self.gateway.write(target, "content")
        
        updates = self.gateway.flush_index_updates()
        self.assertEqual(len(updates), 1)
        self.assertIn(os.path.abspath(target), updates)
        
        # Second flush is empty
        updates = self.gateway.flush_index_updates()
        self.assertEqual(len(updates), 0)


class TestIndexReconciler(unittest.TestCase):
    """
    3.3-FP: Tests for Index Reconciler.
    """
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.index_path = os.path.join(self.temp_dir, "INDEX.md")
        self.reconciler = IndexReconciler(self.index_path, self.temp_dir)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_file(self, name: str, content: str = "content") -> str:
        path = os.path.join(self.temp_dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w') as f:
            f.write(content)
        return path
    
    def test_scan_directory(self):
        """scan_directory finds markdown files."""
        self._create_file("doc1.md")
        self._create_file("subdir/doc2.md")
        self._create_file("other.txt")
        
        files = self.reconciler.scan_directory()
        
        self.assertIn("doc1.md", files)
        self.assertIn("subdir/doc2.md", files)
        self.assertNotIn("other.txt", files)
    
    def test_generate_index_content(self):
        """generate_index_content produces correct markdown."""
        self._create_file("alpha.md")
        self._create_file("beta.md")
        
        content = self.reconciler.generate_index_content("Test Index")
        
        self.assertIn("# Test Index", content)
        self.assertIn("- [alpha.md](./alpha.md)", content)
        self.assertIn("- [beta.md](./beta.md)", content)
    
    def test_reconcile_creates_index(self):
        """reconcile creates index file."""
        self._create_file("doc.md")
        
        updated = self.reconciler.reconcile("My Index")
        
        self.assertTrue(updated)
        self.assertTrue(os.path.exists(self.index_path))
    
    def test_reconcile_no_change(self):
        """reconcile returns False when no change needed."""
        self._create_file("doc.md")
        
        self.reconciler.reconcile("Index")
        updated = self.reconciler.reconcile("Index")
        
        self.assertFalse(updated)
    
    def test_verify_coherence_pass(self):
        """verify_coherence passes when index matches files."""
        self._create_file("doc.md")
        self.reconciler.reconcile("Index")
        
        is_coherent, missing, orphaned = self.reconciler.verify_coherence()
        
        self.assertTrue(is_coherent)
        self.assertEqual(missing, [])
        self.assertEqual(orphaned, [])
    
    def test_verify_coherence_missing(self):
        """verify_coherence detects missing files."""
        self._create_file("doc.md")
        self.reconciler.reconcile("Index")
        
        # Add new file without updating index
        self._create_file("new.md")
        
        is_coherent, missing, orphaned = self.reconciler.verify_coherence()
        
        self.assertFalse(is_coherent)
        self.assertIn("new.md", missing)


if __name__ == '__main__':
    unittest.main()
