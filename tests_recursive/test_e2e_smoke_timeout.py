#!/usr/bin/env python3
"""
E2E Smoke Timeout Regression Tests
===================================

Exercises the mission timeout watchdog to prevent E2E hangs.
All tests are deterministic and do not rely on external services.
"""

import pytest
import threading
import time
import sys
import os
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.opencode_ci_runner import (
    run_with_timeout, MissionTimeout, stop_ephemeral_server
)


class TestMissionTimeout:
    """P0 — Mission timeout watchdog tests."""
    
    def test_fast_function_completes(self):
        """Function completing before timeout returns normally."""
        def fast():
            return "done"
        result = run_with_timeout(fast, 5)
        assert result == "done"
    
    def test_slow_function_times_out(self):
        """Function exceeding timeout raises MissionTimeout and releases thread."""
        stop_event = threading.Event()
        def slow():
            stop_event.wait(10) # Interruptible
            return "never"
        with pytest.raises(MissionTimeout):
            run_with_timeout(slow, 1)
        stop_event.set() # Release the thread
    
    def test_exception_propagates(self):
        """Exceptions inside wrapped function propagate."""
        def failing():
            raise ValueError("test error")
        with pytest.raises(ValueError, match="test error"):
            run_with_timeout(failing, 5)
    
    def test_timeout_message_includes_duration(self):
        """MissionTimeout message includes the timeout duration."""
        stop_event = threading.Event()
        def slow():
            stop_event.wait(10)
        try:
            with pytest.raises(MissionTimeout) as excinfo:
                run_with_timeout(slow, 2)
            assert "2s" in str(excinfo.value) or "2 " in str(excinfo.value)
        finally:
            stop_event.set()


class TestProcessGroupTermination:
    """P0.3 — Cross-platform process cleanup tests."""
    
    def test_stop_ephemeral_server_none_is_safe(self):
        """Calling with None does not raise."""
        stop_ephemeral_server(None)  # Should not raise
    
    def test_stop_ephemeral_server_terminates_process(self):
        """Process is terminated after stop call."""
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.terminate = MagicMock()
        mock_process.wait = MagicMock()
        mock_process.kill = MagicMock()
        
        # Patch subprocess.run to avoid actual taskkill/killpg calls
        with patch('subprocess.run') as mock_run, \
             patch('os.killpg' if os.name != 'nt' else 'os.getcwd') as mock_kill:
            mock_run.return_value = MagicMock(returncode=0)
            stop_ephemeral_server(mock_process)
        
        # Verify terminate was called
        mock_process.terminate.assert_called()
        mock_process.wait.assert_called()

if __name__ == "__main__":
    pytest.main([__file__])
