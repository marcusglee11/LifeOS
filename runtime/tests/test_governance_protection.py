"""
FP-3.9: Governance Protection Tests
Tests for protected artefact enforcement and autonomy ceilings.
"""
import unittest
import tempfile
import os
import json
import shutil
from runtime.governance.protection import (
    GovernanceProtector,
    GovernanceProtectionError,
    AutonomyCeiling,
    OperationScope
)


class TestGovernanceProtector(unittest.TestCase):
    """
    3.9-FP: Tests for Governance Protector.
    """
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.registry_path = os.path.join(self.temp_dir, "protected.json")
        
        # Create a test registry
        registry = {
            "protected_paths": [
                os.path.join(self.temp_dir, "protected"),
                os.path.join(self.temp_dir, "governance.md")
            ]
        }
        with open(self.registry_path, 'w') as f:
            json.dump(registry, f)
        
        self.protector = GovernanceProtector(self.registry_path)
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    # ========== Protected Path Tests ==========
    
    def test_is_protected_exact_match(self):
        """Exact path match is protected."""
        path = os.path.join(self.temp_dir, "governance.md")
        self.assertTrue(self.protector.is_protected(path))
    
    def test_is_protected_subdirectory(self):
        """File in protected directory is protected."""
        path = os.path.join(self.temp_dir, "protected", "secret.md")
        self.assertTrue(self.protector.is_protected(path))
    
    def test_is_not_protected(self):
        """Non-protected path is not protected."""
        path = os.path.join(self.temp_dir, "allowed", "file.md")
        self.assertFalse(self.protector.is_protected(path))
    
    def test_validate_write_allowed(self):
        """Write to non-protected path succeeds."""
        path = os.path.join(self.temp_dir, "allowed.md")
        # Should not raise
        self.protector.validate_write(path)
    
    def test_validate_write_protected_raises(self):
        """Write to protected path raises error."""
        path = os.path.join(self.temp_dir, "governance.md")
        
        with self.assertRaises(GovernanceProtectionError) as ctx:
            self.protector.validate_write(path)
        
        self.assertIn("protected path", str(ctx.exception))
    
    # ========== Add/Remove Protected Paths ==========
    
    def test_add_protected_path(self):
        """Add new protected path."""
        path = os.path.join(self.temp_dir, "new_protected")
        
        self.assertFalse(self.protector.is_protected(path))
        self.protector.add_protected_path(path)
        self.assertTrue(self.protector.is_protected(path))
    
    def test_remove_protected_path(self):
        """Remove protected path."""
        path = os.path.join(self.temp_dir, "governance.md")
        
        self.assertTrue(self.protector.is_protected(path))
        self.protector.remove_protected_path(path)
        self.assertFalse(self.protector.is_protected(path))
    
    # ========== Autonomy Ceiling Tests ==========
    
    def test_validate_scope_within_ceiling(self):
        """Scope within ceiling is valid."""
        scope = OperationScope(
            files_modified={"a.py", "b.py"},
            directories_modified={"dir1"},
            protected_violations=[]
        )
        
        is_valid, violations = self.protector.validate_operation_scope(scope)
        
        self.assertTrue(is_valid)
        self.assertEqual(violations, [])
    
    def test_validate_scope_exceeds_files(self):
        """Scope exceeding file ceiling is invalid."""
        ceiling = AutonomyCeiling(max_files_modified=5)
        self.protector.set_autonomy_ceiling(ceiling)
        
        scope = OperationScope(
            files_modified={f"file{i}.py" for i in range(10)},
            directories_modified=set(),
            protected_violations=[]
        )
        
        is_valid, violations = self.protector.validate_operation_scope(scope)
        
        self.assertFalse(is_valid)
        self.assertTrue(any("Files modified" in v for v in violations))
    
    def test_validate_scope_exceeds_directories(self):
        """Scope exceeding directory ceiling is invalid."""
        ceiling = AutonomyCeiling(max_directories_modified=2)
        self.protector.set_autonomy_ceiling(ceiling)
        
        scope = OperationScope(
            files_modified=set(),
            directories_modified={"d1", "d2", "d3", "d4"},
            protected_violations=[]
        )
        
        is_valid, violations = self.protector.validate_operation_scope(scope)
        
        self.assertFalse(is_valid)
        self.assertTrue(any("Directories modified" in v for v in violations))
    
    def test_validate_scope_protected_violations(self):
        """Scope with protected violations is invalid."""
        scope = OperationScope(
            files_modified=set(),
            directories_modified=set(),
            protected_violations=["protected/file.md"]
        )
        
        is_valid, violations = self.protector.validate_operation_scope(scope)
        
        self.assertFalse(is_valid)
        self.assertTrue(any("Protected paths" in v for v in violations))
    
    def test_validate_scope_or_raise(self):
        """validate_operation_scope_or_raise raises on violation."""
        ceiling = AutonomyCeiling(max_files_modified=1)
        self.protector.set_autonomy_ceiling(ceiling)
        
        scope = OperationScope(
            files_modified={"a.py", "b.py", "c.py"},
            directories_modified=set(),
            protected_violations=[]
        )
        
        with self.assertRaises(GovernanceProtectionError):
            self.protector.validate_operation_scope_or_raise(scope)
    
    # ========== Mission Validation Tests ==========
    
    def test_validate_mission_scope_valid(self):
        """Mission within ceiling is valid."""
        mission = {
            "safety": {
                "autonomy_ceiling": {
                    "max_files_modified": 10,
                    "max_directories_modified": 3
                }
            }
        }
        
        is_valid, violations = self.protector.validate_mission_scope(mission)
        
        self.assertTrue(is_valid)
    
    def test_validate_mission_scope_exceeds_ceiling(self):
        """Mission exceeding ceiling is invalid."""
        ceiling = AutonomyCeiling(max_files_modified=20)
        self.protector.set_autonomy_ceiling(ceiling)
        
        mission = {
            "safety": {
                "autonomy_ceiling": {
                    "max_files_modified": 50
                }
            }
        }
        
        is_valid, violations = self.protector.validate_mission_scope(mission)
        
        self.assertFalse(is_valid)
        self.assertTrue(any("max_files_modified" in v for v in violations))
    
    # ========== Registry Persistence ==========
    
    def test_save_registry(self):
        """Save registry to file."""
        self.protector.add_protected_path("/new/path")
        save_path = os.path.join(self.temp_dir, "saved.json")
        
        self.protector.save_registry(save_path)
        
        self.assertTrue(os.path.exists(save_path))
        with open(save_path, 'r') as f:
            data = json.load(f)
        self.assertIn("/new/path", data["protected_paths"])
    
    def test_get_protected_paths(self):
        """get_protected_paths returns copy of paths."""
        paths = self.protector.get_protected_paths()
        
        self.assertEqual(len(paths), 2)
        
        # Modifying returned list doesn't affect internal state
        paths.append("new_path")
        self.assertEqual(len(self.protector.get_protected_paths()), 2)
    
    # ========== Initialize Without Registry ==========
    
    def test_init_without_registry(self):
        """Initialize without registry file."""
        protector = GovernanceProtector()
        
        # Should not raise
        self.assertFalse(protector.is_protected("/any/path"))


if __name__ == '__main__':
    unittest.main()
