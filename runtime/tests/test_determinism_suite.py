"""
FP-3.1: Determinism Suite
Tests for byte-identical outputs across multiple runs.
Validates no nondeterministic sources exist in runtime.
"""
import unittest
import hashlib
import tempfile
import os
import json
from runtime.engine import RuntimeFSM, RuntimeState, GovernanceError


class TestDeterminismSuite(unittest.TestCase):
    """
    3.1-FP-1: Determinism tests that run canonical operations
    and verify byte-level identical outputs.
    """

    def test_fsm_state_sequence_deterministic(self):
        """Verify FSM state sequences are identical across runs."""
        results = []
        for _ in range(3):
            fsm = RuntimeFSM(strict_mode=False)
            fsm.transition_to(RuntimeState.AMENDMENT_PREP)
            fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
            fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
            results.append(tuple(fsm.history))
        
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[1], results[2])

    def test_fsm_error_message_deterministic(self):
        """Verify error messages are identical across runs."""
        error_messages = []
        for _ in range(3):
            fsm = RuntimeFSM(strict_mode=False)
            try:
                fsm.transition_to(RuntimeState.COMPLETE)  # Invalid
            except GovernanceError as e:
                error_messages.append(str(e))
        
        self.assertEqual(error_messages[0], error_messages[1])
        self.assertEqual(error_messages[1], error_messages[2])

    def test_checkpoint_content_deterministic(self):
        """Verify checkpoint file contents are identical across runs."""
        checksums = []
        for i in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                amu0_path = os.path.join(tmpdir, "amu0")
                os.makedirs(os.path.join(amu0_path, "checkpoints"), exist_ok=True)
                
                # Create pinned_context.json required by checkpoint_state
                pinned_context = {"mock_time": "2025-01-01T00:00:00Z"}
                with open(os.path.join(amu0_path, "pinned_context.json"), "w") as f:
                    json.dump(pinned_context, f)
                
                # strict_mode=True required for CEO_REVIEW transitions
                fsm = RuntimeFSM(strict_mode=True)
                fsm.transition_to(RuntimeState.AMENDMENT_PREP)
                fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
                fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
                fsm.transition_to(RuntimeState.CEO_REVIEW)
                fsm.transition_to(RuntimeState.FREEZE_PREP)
                fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
                fsm.transition_to(RuntimeState.CAPTURE_AMU0)
                
                filepath = fsm.checkpoint_state("test_checkpoint", amu0_path)
                
                # Read RAW bytes - no normalization allowed anymore
                with open(filepath, 'rb') as f:
                    content = f.read()
                    checksums.append(hashlib.sha256(content).hexdigest())
        
        self.assertEqual(checksums[0], checksums[1])
        self.assertEqual(checksums[1], checksums[2])

    def test_checkpoint_no_timestamp_deterministic(self):
        """Verify checkpoints without mock_time are also deterministic (no timestamp field)."""
        checksums = []
        for i in range(3):
            with tempfile.TemporaryDirectory() as tmpdir:
                amu0_path = os.path.join(tmpdir, "amu0")
                # NO pinned_context.json created here - tests no timestamp case
                os.makedirs(amu0_path, exist_ok=True)
                
                # Navigate to a checkpointable state (CAPTURE_AMU0)
                fsm = RuntimeFSM(strict_mode=True)
                fsm.transition_to(RuntimeState.AMENDMENT_PREP)
                fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
                fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
                fsm.transition_to(RuntimeState.CEO_REVIEW)
                fsm.transition_to(RuntimeState.FREEZE_PREP)
                fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
                fsm.transition_to(RuntimeState.CAPTURE_AMU0)
                
                filepath = fsm.checkpoint_state("no_time", amu0_path)
                
                with open(filepath, 'r') as f:
                    data = json.load(f)
                    self.assertNotIn("timestamp", data)
                
                with open(filepath, 'rb') as f:
                    checksums.append(hashlib.sha256(f.read()).hexdigest())
                    
        self.assertEqual(checksums[0], checksums[1])
        self.assertEqual(checksums[1], checksums[2])

    def test_no_time_dependency_in_state(self):
        """Verify FSM state does not depend on wall-clock time."""
        fsm1 = RuntimeFSM(strict_mode=False)
        fsm2 = RuntimeFSM(strict_mode=False)
        
        fsm1.transition_to(RuntimeState.AMENDMENT_PREP)
        fsm2.transition_to(RuntimeState.AMENDMENT_PREP)
        
        self.assertEqual(fsm1.current_state, fsm2.current_state)
        self.assertEqual(fsm1.history, fsm2.history)

    def test_strict_mode_deterministic_from_param(self):
        """Verify strict_mode is deterministic when provided explicitly."""
        fsm_strict = RuntimeFSM(strict_mode=True)
        fsm_not_strict = RuntimeFSM(strict_mode=False)
        
        self.assertTrue(fsm_strict._strict_mode)
        self.assertFalse(fsm_not_strict._strict_mode)

    def test_amu0_timestamp_required(self):
        """Verify AMU0 operations fail without explicit timestamp."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from runtime.state.amu0 import AMU0Manager, AMU0Error
            manager = AMU0Manager(tmpdir)
            
            with open(os.path.join(tmpdir, "test.txt"), "w") as f:
                f.write("test")
                
            with self.assertRaises(AMU0Error):
                manager.create_amu0_baseline("FAIL", [os.path.join(tmpdir, "test.txt")], timestamp="")
    
    def test_determinism_artifact_generation(self):
        """Generate determinism artifact from REAL runtime outputs."""
        runs = []
        
        with tempfile.TemporaryDirectory() as tmpdir:
            from runtime.state.amu0 import AMU0Manager
            
            # Create a file to baseline
            test_file = os.path.join(tmpdir, "artifact_test.txt")
            with open(test_file, "w") as f:
                f.write("content for determinism run")
                
            for i in range(3):
                # We perform a REAL AMU0 operation
                # Use subdirectories to avoid collisions in same temp dir
                run_root = os.path.join(tmpdir, f"run_{i}")
                manager = AMU0Manager(run_root)
                
                baseline_path = manager.create_amu0_baseline(
                    "DET_RUN", 
                    [test_file], 
                    timestamp="2025-01-01T00:00:00Z"
                )
                
                # Checksum the MANIFEST file as the representative artifact
                manifest_path = os.path.join(baseline_path, "amu0_manifest.json")
                with open(manifest_path, "rb") as f:
                    manifest_hash = hashlib.sha256(f.read()).hexdigest()
                    
                runs.append({"run_id": i, "hash": manifest_hash})
        
        # Write the determinism artifact
        artifact_dir = os.path.join(os.path.dirname(__file__), "..", "..", "tests", "_artifacts")
        os.makedirs(artifact_dir, exist_ok=True)
        
        artifact_path = os.path.join(artifact_dir, "determinism_runs.json")
        with open(artifact_path, "w") as f:
            json.dump({"runs": runs}, f, indent=2, sort_keys=True)
            
        self.assertTrue(os.path.exists(artifact_path))
        
        # Verify artifact content
        with open(artifact_path, "r") as f:
            data = json.load(f)
            
        self.assertEqual(len(data["runs"]), 3)
        self.assertEqual(data["runs"][0]["hash"], data["runs"][1]["hash"])
        self.assertEqual(data["runs"][1]["hash"], data["runs"][2]["hash"])


if __name__ == '__main__':
    unittest.main()
