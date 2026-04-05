from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Tuple

from .taxonomy import TerminalReason


@dataclass
class BudgetConfig:
    max_attempts: int = 5
    max_tokens: int = 100000
    max_wall_clock_minutes: int = 30

    def __post_init__(self) -> None:
        """
        Validate budget configuration parameters.

        Raises:
            ValueError: If any parameter is non-positive
        """
        if self.max_attempts <= 0:
            raise ValueError(f"max_attempts must be positive, got {self.max_attempts}")
        if self.max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {self.max_tokens}")
        if self.max_wall_clock_minutes <= 0:
            raise ValueError(
                f"max_wall_clock_minutes must be positive, got {self.max_wall_clock_minutes}"
            )


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

    def check_budget(
        self, current_attempt: int, total_tokens: int, token_accounting_available: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if we are within budget.
        Returns: (is_over_budget, reason)
        If reason is TOKEN_ACCOUNTING_UNAVAILABLE, the caller should treat it as
        ESCALATION_REQUESTED.
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

    def check_diff_budget(
        self, diff_lines: int, max_lines: int = 300
    ) -> Tuple[bool, Optional[str]]:
        if diff_lines > max_lines:
            return True, TerminalReason.DIFF_BUDGET_EXCEEDED.value
        return False, None
