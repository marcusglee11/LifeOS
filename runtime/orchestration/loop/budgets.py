from dataclasses import dataclass
import time
from typing import Tuple, Optional
from .taxonomy import TerminalReason

@dataclass
class BudgetConfig:
    max_attempts: int = 5
    max_tokens: int = 100000
    max_wall_clock_minutes: int = 30
    
class BudgetController:
    """
    Enforces interaction limits on the loop.
    Fail-closed: token accounting unavailability leads to critical termination.
    """
    def __init__(self, config: BudgetConfig = None):
        if config is None:
            config = BudgetConfig()
        self.config = config
        self.start_time = time.monotonic()
        
    def check_budget(self, current_attempt: int, total_tokens: int, token_accounting_available: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Check if we are within budget.
        Returns: (is_over_budget, reason)
        If reason is TOKEN_ACCOUNTING_UNAVAILABLE, the caller should treat it as ESCALATION_REQUESTED.
        """
        
        # 1. Attempt Budget
        if current_attempt > self.config.max_attempts:
            return True, TerminalReason.BUDGET_EXHAUSTED.value

        # 2. Wall Clock Budget
        elapsed_min = (time.monotonic() - self.start_time) / 60.0
        if elapsed_min > self.config.max_wall_clock_minutes:
            return True, TerminalReason.BUDGET_EXHAUSTED.value
            
        # 3. Token Budget (Fail-Closed)
        if not token_accounting_available:
            return True, TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value
            
        # We assume total_tokens is accurate if available
        if total_tokens > self.config.max_tokens:
            return True, TerminalReason.BUDGET_EXHAUSTED.value
            
        return False, None

    def check_diff_budget(self, diff_lines: int, max_lines: int = 300) -> Tuple[bool, Optional[str]]:
        if diff_lines > max_lines:
            return True, TerminalReason.DIFF_BUDGET_EXCEEDED.value
        return False, None
