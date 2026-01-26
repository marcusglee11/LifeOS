"""
ConfigurableLoopPolicy - Config-driven loop policy Phase B.1

Implements:
- Retry budgets from config
- Waiver eligibility checking
- Escalation trigger detection
- Deadlock/oscillation detection (Phase A logic preserved)
- Terminal outcome routing
- Plan bypass eligibility (Art. XVIII §5)
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional, Tuple, List
import os
from pathlib import PurePosixPath
from runtime.orchestration.loop.ledger import AttemptLedger
from runtime.orchestration.loop.taxonomy import FailureClass, TerminalReason
from runtime.orchestration.loop import waiver_artifact
from runtime.governance.self_mod_protection import PROTECTED_PATHS, is_protected

@dataclass
class PlanBypassDecision:
    """Structured decision for plan bypass (C4)."""
    evaluated: bool
    eligible: bool
    applied: bool
    rule_id: Optional[str]
    decision_reason: str
    scope: Dict[str, Any]
    protected_paths_hit: List[str]
    budget: Dict[str, int]
    mode: str
    proposed_patch: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# Governance-controlled paths (from Article XIII §4)
GOVERNANCE_CONTROLLED_PATHS = [
    "docs/00_foundations/",
    "docs/01_governance/",
    "runtime/governance/",
    "GEMINI.md",
]

GOVERNANCE_PATTERNS = [
    "*Constitution*.md",
    "*Protocol*.md",
]


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
        
        # C1: Normalize failure class keys in config for deterministic lookup
        self._normalize_config_keys()

    def normalize_failure_class(self, failure_class: Any) -> str:
        """
        C1: Canonical normalization to lowercase snake_case.
        """
        if isinstance(failure_class, FailureClass):
            return failure_class.value.lower()
        return str(failure_class).strip().lower()

    def _normalize_config_keys(self):
        """Ensure all routing keys are normalized."""
        normalized_routing = {}
        for k, v in self.failure_routing.items():
            normalized_routing[self.normalize_failure_class(k)] = v
        self.failure_routing = normalized_routing
    
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

        return False

    def evaluate_plan_bypass(
        self,
        *,
        failure_class_key: str,
        proposed_patch: Optional[Dict[str, Any]],
        protected_path_registry: Optional[List[str]],
        ledger: AttemptLedger
    ) -> Dict[str, Any]:
        """
        Evaluate if plan bypass is eligible (C3, C4).
        
        Args:
            failure_class_key: Normalized failure class (snake_case)
            proposed_patch: Dict with {files_touched, total_line_delta, ...}
            protected_path_registry: List of protected patterns (Authoritative)
            ledger: The attempt ledger
            
        Returns:
            Dict matching PlanBypassDecision structure
        """
        # Default decision structure (Denied)
        decision = {
            "evaluated": True,
            "eligible": False,
            "applied": False,
            "rule_id": None,
            "decision_reason": "Default deny",
            "scope": {},
            "protected_paths_hit": [],
            "budget": {"per_class_remaining": 0, "global_remaining": 0},
            "mode": "unknown",
            "proposed_patch": {"present": False}
        }

        # C1: Ensure key is normalized
        fc_norm = self.normalize_failure_class(failure_class_key)
        routing = self.failure_routing.get(fc_norm, {})
        decision["rule_id"] = f"loop.{fc_norm}" # Conceptual ID
        
        # 1. Check if rule exists and is eligible
        if not routing.get("plan_bypass_eligible", False):
            decision["decision_reason"] = f"Failure class {fc_norm} not plan_bypass_eligible"
            return decision
            
        decision["mode"] = routing.get("mode", "patchful")

        # 2. C2: Check Proposed Patch Existence (Fail-Closed)
        if decision["mode"] == "patchful":
            if not proposed_patch:
                decision["decision_reason"] = "Proposed Patch missing (fail-closed)"
                return decision
            
            # P0.1: Evasion Check (Symlinks/Suspicious Modes)
            if proposed_patch.get("has_suspicious_modes"):
                decision["decision_reason"] = "Suspicious file modes (symlink/rename) detected"
                return decision

            decision["proposed_patch"] = {"present": True, **proposed_patch}
            decision["scope"] = {
                "files_touched": proposed_patch.get("files_touched", 999), # Fail safe
                "total_line_delta": proposed_patch.get("total_line_delta", 9999),
                "files": proposed_patch.get("files", [])
            }
        elif decision["mode"] == "no_change_rerun":
             # Enforce no changes
             if proposed_patch:
                 decision["decision_reason"] = "no_change_rerun cannot have a proposed patch"
                 return decision
             decision["scope"] = {"files_touched": 0, "total_line_delta": 0, "files": []}
             decision["proposed_patch"]["present"] = False

        # 3. C3: Check Protected Paths (Fail-Closed)
        if protected_path_registry is None:
            decision["decision_reason"] = "Protected path registry unavailable (fail-closed)"
            return decision
            
        touched_files = decision["scope"].get("files", [])
        protected_hits = []
        
        # P0.1: Path Normalization
        for f in touched_files:
            # Reject absolute/traversal immediately
            if os.path.isabs(f) or ".." in f or f.startswith("/") or ":" in f:
                 decision["decision_reason"] = f"Absolute or traversal path denied: {f}"
                 return decision
            
            # Normalize: forward slashes, lowercase (for case-insensitive match safety)
            # We assume protected registry is also normalized to lowercase if we want strict matching,
            # but standardizing the input is the first step.
            f_norm = f.replace("\\", "/").lower()
            
            # Additional Traversal check after replace
            if "/../" in f_norm or f_norm.startswith("../") or f_norm.endswith("/.."):
                decision["decision_reason"] = f"Traversal path denied: {f}"
                return decision

            for pattern in protected_path_registry:
                # Assume registry patterns are also normalized or we normalize them?
                # Better to be strict: normalize pattern too if not sure, but registry should be authoritative.
                # Use fnmatch on normalized strings
                pattern_norm = pattern.lower()
                if fnmatch.fnmatch(f_norm, pattern_norm):
                    protected_hits.append(f)
                    break
        
        decision["protected_paths_hit"] = protected_hits
        if protected_hits:
            decision["decision_reason"] = f"Protected path hit: {protected_hits[0]}"
            return decision

        # 4. Check Scope Limits
        scope_limit = routing.get("scope_limit", {})
        max_lines = scope_limit.get("max_lines", 50)
        max_files = scope_limit.get("max_files", 3)
        
        if decision["scope"].get("total_line_delta", 0) > max_lines:
            decision["decision_reason"] = f"Scope: lines {decision['scope']['total_line_delta']} > {max_lines}"
            return decision
            
        if decision["scope"].get("files_touched", 0) > max_files:
            decision["decision_reason"] = f"Scope: files {decision['scope']['files_touched']} > {max_files}"
            return decision

        # 5. Check Budgets (Simplified stub - assume global=5, per_class=3)
        # LIFEOS_TODO: Connect to real budget controller
        decision["eligible"] = True
        decision["decision_reason"] = "Eligible"
        return decision

    def _is_governance_path(self, path: str) -> bool:
        """Check if path is governance-controlled per Article XIII §4."""
        # Check prefixes
        for prefix in GOVERNANCE_CONTROLLED_PATHS:
            if path.startswith(prefix):
                return True

        # Check patterns
        for pattern in GOVERNANCE_PATTERNS:
            if fnmatch.fnmatch(path, pattern):
                return True

        return False
