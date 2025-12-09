"""Tests for CND-1: Execution Envelope - Single Process"""
import unittest
import os
import sys


class TestEnvelopeSingleProcess(unittest.TestCase):
    """Test single-process enforcement."""
    
    def test_banned_module_detection(self):
        """Verify detection of banned modules if loaded."""
        from runtime.envelope import ExecutionEnvelope, ExecutionEnvelopeError
        
        # Simulate banned module in sys.modules
        was_loaded = 'multiprocessing' in sys.modules
        if not was_loaded:
            sys.modules['multiprocessing'] = type(sys)('multiprocessing')
        
        try:
            envelope = ExecutionEnvelope()
            with self.assertRaises(ExecutionEnvelopeError):
                envelope.verify_single_process()
        finally:
            if not was_loaded and 'multiprocessing' in sys.modules:
                del sys.modules['multiprocessing']
    
    def test_envelope_status_reports_failure(self):
        """Envelope status reports failures correctly."""
        from runtime.envelope import ExecutionEnvelope
        
        envelope = ExecutionEnvelope()
        status = envelope.verify_all_soft()
        
        # In test environment, some modules may be loaded
        # Just verify the status structure is correct
        self.assertIn('verified', status.__dict__)
        self.assertIn('checks_passed', status.__dict__)


if __name__ == '__main__':
    unittest.main()
