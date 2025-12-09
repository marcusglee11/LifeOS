"""
FP-3.7: Workflow Validator Tests
Tests for Anti-Failure constraint enforcement.
"""
import unittest
from runtime.workflows.validator import (
    WorkflowValidator,
    WorkflowStep,
    StepActor,
    WorkflowValidationError,
    ValidationResult
)


class TestWorkflowValidator(unittest.TestCase):
    """
    3.7-FP: Tests for Workflow Validator.
    """
    
    def setUp(self):
        self.validator = WorkflowValidator()
    
    # ========== Valid Workflows ==========
    
    def test_valid_workflow_5_agent_steps(self):
        """5 agent steps is valid."""
        steps = [
            WorkflowStep("Step1", StepActor.AGENT, "Agent step 1"),
            WorkflowStep("Step2", StepActor.AGENT, "Agent step 2"),
            WorkflowStep("Step3", StepActor.AGENT, "Agent step 3"),
            WorkflowStep("Step4", StepActor.AGENT, "Agent step 4"),
            WorkflowStep("Step5", StepActor.AGENT, "Agent step 5"),
        ]
        
        result = self.validator.validate(steps)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.total_steps, 5)
        self.assertEqual(result.human_steps, 0)
    
    def test_valid_workflow_2_human_steps(self):
        """2 human steps is valid."""
        steps = [
            WorkflowStep("Intent", StepActor.HUMAN, "Express intent"),
            WorkflowStep("Execute", StepActor.AGENT, "Execute work"),
            WorkflowStep("Approve", StepActor.HUMAN, "Approve result"),
        ]
        
        result = self.validator.validate(steps)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.human_steps, 2)
    
    def test_valid_empty_workflow(self):
        """Empty workflow is valid."""
        result = self.validator.validate([])
        self.assertTrue(result.is_valid)
    
    # ========== Invalid Workflows - Too Many Steps ==========
    
    def test_invalid_too_many_steps(self):
        """More than 5 steps is invalid."""
        steps = [
            WorkflowStep(f"Step{i}", StepActor.AGENT, f"Step {i}")
            for i in range(6)
        ]
        
        result = self.validator.validate(steps)
        
        self.assertFalse(result.is_valid)
        self.assertIn("6 steps", result.violations[0])
    
    # ========== Invalid Workflows - Too Many Human Steps ==========
    
    def test_invalid_too_many_human_steps(self):
        """More than 2 human steps is invalid."""
        steps = [
            WorkflowStep("H1", StepActor.HUMAN, "Human 1"),
            WorkflowStep("H2", StepActor.HUMAN, "Human 2"),
            WorkflowStep("H3", StepActor.HUMAN, "Human 3"),
        ]
        
        result = self.validator.validate(steps)
        
        self.assertFalse(result.is_valid)
        self.assertIn("3 human steps", result.violations[0])
    
    # ========== Invalid Workflows - Routine Human Ops ==========
    
    def test_invalid_routine_human_operations(self):
        """Routine human operations are invalid."""
        steps = [
            WorkflowStep("Copy Files", StepActor.HUMAN, "Copy files manually", is_routine=True),
        ]
        
        result = self.validator.validate(steps)
        
        self.assertFalse(result.is_valid)
        self.assertIn("routine human operations", result.violations[0])
    
    def test_routine_allowed_when_configured(self):
        """Routine human ops allowed when configured."""
        validator = WorkflowValidator(allow_routine_human_ops=True)
        steps = [
            WorkflowStep("Copy", StepActor.HUMAN, "Copy files", is_routine=True),
        ]
        
        result = validator.validate(steps)
        
        self.assertTrue(result.is_valid)
    
    # ========== Suggestions ==========
    
    def test_suggestions_for_too_many_steps(self):
        """Suggestions provided for too many steps."""
        steps = [WorkflowStep(f"S{i}", StepActor.AGENT, f"S{i}") for i in range(7)]
        
        result = self.validator.validate(steps)
        
        self.assertTrue(len(result.suggestions) > 0)
        self.assertIn("combining steps", result.suggestions[0].lower())
    
    def test_suggestions_for_routine_automation(self):
        """Suggestions for automating routine tasks."""
        steps = [
            WorkflowStep("Manual Test", StepActor.HUMAN, "Run tests manually", is_routine=True),
        ]
        
        result = self.validator.validate(steps)
        
        self.assertTrue(any("Automate" in s for s in result.suggestions))
    
    # ========== validate_or_raise ==========
    
    def test_validate_or_raise_passes(self):
        """validate_or_raise passes for valid workflow."""
        steps = [WorkflowStep("S1", StepActor.AGENT, "Step 1")]
        
        result = self.validator.validate_or_raise(steps)
        
        self.assertTrue(result.is_valid)
    
    def test_validate_or_raise_raises(self):
        """validate_or_raise raises for invalid workflow."""
        steps = [WorkflowStep(f"S{i}", StepActor.AGENT, f"S{i}") for i in range(10)]
        
        with self.assertRaises(WorkflowValidationError) as ctx:
            self.validator.validate_or_raise(steps)
        
        self.assertIn("validation failed", str(ctx.exception))
    
    # ========== Mission Validation ==========
    
    def test_validate_mission(self):
        """validate_mission parses mission format."""
        mission = {
            "execution_flow": [
                {"step": "G1_init", "description": "Initialize"},
                {"step": "FP_3_1", "description": "Fix Pack 1"},
                {"step": "human_approve", "description": "CEO approval"},
            ]
        }
        
        result = self.validator.validate_mission(mission)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(result.total_steps, 3)
        self.assertEqual(result.human_steps, 1)
    
    # ========== Factory Methods ==========
    
    def test_create_human_step(self):
        """create_human_step creates correct step."""
        step = WorkflowValidator.create_human_step("Approve", "Approve changes")
        
        self.assertEqual(step.actor, StepActor.HUMAN)
        self.assertEqual(step.name, "Approve")
    
    def test_create_agent_step(self):
        """create_agent_step creates correct step."""
        step = WorkflowValidator.create_agent_step("Build", "Build code")
        
        self.assertEqual(step.actor, StepActor.AGENT)
    
    def test_create_system_step(self):
        """create_system_step creates correct step."""
        step = WorkflowValidator.create_system_step("Test", "Run tests")
        
        self.assertEqual(step.actor, StepActor.SYSTEM)
    
    # ========== Custom Limits ==========
    
    def test_custom_max_steps(self):
        """Custom max_steps is respected."""
        validator = WorkflowValidator(max_steps=3)
        steps = [WorkflowStep(f"S{i}", StepActor.AGENT, f"S{i}") for i in range(4)]
        
        result = validator.validate(steps)
        
        self.assertFalse(result.is_valid)
    
    def test_custom_max_human_steps(self):
        """Custom max_human_steps is respected."""
        validator = WorkflowValidator(max_human_steps=1)
        steps = [
            WorkflowStep("H1", StepActor.HUMAN, "H1"),
            WorkflowStep("H2", StepActor.HUMAN, "H2"),
        ]
        
        result = validator.validate(steps)
        
        self.assertFalse(result.is_valid)


if __name__ == '__main__':
    unittest.main()
