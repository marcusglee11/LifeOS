"""
Test Sandbox Capabilities
========================
Verifies that the ExecutionEnvelope correctly relaxes constraints in 'sandbox' mode.
"""
import pytest
import sys
import unittest.mock
from runtime.envelope.execution_envelope import ExecutionEnvelope, ExecutionEnvelopeError

def test_sandbox_allows_multiprocessing_check():
    """
    Verify that sandbox mode allows the verification check even if banned modules are loaded.
    Note: We mock sys.modules to simulate banned modules being present.
    """
    with unittest.mock.patch.dict(sys.modules, {'multiprocessing': unittest.mock.Mock()}):
        # Strict mode should fail
        env_strict = ExecutionEnvelope(mode='tier2')
        with pytest.raises(ExecutionEnvelopeError, match="Banned multiprocessing modules"):
            env_strict.verify_single_process()

        # Sandbox mode should pass
        env_sandbox = ExecutionEnvelope(mode='sandbox')
        env_sandbox.verify_single_process()
        assert 'single_process_skipped_sandbox' in env_sandbox._checks_passed

def test_sandbox_allows_writes(tmp_path):
    """
    Verify that we can write files (mostly a sanity check that no other mechanism blocks it).
    Using pytest's tmp_path.
    """
    # This is implicit, as we haven't implemented a filesystem envelope, 
    # but we want to ensure the environment allows it.
    p = tmp_path / "test__sandbox_write.txt"
    p.write_text("hello sandbox")
    assert p.read_text() == "hello sandbox"

def test_network_still_restricted_in_sandbox():
    """
    Verify that sandbox mode DOES NOT restrict network checks (unless we decided to relax them too).
    Current plan says: "Maintain safety invariants (no network)".
    So network checks should still run.
    """
    with unittest.mock.patch.dict(sys.modules, {'requests': unittest.mock.Mock()}):
        env_sandbox = ExecutionEnvelope(mode='sandbox')
        with pytest.raises(ExecutionEnvelopeError, match="Direct network modules detected"):
            env_sandbox.verify_network_restrictions()
