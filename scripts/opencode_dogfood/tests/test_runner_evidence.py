import unittest
import json
import shutil
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# We will import run_suite main to test it, or mock subprocess?
# Better to test logic or minimal run.
# Let's import lib and maybe just check if we can invoke run_suite on a single case safely.

from scripts.opencode_dogfood import run_suite, lib

class TestRunnerEvidence(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.original_cwd = Path.cwd()
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_mandatory_evidence_captured(self):
        """Assert runner captures repo_commit.txt and worktree_check.txt for every case."""
        # We need to simulate a run of a simple case (T1C01)
        # We can mock the subprocess calls to avoid actual execution overhead/network.
        
        args = MagicMock()
        args.dry_run = False
        args.case = "T1C01" 
        args.stages = None
        args.fail_fast = False
        
        # We need to patch:
        # 1. argparse.parse_args -> return our mock
        # 2. subprocess.run -> return exit 0
        # 3. subprocess.check_output -> return dummy strings
        # 4. run_suite.SCENARIOS -> just T1C01 to be fast
        
        with patch("scripts.opencode_dogfood.run_suite.argparse.ArgumentParser.parse_args", return_value=args), \
             patch("subprocess.run") as mock_run, \
             patch("subprocess.check_output") as mock_check_output, \
             patch("scripts.opencode_dogfood.run_suite.SCENARIOS", [{"case_id": "T1C01", "stage": "T1", "cmd": "echo ok", "pass_criteria": "exit_zero", "expected_outcome": "SUCCESS"}]):
             
            # Mock outputs
            mock_run.return_value.returncode = 0
            mock_check_output.return_value = "a" * 40
            
            # Use our temp dir as repo root so artifacts are written there?
            # run_suite uses Path.cwd(). We can chdir or patch repo_root.
            # run_suite.main() calculates repo_root = Path.cwd()
            
            # Patch CWD
            with patch("pathlib.Path.cwd", return_value=self.test_dir):
                 # also we need to patch os.environ LC_ALL etc or let it set
                 with self.assertRaises(SystemExit) as cm:
                     run_suite.main()
                 self.assertEqual(cm.exception.code, 0)
                 
            # Now check artifacts
            # run_id unknown... scan the dir
            ledger = self.test_dir / "artifacts/ledger/opencode_dogfood"
            self.assertTrue(ledger.exists(), "Ledger dir not created")
            run_dirs = list(ledger.glob("RUN_*"))
            self.assertTrue(len(run_dirs) > 0, "No run dir created")
            run_dir = run_dirs[0]
            
            evidence_dir = run_dir / "evidence/T1C01"
            self.assertTrue(evidence_dir.exists(), "Evidence dir for T1C01 not created")
            
            # CHECK MANDATORY FILES
            self.assertTrue((evidence_dir / "repo_commit.txt").exists(), "repo_commit.txt missing")
            self.assertTrue((evidence_dir / "repo_commit.txt.sha256").exists(), "repo_commit.txt.sha256 missing")
            
            self.assertTrue((evidence_dir / "worktree_check.txt").exists(), "worktree_check.txt missing")
            self.assertTrue((evidence_dir / "worktree_check.txt.sha256").exists(), "worktree_check.txt.sha256 missing")
            
            # verify content
            self.assertEqual((evidence_dir / "repo_commit.txt").read_text().strip(), "a" * 40)

if __name__ == "__main__":
    unittest.main()
