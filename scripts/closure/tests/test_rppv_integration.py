
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# Import the module under test
# We need to add repo_root to sys.path if not present
sys.path.append(str(Path.cwd()))
from scripts.closure import build_closure_bundle

class TestRPPVIntegration(unittest.TestCase):
    @patch('scripts.closure.build_closure_bundle.run_command_capture')
    @patch('scripts.closure.build_closure_bundle.calculate_sha256')
    @patch('scripts.closure.build_closure_bundle.get_git_commit')
    @patch('pathlib.Path.glob')
    @patch('builtins.open')
    @patch('os.getcwd')
    @patch('zipfile.ZipFile')
    @patch('shutil.rmtree')
    @patch('pathlib.Path.mkdir')
    def test_rppv_hook_invocation(self, mock_mkdir, mock_rmtree, mock_zip, mock_getcwd, 
                                 mock_open, mock_glob, mock_commit, mock_sha, mock_run):
        """Verify RPPV builder is invoked in repayment mode."""
        
        # Setup mocks
        mock_commit.return_value = "commit123"
        mock_getcwd.return_value = "/repo"
        mock_sha.return_value = "sha123"
        
        # Mock glob to return a fake zip
        mock_zip_path = MagicMock()
        mock_zip_path.name = "return_packet_123.zip"
        mock_glob.return_value = [mock_zip_path]
        
        # Args
        args = MagicMock()
        args.profile = "test_profile"
        args.closure_id = "test_closure"
        args.output = "bundle.zip"
        args.repayment_mode = True  # KEY: Enables G3/RPPV
        args.deterministic = True
        args.include = None
        
        # Patch argparse
        with patch('argparse.ArgumentParser.parse_args', return_value=args):
             # Run main
             # We expect it might fail later due to complex filesystem mocks, 
             # but we only care about the subprocess call.
             try:
                 build_closure_bundle.main()
             except SystemExit:
                 pass
             except Exception:
                 pass
                 
        # Verify RPPV invocation
        # Look for the command list in the mock_run calls
        rppv_called = False
        for call in mock_run.call_args_list:
            cmd_list = call[0][0]
            if "scripts.packaging.build_return_packet" in cmd_list:
                rppv_called = True
                break
        
        self.assertTrue(rppv_called, "RPPV builder should be invoked in repayment_mode")

if __name__ == '__main__':
    unittest.main()
