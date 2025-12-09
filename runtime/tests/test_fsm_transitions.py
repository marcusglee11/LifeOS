"""
FP-3.1: FSM Transition Tests
Comprehensive legal/illegal transition coverage.
"""
import unittest
from runtime.engine import RuntimeFSM, RuntimeState, GovernanceError


class TestFSMTransitions(unittest.TestCase):
    """
    3.1-FP-2: Tests for legal and illegal FSM transitions.
    """

    def setUp(self):
        # strict_mode=True required for CEO_REVIEW/CEO_FINAL_REVIEW transitions
        self.fsm = RuntimeFSM(strict_mode=True)

    # ========== Legal Transitions ==========

    def test_legal_init_to_amendment_prep(self):
        """INIT -> AMENDMENT_PREP is legal."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.assertEqual(self.fsm.current_state, RuntimeState.AMENDMENT_PREP)

    def test_legal_amendment_prep_to_exec(self):
        """AMENDMENT_PREP -> AMENDMENT_EXEC is legal."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        self.assertEqual(self.fsm.current_state, RuntimeState.AMENDMENT_EXEC)

    def test_legal_amendment_exec_to_verify(self):
        """AMENDMENT_EXEC -> AMENDMENT_VERIFY is legal."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        self.fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        self.assertEqual(self.fsm.current_state, RuntimeState.AMENDMENT_VERIFY)

    def test_legal_amendment_verify_to_ceo_review(self):
        """AMENDMENT_VERIFY -> CEO_REVIEW is legal."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        self.fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        self.fsm.transition_to(RuntimeState.CEO_REVIEW)
        self.assertEqual(self.fsm.current_state, RuntimeState.CEO_REVIEW)

    def test_legal_ceo_review_to_freeze_prep(self):
        """CEO_REVIEW -> FREEZE_PREP is legal."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        self.fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        self.fsm.transition_to(RuntimeState.CEO_REVIEW)
        self.fsm.transition_to(RuntimeState.FREEZE_PREP)
        self.assertEqual(self.fsm.current_state, RuntimeState.FREEZE_PREP)

    def test_legal_freeze_prep_to_activated(self):
        """FREEZE_PREP -> FREEZE_ACTIVATED is legal."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        self.fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        self.fsm.transition_to(RuntimeState.CEO_REVIEW)
        self.fsm.transition_to(RuntimeState.FREEZE_PREP)
        self.fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
        self.assertEqual(self.fsm.current_state, RuntimeState.FREEZE_ACTIVATED)

    def test_legal_freeze_activated_to_capture(self):
        """FREEZE_ACTIVATED -> CAPTURE_AMU0 is legal."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        self.fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        self.fsm.transition_to(RuntimeState.CEO_REVIEW)
        self.fsm.transition_to(RuntimeState.FREEZE_PREP)
        self.fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
        self.fsm.transition_to(RuntimeState.CAPTURE_AMU0)
        self.assertEqual(self.fsm.current_state, RuntimeState.CAPTURE_AMU0)

    def test_legal_capture_to_migration(self):
        """CAPTURE_AMU0 -> MIGRATION_SEQUENCE is legal."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        self.fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        self.fsm.transition_to(RuntimeState.CEO_REVIEW)
        self.fsm.transition_to(RuntimeState.FREEZE_PREP)
        self.fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
        self.fsm.transition_to(RuntimeState.CAPTURE_AMU0)
        self.fsm.transition_to(RuntimeState.MIGRATION_SEQUENCE)
        self.assertEqual(self.fsm.current_state, RuntimeState.MIGRATION_SEQUENCE)

    def test_legal_migration_to_gates(self):
        """MIGRATION_SEQUENCE -> GATES is legal."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        self.fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        self.fsm.transition_to(RuntimeState.CEO_REVIEW)
        self.fsm.transition_to(RuntimeState.FREEZE_PREP)
        self.fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
        self.fsm.transition_to(RuntimeState.CAPTURE_AMU0)
        self.fsm.transition_to(RuntimeState.MIGRATION_SEQUENCE)
        self.fsm.transition_to(RuntimeState.GATES)
        self.assertEqual(self.fsm.current_state, RuntimeState.GATES)

    def test_legal_gates_to_ceo_final(self):
        """GATES -> CEO_FINAL_REVIEW is legal."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        self.fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        self.fsm.transition_to(RuntimeState.CEO_REVIEW)
        self.fsm.transition_to(RuntimeState.FREEZE_PREP)
        self.fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
        self.fsm.transition_to(RuntimeState.CAPTURE_AMU0)
        self.fsm.transition_to(RuntimeState.MIGRATION_SEQUENCE)
        self.fsm.transition_to(RuntimeState.GATES)
        self.fsm.transition_to(RuntimeState.CEO_FINAL_REVIEW)
        self.assertEqual(self.fsm.current_state, RuntimeState.CEO_FINAL_REVIEW)

    def test_legal_ceo_final_to_complete(self):
        """CEO_FINAL_REVIEW -> COMPLETE is legal."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        self.fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        self.fsm.transition_to(RuntimeState.CEO_REVIEW)
        self.fsm.transition_to(RuntimeState.FREEZE_PREP)
        self.fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
        self.fsm.transition_to(RuntimeState.CAPTURE_AMU0)
        self.fsm.transition_to(RuntimeState.MIGRATION_SEQUENCE)
        self.fsm.transition_to(RuntimeState.GATES)
        self.fsm.transition_to(RuntimeState.CEO_FINAL_REVIEW)
        self.fsm.transition_to(RuntimeState.COMPLETE)
        self.assertEqual(self.fsm.current_state, RuntimeState.COMPLETE)

    # ========== Illegal Transitions ==========

    def test_illegal_init_to_complete(self):
        """INIT -> COMPLETE is illegal."""
        with self.assertRaises(GovernanceError):
            self.fsm.transition_to(RuntimeState.COMPLETE)
        self.assertEqual(self.fsm.current_state, RuntimeState.ERROR)

    def test_illegal_init_to_gates(self):
        """INIT -> GATES is illegal."""
        with self.assertRaises(GovernanceError):
            self.fsm.transition_to(RuntimeState.GATES)
        self.assertEqual(self.fsm.current_state, RuntimeState.ERROR)

    def test_illegal_init_to_freeze_activated(self):
        """INIT -> FREEZE_ACTIVATED is illegal."""
        with self.assertRaises(GovernanceError):
            self.fsm.transition_to(RuntimeState.FREEZE_ACTIVATED)
        self.assertEqual(self.fsm.current_state, RuntimeState.ERROR)

    def test_illegal_amendment_prep_to_complete(self):
        """AMENDMENT_PREP -> COMPLETE is illegal."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        with self.assertRaises(GovernanceError):
            self.fsm.transition_to(RuntimeState.COMPLETE)
        self.assertEqual(self.fsm.current_state, RuntimeState.ERROR)

    def test_illegal_amendment_exec_to_init(self):
        """AMENDMENT_EXEC -> INIT is illegal (no backward transitions)."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        with self.assertRaises(GovernanceError):
            self.fsm.transition_to(RuntimeState.INIT)
        self.assertEqual(self.fsm.current_state, RuntimeState.ERROR)

    def test_illegal_skip_amendment_exec(self):
        """AMENDMENT_PREP -> AMENDMENT_VERIFY is illegal (skips EXEC)."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        with self.assertRaises(GovernanceError):
            self.fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        self.assertEqual(self.fsm.current_state, RuntimeState.ERROR)

    def test_illegal_skip_ceo_review(self):
        """AMENDMENT_VERIFY -> FREEZE_PREP is illegal (skips CEO_REVIEW)."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        self.fsm.transition_to(RuntimeState.AMENDMENT_VERIFY)
        with self.assertRaises(GovernanceError):
            self.fsm.transition_to(RuntimeState.FREEZE_PREP)
        self.assertEqual(self.fsm.current_state, RuntimeState.ERROR)

    # ========== Error State Behavior ==========

    def test_error_state_is_terminal(self):
        """Once in ERROR, no further transitions are possible."""
        self.fsm.transition_to(RuntimeState.AMENDMENT_PREP)
        with self.assertRaises(GovernanceError):
            self.fsm.transition_to(RuntimeState.COMPLETE)  # Force error
        
        # Now try to transition again
        with self.assertRaises(GovernanceError):
            self.fsm.transition_to(RuntimeState.AMENDMENT_EXEC)
        self.assertEqual(self.fsm.current_state, RuntimeState.ERROR)

    def test_error_message_format(self):
        """Verify error messages have consistent format."""
        try:
            self.fsm.transition_to(RuntimeState.COMPLETE)
        except GovernanceError as e:
            self.assertIn("INIT", str(e))
            self.assertIn("COMPLETE", str(e))


if __name__ == '__main__':
    unittest.main()
