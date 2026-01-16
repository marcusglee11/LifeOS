"""
Phase B: Configurable Loop Policy

Config-driven policy engine that replaces Phase A hardcoded policy.
Supports retry budgets, waiver eligibility, escalation triggers.
"""
from typing import Optional, Tuple
from .config_loader import PolicyConfig
from .ledger import AttemptLedger
from .taxonomy import FailureClass, TerminalOutcome, TerminalReason, LoopAction


class ConfigurableLoopPolicy:
    """
    Phase B Policy: Config-Driven, Waiver-Aware.

    Loads policy from PolicyConfig (YAML-based) and makes decisions based on:
    - Configurable retry limits per failure class
    - Waiver eligibility rules
    - Escalation triggers (governance surfaces, protected paths)
    - Progress/deadlock/oscillation detection (Phase A logic preserved)
    """

    def __init__(self, config: PolicyConfig):
        """
        Initialize policy with loaded config.

        Args:
            config: PolicyConfig object from PolicyConfigLoader.load()
        """
        self.config = config

    def decide_next_action(self, ledger: AttemptLedger) -> Tuple[str, str, Optional[str]]:
        """
        Decide the next action based on ledger history and config policy.

        Returns:
            (action, reason, terminal_outcome_override)

            action: "RETRY" | "TERMINATE"
            reason: Rationale string explaining the decision
            terminal_outcome_override: Override for terminal outcome
                - "WAIVER_REQUESTED" if retry limit exhausted for waiver-eligible failure
                - "ESCALATION_REQUESTED" if escalation trigger detected
                - None otherwise (use default routing from config)

        Logic Flow:
        0. IMMEDIATE governance check (Phase B P0.3 fix)
           - Check escalation triggers (protected paths, governance surfaces)
           - Escalate immediately if detected (pre-empts retry/budget logic)
        1. Check deadlock/oscillation (Phase A logic preserved)
        2. If last attempt succeeded → TERMINATE with PASS
        3. If last attempt failed:
           - Count retries for failure class
           - Check retry limit from config
           - If exhausted:
             - Check escalation triggers again (for non-governance failure classes)
             - Check waiver eligibility
             - Route to WAIVER_REQUESTED or ESCALATION_REQUESTED or BLOCKED
           - Else retry per config routing
        """
        history = ledger.history

        # Start of run
        if not history:
            return LoopAction.RETRY.value, "Start of autonomous build loop", None

        last_attempt = history[-1]

        # IMMEDIATE GOVERNANCE CHECK (P0.3 Phase B activation fix)
        # Governance violations trigger immediate escalation, pre-empting retry/budget logic.
        # This ensures protected path modifications cannot be masked by budget exhaustion.
        if self._check_escalation_triggers(ledger):
            return (
                LoopAction.TERMINATE.value,  # Use enum value for consistency ("terminate" lowercase)
                "Governance surface touched - immediate escalation required",
                "ESCALATION_REQUESTED"
            )

        # 1. Check for Progress / Deadlock / Oscillation (Phase A logic)
        if len(history) >= 2:
            prev_attempt = history[-2]
            # Check No Progress: Identical diff hash
            if last_attempt.diff_hash and prev_attempt.diff_hash:
                if last_attempt.diff_hash == prev_attempt.diff_hash:
                    return (
                        LoopAction.TERMINATE.value,
                        TerminalReason.NO_PROGRESS.value,
                        None  # Default to BLOCKED per config
                    )

        if len(history) >= 3:
            osc_attempt = history[-3]
            # Check Oscillation: A -> B -> A pattern
            if last_attempt.diff_hash and osc_attempt.diff_hash:
                if last_attempt.diff_hash == osc_attempt.diff_hash:
                    return (
                        LoopAction.TERMINATE.value,
                        TerminalReason.OSCILLATION_DETECTED.value,
                        None  # Default to BLOCKED per config
                    )

        # 2. Check Outcome of Last Attempt
        if last_attempt.success:
            return LoopAction.TERMINATE.value, TerminalReason.PASS.value, None

        # 3. Handle Failures (Config-Driven Phase B)
        failure_class_str = last_attempt.failure_class

        # Convert string to FailureClass enum
        try:
            failure_class = FailureClass(failure_class_str)
        except ValueError:
            # Unknown failure class - treat as UNKNOWN
            failure_class = FailureClass.UNKNOWN

        # Get routing config for this failure class
        routing_key = failure_class.name  # Enum MEMBER NAME (e.g., TEST_FAILURE)
        routing = self.config.failure_routing.get(routing_key)

        if not routing:
            # Should never happen if config is valid (totality check)
            return LoopAction.TERMINATE.value, "Missing routing for failure class", None

        # Count retries for this specific failure class
        retry_count = self._count_retries_for_class(ledger, failure_class)
        retry_limit = self.config.budgets["retry_limits"].get(routing_key, 0)

        # Check if retry limit exhausted
        if retry_count >= retry_limit:
            # Retry limit exhausted - check for escalation or waiver

            # Check escalation triggers (P0.4 governance posture)
            if self._check_escalation_triggers(ledger):
                return (
                    LoopAction.TERMINATE.value,
                    f"Escalation required: {failure_class.value} with governance surface touched",
                    "ESCALATION_REQUESTED"
                )

            # Check waiver eligibility
            if self._check_waiver_eligibility(failure_class):
                return (
                    LoopAction.TERMINATE.value,
                    f"Retry limit exceeded for {failure_class.value}, waiver eligible",
                    "WAIVER_REQUESTED"
                )

            # Not eligible for waiver or escalation - use terminal_outcome from config
            terminal_outcome = routing.get("terminal_outcome")
            terminal_reason = routing.get("terminal_reason", "MAX_RETRIES_EXCEEDED")

            return (
                LoopAction.TERMINATE.value,
                f"Retry limit exceeded for {failure_class.value}: {terminal_reason}",
                terminal_outcome
            )

        # Retry budget still available
        default_action = routing.get("default_action", "RETRY")

        if default_action == "TERMINATE":
            # Immediate termination per config (e.g., SYNTAX_ERROR)
            terminal_outcome = routing.get("terminal_outcome")
            terminal_reason = routing.get("terminal_reason", "CRITICAL_FAILURE")
            return (
                LoopAction.TERMINATE.value,
                f"{failure_class.value} triggers immediate termination: {terminal_reason}",
                terminal_outcome
            )
        else:
            # RETRY
            return (
                LoopAction.RETRY.value,
                f"Retrying {failure_class.value} ({retry_count + 1}/{retry_limit} attempts)",
                None
            )

    def _count_retries_for_class(
        self,
        ledger: AttemptLedger,
        failure_class: FailureClass
    ) -> int:
        """
        Count how many consecutive retries have occurred for this failure class.

        Only counts consecutive failures of the same class from the most recent
        attempt backwards. Resets if a different failure class or success occurs.

        Args:
            ledger: Attempt ledger with history
            failure_class: FailureClass to count

        Returns:
            Count of consecutive retries (0 if last attempt was success)
        """
        history = ledger.history
        if not history:
            return 0

        count = 0
        # Count backwards from most recent attempt
        for attempt in reversed(history):
            # Stop counting if we hit a success
            if attempt.success:
                break

            # Stop counting if we hit a different failure class
            try:
                attempt_fc = FailureClass(attempt.failure_class)
            except ValueError:
                attempt_fc = FailureClass.UNKNOWN

            if attempt_fc != failure_class:
                break

            count += 1

        return count

    def _check_escalation_triggers(self, ledger: AttemptLedger) -> bool:
        """
        Check if escalation triggers are present (P0.4 governance posture).

        Escalation triggers:
        - Governance surfaces touched (docs/00_foundations/, docs/01_governance/)
        - Protected paths modified
        - Constitutional files changed

        Args:
            ledger: Attempt ledger with history

        Returns:
            True if escalation required, False otherwise
        """
        history = ledger.history
        if not history:
            return False

        # Protected path patterns for governance surfaces
        protected_patterns = [
            "docs/00_foundations/",
            "docs/01_governance/",
            "config/governance/"
        ]

        # Check if any protected paths were touched in the last attempt
        last_attempt = history[-1]

        # Check changed_files list for protected paths
        # AttemptRecord has changed_files (List[str]), not diff_summary
        if hasattr(last_attempt, 'changed_files') and last_attempt.changed_files:
            for changed_file in last_attempt.changed_files:
                for pattern in protected_patterns:
                    if changed_file.startswith(pattern):
                        return True

        return False

    def _check_waiver_eligibility(self, failure_class: FailureClass) -> bool:
        """
        Check if failure class is eligible for waiver request.

        Args:
            failure_class: FailureClass to check

        Returns:
            True if waiver eligible, False otherwise
        """
        waiver_rules = self.config.waiver_rules

        # Get eligible and ineligible lists
        eligible = waiver_rules.get("eligible_failure_classes", [])
        ineligible = waiver_rules.get("ineligible_failure_classes", [])

        # Check explicit ineligibility first (takes precedence)
        if failure_class.name in ineligible:
            return False

        # Check explicit eligibility
        if failure_class.name in eligible:
            return True

        # Default: not eligible
        return False
