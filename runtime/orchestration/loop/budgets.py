from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

from .taxonomy import TerminalReason

logger = logging.getLogger(__name__)


def extract_usage_tokens(evidence: dict) -> Optional[int]:
    """Return normalized token count from mission evidence, or None if unavailable."""
    usage = evidence.get("usage")
    if not isinstance(usage, dict) or not usage:
        return None
    total = usage.get("total_tokens")
    if isinstance(total, int) and total >= 0:
        return total
    inp = usage.get("input_tokens")
    out = usage.get("output_tokens")
    if isinstance(inp, int) and inp >= 0 and isinstance(out, int) and out >= 0:
        return inp + out
    legacy = usage.get("total")
    if isinstance(legacy, int) and legacy >= 0:
        return legacy
    return None


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

    Fail-closed behaviour is caller-opt-in via the ``token_accounting_available``
    parameter to ``check_budget``.  Callers that pass ``False`` trigger immediate
    ``BUDGET_EXHAUSTED`` termination.  The typed workflow (``_run_typed_workflow``)
    intentionally passes ``True`` and instead surfaces partial accounting via
    ``token_accounting_complete`` on the terminal packet, allowing mixed-agent
    runs where some steps emit estimates and others have no usage data.
    """

    def __init__(
        self,
        config: BudgetConfig = None,
        *,
        run_started_at: Optional[str] = None,
    ):
        if config is None:
            config = BudgetConfig()
        self.config = config
        self.start_time = time.monotonic()
        self.run_started_at = run_started_at
        self._warned = False

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
        elapsed_min = self._elapsed_minutes()
        if elapsed_min > self.config.max_wall_clock_minutes:
            return True, TerminalReason.BUDGET_EXHAUSTED.value

        # 3. Token Budget (Fail-Closed)
        if not token_accounting_available:
            return True, TerminalReason.TOKEN_ACCOUNTING_UNAVAILABLE.value

        # We assume total_tokens is accurate if available
        if total_tokens > self.config.max_tokens:
            return True, TerminalReason.BUDGET_EXHAUSTED.value

        return False, None

    def check_budget_warn(self, total_tokens: int, warn_threshold: float = 0.8) -> bool:
        """Log warning if total_tokens exceeds the warning threshold. Returns True once."""
        if self._warned:
            return False

        threshold = int(self.config.max_tokens * warn_threshold)
        if total_tokens >= threshold:
            logger.warning(
                "TOKEN_BUDGET_WARNING: %d/%d tokens consumed (%.0f%% of budget)",
                total_tokens,
                self.config.max_tokens,
                100.0 * total_tokens / self.config.max_tokens,
            )
            self._warned = True
            return True
        return False

    def check_diff_budget(
        self, diff_lines: int, max_lines: int = 300
    ) -> Tuple[bool, Optional[str]]:
        if diff_lines > max_lines:
            return True, TerminalReason.DIFF_BUDGET_EXCEEDED.value
        return False, None

    def _elapsed_minutes(self) -> float:
        if self.run_started_at:
            try:
                started = datetime.fromisoformat(self.run_started_at.replace("Z", "+00:00"))
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                return max(0.0, (datetime.now(timezone.utc) - started).total_seconds() / 60.0)
            except ValueError:
                pass
        return (time.monotonic() - self.start_time) / 60.0
