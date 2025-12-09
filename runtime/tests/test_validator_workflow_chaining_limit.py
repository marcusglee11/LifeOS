"""Tests for CND-4: Validator Workflow Chaining Limit"""
import unittest

from runtime.validator import AntiFailureValidator, WorkflowStep, StepActor


class TestValidatorWorkflowChainingLimit(unittest.TestCase):
    """Test workflow chaining limit enforcement."""
    
    def test_single_workflow_within_limits(self):
        """Single workflow within limits passes."""
        validator = AntiFailureValidator()
        
        workflows = [[
            WorkflowStep("Step1", StepActor.AGENT, "Do thing 1"),
            WorkflowStep("Step2", StepActor.AGENT, "Do thing 2"),
        ]]
        
        is_valid, violations = validator.check_workflow_chaining(workflows)
        self.assertTrue(is_valid)
    
    def test_chained_workflows_exceed_steps(self):
        """Chained workflows exceeding step limit fail."""
        validator = AntiFailureValidator(max_steps=5)
        
        workflows = [
            [WorkflowStep(f"WF1_{i}", StepActor.AGENT, "") for i in range(3)],
            [WorkflowStep(f"WF2_{i}", StepActor.AGENT, "") for i in range(3)],
        ]
        
        is_valid, violations = validator.check_workflow_chaining(workflows)
        self.assertFalse(is_valid)
        self.assertTrue(any("effective steps" in v.lower() for v in violations))
    
    def test_chained_human_steps_exceed(self):
        """Chained workflows with too many human steps fail."""
        validator = AntiFailureValidator(max_human_steps=2)
        
        workflows = [
            [WorkflowStep("H1", StepActor.HUMAN, "", human_primitive="intent")],
            [WorkflowStep("H2", StepActor.HUMAN, "", human_primitive="approve")],
            [WorkflowStep("H3", StepActor.HUMAN, "", human_primitive="veto")],
        ]
        
        is_valid, violations = validator.check_workflow_chaining(workflows)
        self.assertFalse(is_valid)


if __name__ == '__main__':
    unittest.main()
