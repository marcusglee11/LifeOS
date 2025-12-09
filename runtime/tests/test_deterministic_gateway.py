"""Tests for CND-1: Deterministic Gateway"""
import unittest
import tempfile
import os
import json

from runtime.gateway import (
    DeterministicGateway, DeterministicCallError,
    CallSpec, deterministic_call
)


class TestDeterministicGateway(unittest.TestCase):
    """Test deterministic call gateway."""
    
    def test_valid_spec_accepted(self):
        """Valid call specs are accepted."""
        gateway = DeterministicGateway()
        spec = CallSpec(kind="subprocess", target="echo", args={"text": "hello"})
        gateway.validate_spec(spec)
    
    def test_invalid_kind_rejected(self):
        """Invalid call kinds are rejected."""
        gateway = DeterministicGateway()
        spec = CallSpec(kind="invalid", target="test", args={})
        
        with self.assertRaises(DeterministicCallError):
            gateway.validate_spec(spec)
    
    def test_non_serializable_args_rejected(self):
        """Non-JSON-serializable args are rejected."""
        gateway = DeterministicGateway()
        spec = CallSpec(kind="subprocess", target="test", args={"fn": lambda x: x})
        
        with self.assertRaises(DeterministicCallError):
            gateway.validate_spec(spec)
    
    def test_call_returns_stub(self):
        """Tier-1 calls return stub result."""
        result = deterministic_call("subprocess", "echo", {"text": "test"})
        
        self.assertTrue(result.success)
        self.assertTrue(result.output.get("stub"))
    
    def test_ledger_logging(self):
        """Calls are logged to ledger."""
        with tempfile.TemporaryDirectory() as tmpdir:
            ledger_path = os.path.join(tmpdir, "ledger.json")
            gateway = DeterministicGateway(ledger_path=ledger_path)
            
            spec = CallSpec(kind="subprocess", target="test", args={})
            gateway.call(spec)
            
            with open(ledger_path, 'r') as f:
                ledger = json.load(f)
            
            self.assertEqual(len(ledger), 1)
            self.assertIn("call_hash", ledger[0])


if __name__ == '__main__':
    unittest.main()
