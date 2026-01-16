from typing import List, Optional, Tuple
from .taxonomy import FailureClass, LoopAction, TerminalReason
from .ledger import AttemptLedger

class LoopPolicy:
    """
    Phase A Policy: Hardcoded, Minimally Taxonomy-Aware.
    """
    
    def decide_next_action(self, ledger: AttemptLedger) -> Tuple[str, str]:
        """
        Decide the next action based on the ledger history.
        Returns: (LoopAction.value, rationale/reason)
        """
        history = ledger.history
        if not history:
            # Start of run
            return LoopAction.RETRY.value, "Start"
            
        last_attempt = history[-1]
        
        # 1. Check for Progress / Deadlock / Oscillation
        # Need at least 2 attempts for deadlock (N, N-1)
        # Need at least 3 attempts for oscillation (N, N-2)
        
        if len(history) >= 2:
            prev_attempt = history[-2]
            # Check No Progress: Identical output hash or no delta
            # We use input_hash? No, we check the *result* or *diff*.
            # The prompt says: "hash(N)==hash(N-1) OR diff delta == 0"
            # It likely refers to the state hash or the produced artifact hash.
            # In Phase A, we might use diff_hash as the proxy for "what we did".
            
            # If both attempts failed, and produced exactly the same result/error state?
            # Let's use diff_hash if available, or perhaps the evidence_hashes of the review packet.
            
            # Prompt says "hash(N) == hash(N-1)". This usually refers to the 'state' hash.
            # In our ledger, we have 'diff_hash'.
            if last_attempt.diff_hash and prev_attempt.diff_hash:
                if last_attempt.diff_hash == prev_attempt.diff_hash:
                     return LoopAction.TERMINATE.value, TerminalReason.NO_PROGRESS.value
        
        if len(history) >= 3:
            osc_attempt = history[-3]
            # Check Oscillation: A -> B -> A
            if last_attempt.diff_hash and osc_attempt.diff_hash:
                if last_attempt.diff_hash == osc_attempt.diff_hash:
                    return LoopAction.TERMINATE.value, TerminalReason.OSCILLATION_DETECTED.value

        # 2. Check Outcome of Last Attempt
        if last_attempt.success:
            return LoopAction.TERMINATE.value, TerminalReason.PASS.value
            
        # 3. Handle Failures (Hardcoded Phase A)
        f_class = last_attempt.failure_class
        
        if f_class == FailureClass.REVIEW_REJECTION.value:
            return LoopAction.RETRY.value, "Review rejection triggers retry"
            
        elif f_class == FailureClass.TEST_FAILURE.value:
            return LoopAction.RETRY.value, "Test failure triggers retry"
            
        elif f_class == FailureClass.TIMEOUT.value:
            # Retry once? How to track "retry once"?
            # Check if previous attempt was also TIMEOUT.
            if len(history) >= 2 and history[-2].failure_class == FailureClass.TIMEOUT.value:
                 return LoopAction.TERMINATE.value, "Timeout retry limit exceeded"
            return LoopAction.RETRY.value, "Timeout triggers single retry"
            
        elif f_class == FailureClass.SYNTAX_ERROR.value:
            return LoopAction.TERMINATE.value, "Syntax error is fail-closed"
            
        elif f_class == FailureClass.VALIDATION_ERROR.value:
             return LoopAction.TERMINATE.value, "Validation error is fail-closed"
             
        elif f_class == FailureClass.UNKNOWN.value:
            return LoopAction.TERMINATE.value, "Unknown error is fail-closed"
            
        # Default fallback
        return LoopAction.TERMINATE.value, "Default fall-through blocked"
