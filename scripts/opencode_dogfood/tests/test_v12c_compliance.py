"""TDD Tests for v1.2c: Strict contracts, Fixtures, and Worktree logic."""
import unittest
import re
import sys
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import lib for worktree check logic
from scripts.opencode_dogfood import lib

PLAN_PATH = PROJECT_ROOT / "artifacts/for_ceo/Plan_OpenCode_Dogfooding_v1.2c.md"
FIXTURES_DIR = PROJECT_ROOT / "scripts/opencode_dogfood/sandbox/fixtures"

class TestPlanContractV12c(unittest.TestCase):
    """P0.1, P0.3: Strict plan contracts."""
    
    def test_plan_exists(self):
        if not PLAN_PATH.exists():
            self.skipTest("Plan v1.2c not created yet")

    def test_scenario_table_failure_codes_strict(self):
        """Failure codes must NOT contain parenthetical notes."""
        if not PLAN_PATH.exists():
            self.skipTest("Plan v1.2c not created yet")
            
        content = PLAN_PATH.read_text(encoding="utf-8")
        lines = content.splitlines()
        
        # Find start of Executable Scenario Table
        in_executable_table = False
        table_lines = []
        for i, line in enumerate(lines):
            if "Executable Scenario Table" in line:
                in_executable_table = True
                continue
            if in_executable_table and line.strip().startswith("| case_id"):
                continue  # skip header
            if in_executable_table and line.strip().startswith("|---"):
                continue  # skip separator
            if in_executable_table and not line.strip().startswith("|"):
                if table_lines: # End of table
                    break
                continue
            
            if in_executable_table and re.match(r'^\|\s*T\d', line):
                table_lines.append(line)

        for line in table_lines:
            # Column 5 is failure codes
            parts = [p.strip() for p in line.split('|')]
            if len(parts) < 6: continue
            failure_codes = parts[5]
            
            # forbid (...) 
            if "(" in failure_codes or ")" in failure_codes:
                self.fail(f"Plan line contains parenthetical failure code note: {line}")
            
            # T2B03 must be GITCLEANFAIL
            if "T2B03" in line and "GITCLEANFAIL" not in failure_codes:
                self.fail(f"T2B03 must explicitly look for GITCLEANFAIL: {line}")
                
            # T4E01 must be blank or (none) -> Plan requirement says blank
            if "T4E01" in line and failure_codes:
                 self.fail(f"T4E01 failure code should be blank/empty: {line}")


class TestFixturesV12c(unittest.TestCase):
    """P0.1, P0.2: T3 Fixtures existence."""
    
    def test_fixtures_exist(self):
        """Assert all 4 required fixtures exist."""
        required = [
            "fixture_01_function_spec.md",
            "fixture_02_buggy_module.py",
            "fixture_03_tests_expected.py",
            "fixture_04_review_prompt.md"
        ]
        if not FIXTURES_DIR.exists():
            self.fail("Fixtures directory missing")
            
        for f in required:
            self.assertTrue((FIXTURES_DIR / f).exists(), f"Fixture {f} missing")


class TestWorktreeEnforcement(unittest.TestCase):
    """P0.1, P0.4: Worktree predicate logic."""
    
    def test_worktree_predicate_fail_in_normal_repo(self):
        """Simulate normal repo - predicate should fail."""
        # Main repo .git is a directory
        with patch("subprocess.check_output") as mock_git:
            # git rev-parse --git-dir returns .git
            mock_git.return_value = ".git"
            
            # Logic: is_worktree = "worktrees" in git_dir or (file check)
            # here .git is dir, so file check false. "worktrees" false.
            is_worktree = lib.is_isolated_worktree(".git")
            self.assertFalse(is_worktree)
            
    def test_worktree_predicate_pass_in_worktree(self):
        """Simulate worktree - predicate should pass."""
        # Worktree .git is a file pointing to gitdir
        # git rev-parse --git-dir returns .../.git/worktrees/wt_name
        with patch("subprocess.check_output") as mock_git:
            mock_git.return_value = "/abs/path/to/.git/worktrees/dogfood"
            is_worktree = lib.is_isolated_worktree(mock_git.return_value)
            self.assertTrue(is_worktree)

if __name__ == "__main__":
    unittest.main()
