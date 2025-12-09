"""Tests for CND-4: Validator Smuggled Human Steps"""
import unittest

from runtime.validator import AntiFailureValidator, WorkflowStep, StepActor


class TestValidatorSmuggledHumanSteps(unittest.TestCase):
    """Test detection of smuggled human steps."""
    
    def test_detect_manual_in_agent_step(self):
        """Detect 'manual' keyword in agent step."""
        validator = AntiFailureValidator()
        
        steps = [
            WorkflowStep(
                name="Process Data",
                actor=StepActor.AGENT,
                description="Manually verify the results"
            )
        ]
        
        result = validator.validate(steps)
        self.assertTrue(len(result.warnings) > 0)
        self.assertTrue(any("smuggled" in w.lower() or "manual" in w.lower() 
                          for w in result.warnings))
    
    def test_detect_user_must_in_agent(self):
        """Detect 'user must' pattern in agent step."""
        validator = AntiFailureValidator()
        
        steps = [
            WorkflowStep(
                name="Deploy",
                actor=StepActor.AGENT,
                description="User must confirm deployment"
            )
        ]
        
        result = validator.validate(steps)
        self.assertTrue(len(result.warnings) > 0)
    
    def test_clean_agent_step_no_warnings(self):
        """Clean agent step produces no warnings."""
        validator = AntiFailureValidator()
        
        steps = [
            WorkflowStep(
                name="Process Data",
                actor=StepActor.AGENT,
                description="Automatically process all records"
            )
        ]
        
        result = validator.validate(steps)
        self.assertEqual(len(result.warnings), 0)


if __name__ == '__main__':
    unittest.main()
