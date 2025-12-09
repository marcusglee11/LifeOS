"""Tests for CND-4: Attestation Recording"""
import unittest

from runtime.validator import (
    AntiFailureValidator, WorkflowStep, StepActor,
    create_attestation_from_result
)


class TestAttestationRecording(unittest.TestCase):
    """Test attestation logging in validator."""
    
    def test_attestation_captures_primitives(self):
        """Attestation correctly captures human primitives."""
        validator = AntiFailureValidator()
        
        steps = [
            WorkflowStep("Intent", StepActor.HUMAN, "", human_primitive="intent"),
            WorkflowStep("Process", StepActor.AGENT, ""),
            WorkflowStep("Approve", StepActor.HUMAN, "", human_primitive="approve"),
        ]
        
        result = validator.validate(steps)
        
        self.assertTrue(result.attestation.intent_used)
        self.assertTrue(result.attestation.approve_used)
        self.assertFalse(result.attestation.veto_used)
        self.assertEqual(result.attestation.total_primitives, 2)
    
    def test_attestation_dict_format(self):
        """Attestation converts to correct dict format."""
        validator = AntiFailureValidator()
        
        steps = [
            WorkflowStep("Veto", StepActor.HUMAN, "", human_primitive="veto"),
        ]
        
        result = validator.validate(steps)
        attestation_dict = create_attestation_from_result(result)
        
        self.assertIn("human_attestation", attestation_dict)
        self.assertTrue(attestation_dict["human_attestation"]["veto_used"])


if __name__ == '__main__':
    unittest.main()
