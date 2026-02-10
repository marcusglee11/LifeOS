
import unittest
from unittest.mock import patch, MagicMock
import sys
import json
import os
from pathlib import Path

# Add repo root to path to import script
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import the script module (assume it's importable)
# We might need to adjust if it's not a module, but we put it in scripts/
# For testing, we can use subprocess or try to import if __name__ main guard allows.
# Given it's a script, let's try to import it by loading source or similar, 
# but easiest is if it's just importable. Since it's in scripts/, not a package.
# Let's mock subprocess.run and test the logic functions if we can expose them.
# The script `scripts/git_workflow.py` has no classes, just functions. 

import scripts.git_workflow as gw

class TestGitWorkflow(unittest.TestCase):
    
    @patch('scripts.git_workflow.run_cmd')
    def test_branch_create_valid(self, mock_run):
        # Setup - Default for all calls
        mock_run.return_value = (0, "main", "") 
        
        # Execute
        with patch('scripts.git_workflow.update_active_branches') as mock_update:
            gw.cmd_branch_create("build/test-feature")
            
        # Verify
        # Should have pulled and checked out. 
        # calls: 1. symbolic-ref (get_curr), 2. symbolic-ref (check safe start main vs main), 
        # wait implementation checks if curr != main.
        # 3. git pull, 4. git checkout -b
        self.assertTrue(mock_run.call_count >= 2)
        # Check that checkout was called
        calls = [c[0][0] for c in mock_run.call_args_list]
        self.assertTrue(['git', 'checkout', '-b', 'build/test-feature'] in calls)

    @patch('scripts.git_workflow.sys.exit')
    @patch('scripts.git_workflow.run_cmd')
    def test_branch_create_invalid_name(self, mock_run, mock_exit):
        mock_run.return_value = (0, "", "")
        gw.cmd_branch_create("invalid-name")
        mock_exit.assert_called_with(1)

    @patch('scripts.git_workflow.sys.exit')
    @patch('scripts.git_workflow.run_cmd')
    def test_merge_block_no_gh(self, mock_run, mock_exit):
        mock_exit.side_effect = SystemExit
        
        # Define side effect to simulate run_cmd behavior + return values
        # 1. get_current_branch -> feature 
        # 2. get_head_sha -> sha
        # 3. gh version -> fail (simulating check=True behavior inside run_cmd)
        
        # We need to track calls or use iterator for return values, but conditionally raise
        # Easier: check args in side_effect
        
        call_iter = iter([
            (0, "build/feature", ""), 
            (0, "sha123", ""),
            # 3rd call will be intercepted
        ])
        
        def smart_side_effect(args, **kwargs):
            if args[0] == 'gh' and args[1] == '--version':
                # Simulate run_cmd failure behavior when check=True
                mock_exit(1)
                return (127, "", "Not found") # Should not be reached if mock_exit raises
            return next(call_iter)
            
        mock_run.side_effect = smart_side_effect
        
        with self.assertRaises(SystemExit):
            gw.cmd_merge()
        
        mock_exit.assert_called_with(1)

    @patch('scripts.git_workflow.write_json')
    @patch('scripts.git_workflow.run_cmd')
    def test_archive_receipt(self, mock_run, mock_write):
        # Mock branch exists
        mock_run.return_value = (0, "sha123", "")
        
        gw.cmd_branch_archive("build/old-one", "cleanup")
        
        # Verify receipt written - find the call that writes the receipt
        # write_json is called twice: once for receipt, once for active_branches
        found = False
        for call in mock_write.call_args_list:
            args, _ = call
            data = args[1]
            if data.get('protocol_version') == '1.1' and data.get('branch_name') == "build/old-one":
                found = True
                self.assertEqual(data['reason'], "cleanup")
                break
        self.assertTrue(found, "Receipt not written")

    @patch('scripts.git_workflow.write_json')
    @patch('scripts.git_workflow.run_cmd')
    def test_safety_preflight_destructive(self, mock_run, mock_write):
        # Mock exists
        with patch('os.path.exists', return_value=True):
            # Mock clean output
            mock_run.return_value = (0, "Would remove foo.txt", "")
            
            gw.cmd_safety_preflight("destructive")
            
            # Verify evidence
            self.assertTrue(mock_write.called)
            # destructive ops only writes once? No, it writes evidence.
            args, _ = mock_write.call_args
            evidence = args[1]
            self.assertEqual(evidence['op'], "git clean -fdX")

if __name__ == '__main__':
    unittest.main()
