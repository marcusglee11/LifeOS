"""
ConfigurableLoopPolicy - Config-driven loop policy Phase B.1

Implements:
- Retry budgets from config
- Waiver eligibility checking
- Escalation trigger detection
- Deadlock/oscillation detection (Phase A logic preserved)
- Terminal outcome routing
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
from runtime.orchestration.loop.ledger import AttemptLedger
from runtime.orchestration.loop.taxonomy import FailureClass, TerminalReason
from runtime.orchestration.loop import waiver_artifact


class ConfigurableLoopPolicy:
    """
    Config-driven loop policy.
    
    Decides next action based on:
    - Config retry budgets
    - Waiver eligibility
    - Escalation triggers
    - Deadlock/oscillation detection
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize with policy config.
        
        Args:
            config: Policy configuration dict
        """
        self.config = config
        self.budgets = config.get("budgets", {})
        self.failure_routing = config.get("failure_routing", {})
        self.waiver_rules = config.get("waiver_rules", {})
        self.progress_detection = config.get("progress_detection", {})
        self.retry_limits = self.budgets.get("retry_limits", {})
    
    def decide_next_action(
        self,
        ledger: AttemptLedger,
        now: Optional[datetime] = None
    ) -> Tuple[str, str, Optional[str]]:
        """
        Decide next action based on ledger history and config.
        
        Args:
            ledger: Attempt ledger with history
            now: Optional fixed datetime for deterministic waiver validation
        
        Returns:
            (action, reason, override) where:
            - action: "retry" or "terminate"
            - reason: Human-readable reason
            - override: Terminal outcome override (e.g., "WAIVER_REQUESTED", "ESCALATION_REQUESTED")
        """
        history = ledger.history
        
        # Start of run
        if not history:
            return "retry", "Start", None
        
        last_attempt = history[-1]
        
        # Check for success
        if last_attempt.success:
            return "terminate", TerminalReason.PASS.value, None
        
        # Check for deadlock (no progress)
        if self._check_deadlock(history):
            return "terminate", TerminalReason.NO_PROGRESS.value, None
        
        # Check for oscillation
        if self._check_oscillation(history):
            return "terminate", TerminalReason.OSCILLATION_DETECTED.value, None
        
        # Get failure class - normalize to uppercase for config lookup
        failure_class_str_raw = last_attempt.failure_class or "UNKNOWN"
        failure_class_str = failure_class_str_raw.upper()  # Normalize for config lookup
        
        # Normalize to FailureClass enum if possible
        try:
            failure_class = FailureClass[failure_class_str]
        except KeyError:
            failure_class = FailureClass.UNKNOWN
        
        # Get routing config for this failure class
        routing = self.failure_routing.get(failure_class_str, {})
        default_action = routing.get("default_action", "TERMINATE")
        retry_limit = self.retry_limits.get(failure_class_str, 0)
        
        # Check if immediate terminate (retry_limit == 0 and action is TERMINATE)
        if default_action == "TERMINATE" and retry_limit == 0:
            terminal_outcome = routing.get("terminal_outcome", "BLOCKED")
            terminal_reason = routing.get("terminal_reason", "CRITICAL_FAILURE")
            return "terminate", f"Immediate terminate: {terminal_reason}", terminal_outcome
        
        # Check retry limit
        retry_count = self._count_retries_for_class(ledger, failure_class)
        
        # Retry limit exhausted when count >= limit (3 failures with limit 3 = exhausted)
        if retry_count >= retry_limit:
            # Retry limit exhausted
            # Check for escalation triggers first (overrides waiver)
            if self._check_escalation_triggers(ledger):
                return "terminate", "Escalation triggered: protected path touched", "ESCALATION_REQUESTED"
            
            # Check waiver eligibility
            if self._check_waiver_eligibility(failure_class_str):
                # Build waiver context for artifact binding
                waiver_context = {
                    "failure_class": failure_class_str,
                    "retry_count": retry_count,
                    "retry_limit": retry_limit
                }
                
                # Check if valid waiver artifact exists
                if waiver_artifact.check_waiver_for_context(waiver_context, now=now):
                    # Valid waiver found - resume with retry
                    return "retry", f"Waiver applied for {failure_class_str} - resuming", "WAIVER_APPLIED"
                
                # No valid waiver - request one
                return "terminate", f"Retry limit exhausted ({retry_count}/{retry_limit}): waiver requested", "WAIVER_REQUESTED"
            
            # Not waiver eligible - use configured terminal outcome
            terminal_outcome = routing.get("terminal_outcome", "BLOCKED")
            terminal_reason = routing.get("terminal_reason", "MAX_RETRIES_EXCEEDED")
            return "terminate", f"{terminal_reason} ({retry_count}/{retry_limit})", terminal_outcome
        
        # Within retry budget
        return "retry", f"Retry {retry_count}/{retry_limit} for {failure_class_str}", None
    
    def _count_retries_for_class(self, ledger: AttemptLedger, failure_class: FailureClass) -> int:
        """
        Count consecutive retries for a specific failure class.
        
        Count resets on:
        - Different failure class
        - Success
        
        Args:
            ledger: Attempt ledger
            failure_class: Failure class to count
            
        Returns:
            Number of consecutive failures (attempts) for this class
        """
        count = 0
        # Get the uppercase version for comparison
        target_class_upper = failure_class.value.upper() if isinstance(failure_class, FailureClass) else str(failure_class).upper()
        
        for attempt in reversed(ledger.history):
            if attempt.success:
                break
            attempt_class = (attempt.failure_class or "").upper()
            if attempt_class != target_class_upper:
                break
            count += 1
        
        return count
    
    def _check_waiver_eligibility(self, failure_class) -> bool:
        """
        Check if failure class is waiver-eligible.
        
        Args:
            failure_class: Failure class (string or FailureClass enum)
            
        Returns:
            True if waiver-eligible
        """
        eligible = self.waiver_rules.get("eligible_failure_classes", [])
        ineligible = self.waiver_rules.get("ineligible_failure_classes", [])
        
        # Handle both enum and string - normalize to uppercase
        if isinstance(failure_class, FailureClass):
            failure_class_upper = failure_class.value.upper()
        else:
            failure_class_upper = str(failure_class).upper()
        
        # Explicit ineligible takes precedence
        if failure_class_upper in ineligible:
            return False
        
        # Explicit eligible
        if failure_class_upper in eligible:
            return True
        
        # Default: not eligible
        return False
    
    def _check_escalation_triggers(self, ledger: AttemptLedger) -> bool:
        """
        Check if escalation is required based on triggers.
        
        Triggers include:
        - Protected path modified (governance, foundations, etc.)
        
        Args:
            ledger: Attempt ledger
            
        Returns:
            True if escalation required
        """
        escalation_config = self.waiver_rules.get("escalation_triggers", [])
        
        for attempt in ledger.history:
            changed_files = getattr(attempt, 'changed_files', None) or []
            
            for file_path in changed_files:
                # Check for protected paths
                protected_prefixes = [
                    "docs/00_foundations/",
                    "docs/01_governance/",
                    "docs/02_protocols/",
                ]
                
                if any(file_path.startswith(prefix) for prefix in protected_prefixes):
                    return True
        
        return False
    
    def _check_deadlock(self, history: List) -> bool:
        """
        Check for deadlock (no progress).
        
        Deadlock = consecutive attempts with identical diff hash
        
        Args:
            history: List of attempts
            
        Returns:
            True if deadlock detected
        """
        if len(history) < 2:
            return False
        
        enabled = self.progress_detection.get("no_progress_enabled", True)
        if not enabled:
            return False
        
        lookback = self.progress_detection.get("no_progress_lookback", 1)
        
        if len(history) >= lookback + 1:
            last = history[-1]
            prev = history[-(lookback + 1)]
            
            if last.diff_hash and prev.diff_hash:
                if last.diff_hash == prev.diff_hash:
                    return True
        
        return False
    
    def _check_oscillation(self, history: List) -> bool:
        """
        Check for oscillation pattern (A -> B -> A).
        
        Args:
            history: List of attempts
            
        Returns:
            True if oscillation detected
        """
        if len(history) < 3:
            return False
        
        enabled = self.progress_detection.get("oscillation_enabled", True)
        if not enabled:
            return False
        
        window = self.progress_detection.get("oscillation_window_size", 3)
        
        if len(history) >= window:
            last = history[-1]
            third_last = history[-window]
            
            if last.diff_hash and third_last.diff_hash:
                if last.diff_hash == third_last.diff_hash:
                    return True
        
        return False
