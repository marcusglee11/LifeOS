"""Tests for CND-1: Execution Envelope - Network Block"""
import unittest
import sys


class TestEnvelopeNetworkBlock(unittest.TestCase):
    """Test network restriction enforcement."""
    
    def test_network_module_detection(self):
        """Verify detection of network modules if loaded."""
        from runtime.envelope import ExecutionEnvelope, ExecutionEnvelopeError
        
        # Simulate network module load
        was_loaded = 'requests' in sys.modules
        if not was_loaded:
            sys.modules['requests'] = type(sys)('requests')
        
        try:
            envelope = ExecutionEnvelope()
            with self.assertRaises(ExecutionEnvelopeError):
                envelope.verify_network_restrictions()
        finally:
            if not was_loaded and 'requests' in sys.modules:
                del sys.modules['requests']
    
    def test_envelope_network_status(self):
        """Envelope reports network check status."""
        from runtime.envelope import ExecutionEnvelope
        
        envelope = ExecutionEnvelope()
        status = envelope.verify_all_soft()
        
        # Verify structure
        self.assertIsInstance(status.checks_passed, list)
        self.assertIsInstance(status.checks_failed, list)


if __name__ == '__main__':
    unittest.main()
