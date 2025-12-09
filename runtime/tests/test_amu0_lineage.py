"""
FP-3.2: AMU₀ State Lineage Tests
Tests for create, restore, promote operations and byte-level integrity.
"""
import unittest
import tempfile
import os
import json
import shutil
from runtime.state.amu0 import AMU0Manager, AMU0Error


class TestAMU0Lineage(unittest.TestCase):
    """
    3.2-FP-2: Tests for AMU₀ discipline and state lineage.
    """
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_root = os.path.join(self.temp_dir, "state")
        self.manager = AMU0Manager(self.state_root)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def _create_test_file(self, name: str, content: str) -> str:
        """Create a test file and return its path."""
        path = os.path.join(self.temp_dir, name)
        with open(path, "w") as f:
            f.write(content)
        return path
    
    # ========== create_amu0_baseline Tests ==========
    
    def test_create_baseline_single_file(self):
        """Create baseline with a single file."""
        test_file = self._create_test_file("test.txt", "hello world")
        
        baseline_path = self.manager.create_amu0_baseline(
            "TEST",
            [test_file],
            timestamp="2025-01-01T00:00:00Z"
        )
        
        self.assertTrue(os.path.exists(baseline_path))
        self.assertTrue(os.path.exists(os.path.join(baseline_path, "amu0_manifest.json")))
        self.assertTrue(os.path.exists(os.path.join(baseline_path, "amu0_manifest.sha256")))
    
    def test_create_baseline_duplicate_raises(self):
        """Creating duplicate baseline raises AMU0Error."""
        test_file = self._create_test_file("test.txt", "content")
        
        self.manager.create_amu0_baseline(
            "DUPLICATE", 
            [test_file],
            timestamp="2025-01-01T00:00:00Z"
        )
        
        with self.assertRaises(AMU0Error):
            self.manager.create_amu0_baseline(
                "DUPLICATE", 
                [test_file],
                timestamp="2025-01-01T00:00:00Z"
            )

    def test_create_baseline_missing_timestamp_raises(self):
        """Missing timestamp raises AMU0Error."""
        test_file = self._create_test_file("test.txt", "content")
        
        with self.assertRaisesRegex(AMU0Error, "Timestamp must be explicitly provided"):
            self.manager.create_amu0_baseline("NO_TIME", [test_file], timestamp="")
    
    def test_create_baseline_manifest_integrity(self):
        """Manifest checksum is computed correctly."""
        test_file = self._create_test_file("test.txt", "content")
        baseline_path = self.manager.create_amu0_baseline(
            "MANIFEST", 
            [test_file],
            timestamp="2025-01-01T00:00:00Z"
        )
        
        manifest_path = os.path.join(baseline_path, "amu0_manifest.json")
        checksum_path = os.path.join(baseline_path, "amu0_manifest.sha256")
        
        import hashlib
        with open(manifest_path, "rb") as f:
            actual_hash = hashlib.sha256(f.read()).hexdigest()
        
        with open(checksum_path, "r") as f:
            stored_hash = f.read().strip()
        
        self.assertEqual(actual_hash, stored_hash)
    
    # ========== restore_from_amu0 Tests ==========
    
    def test_restore_from_baseline(self):
        """Restore files from a baseline."""
        test_file = self._create_test_file("restore_test.txt", "restore me")
        self.manager.create_amu0_baseline(
            "RESTORE", 
            [test_file],
            timestamp="2025-01-01T00:00:00Z"
        )
        
        restore_dir = os.path.join(self.temp_dir, "restored")
        self.manager.restore_from_amu0("RESTORE", restore_dir)
        
        restored_file = os.path.join(restore_dir, "restore_test.txt")
        self.assertTrue(os.path.exists(restored_file))
        
        with open(restored_file, "r") as f:
            self.assertEqual(f.read(), "restore me")
    
    def test_restore_byte_identical(self):
        """Restored files are byte-identical to originals."""
        content = b"\x00\x01\x02\xff\xfe\xfd"
        binary_path = os.path.join(self.temp_dir, "binary.bin")
        with open(binary_path, "wb") as f:
            f.write(content)
        
        self.manager.create_amu0_baseline(
            "BINARY", 
            [binary_path],
            timestamp="2025-01-01T00:00:00Z"
        )
        
        restore_dir = os.path.join(self.temp_dir, "binary_restored")
        self.manager.restore_from_amu0("BINARY", restore_dir)
        
        restored_path = os.path.join(restore_dir, "binary.bin")
        with open(restored_path, "rb") as f:
            restored_content = f.read()
        
        self.assertEqual(content, restored_content)
    
    def test_restore_nonexistent_raises(self):
        """Restoring nonexistent baseline raises AMU0Error."""
        with self.assertRaises(AMU0Error):
            self.manager.restore_from_amu0("NONEXISTENT", self.temp_dir)
    
    # ========== promote_run_to_amu0 Tests ==========
    
    def test_promote_run(self):
        """Promote a run directory to baseline."""
        run_dir = os.path.join(self.temp_dir, "run")
        os.makedirs(run_dir)
        with open(os.path.join(run_dir, "output.txt"), "w") as f:
            f.write("run output")
        
        baseline_path = self.manager.promote_run_to_amu0(
            run_dir, 
            "NEW",
            timestamp="2025-01-01T00:00:00Z"
        )
        
        self.assertTrue(os.path.exists(baseline_path))
        self.assertTrue(self.manager.verify_baseline("NEW"))
    
    def test_promote_nonexistent_raises(self):
        """Promoting nonexistent run directory raises AMU0Error."""
        with self.assertRaises(AMU0Error):
            self.manager.promote_run_to_amu0(
                "/nonexistent/path", 
                "FAIL",
                timestamp="2025-01-01T00:00:00Z"
            )
    
    # ========== verify_baseline Tests ==========
    
    def test_verify_valid_baseline(self):
        """Valid baseline passes verification."""
        test_file = self._create_test_file("verify.txt", "verify me")
        self.manager.create_amu0_baseline(
            "VERIFY", 
            [test_file],
            timestamp="2025-01-01T00:00:00Z"
        )
        
        self.assertTrue(self.manager.verify_baseline("VERIFY"))
    
    def test_verify_corrupted_manifest_fails(self):
        """Corrupted manifest fails verification."""
        test_file = self._create_test_file("corrupt.txt", "content")
        baseline_path = self.manager.create_amu0_baseline(
            "CORRUPT", 
            [test_file],
            timestamp="2025-01-01T00:00:00Z"
        )
        
        # Corrupt the manifest
        manifest_path = os.path.join(baseline_path, "amu0_manifest.json")
        with open(manifest_path, "a") as f:
            f.write("corruption")
        
        self.assertFalse(self.manager.verify_baseline("CORRUPT"))
    
    def test_verify_nonexistent_fails(self):
        """Nonexistent baseline fails verification."""
        self.assertFalse(self.manager.verify_baseline("DOES_NOT_EXIST"))
    
    # ========== list_baselines Tests ==========
    
    def test_list_baselines(self):
        """List all baselines."""
        test_file = self._create_test_file("list.txt", "content")
        self.manager.create_amu0_baseline("ALPHA", [test_file], timestamp="2025-01-01T00:00:00Z")
        self.manager.create_amu0_baseline("BETA", [test_file], timestamp="2025-01-01T00:00:00Z")
        
        baselines = self.manager.list_baselines()
        
        self.assertIn("ALPHA", baselines)
        self.assertIn("BETA", baselines)
        self.assertEqual(len(baselines), 2)
    
    # ========== Determinism Tests ==========
    
    def test_create_restore_deterministic(self):
        """Create and restore produces byte-identical results."""
        test_content = "deterministic content 123"
        results = []
        
        for i in range(3):
            test_file = self._create_test_file(f"det_{i}.txt", test_content)
            self.manager.create_amu0_baseline(
                f"DET_{i}",
                [test_file],
                timestamp="2025-01-01T00:00:00Z"
            )
            
            restore_dir = os.path.join(self.temp_dir, f"det_restore_{i}")
            self.manager.restore_from_amu0(f"DET_{i}", restore_dir)
            
            restored_file = os.path.join(restore_dir, f"det_{i}.txt")
            with open(restored_file, "r") as f:
                results.append(f.read())
        
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])


if __name__ == '__main__':
    unittest.main()
