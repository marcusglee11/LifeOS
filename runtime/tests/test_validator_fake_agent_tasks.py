"""Tests for CND-4: Validator Fake Agent Tasks"""
import unittest

from runtime.validator import AntiFailureValidator, WorkflowStep, StepActor


class TestValidatorFakeAgentTasks(unittest.TestCase):
    """Test detection of fake agent tasks requiring human effort."""
    
    def test_detect_human_review_in_agent(self):
        """Detect 'human review' in agent task."""
        validator = AntiFailureValidator()
        
        steps = [
            WorkflowStep(
                name="Review Report",
                actor=StepActor.AGENT,
                description="Perform human review of output"
            )
        ]
        
        result = validator.validate(steps)
        self.assertTrue(len(result.warnings) > 0)
    
    def test_detect_requires_user_in_agent(self):
        """Detect 'requires user' in agent task."""
        validator = AntiFailureValidator()
        
        steps = [
            WorkflowStep(
                name="Complete Task",
                actor=StepActor.AGENT,
                description="This requires user input to complete"
            )
        ]
        
        result = validator.validate(steps)
        self.assertTrue(len(result.warnings) > 0)


if __name__ == '__main__':
    unittest.main()
