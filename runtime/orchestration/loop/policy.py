"""
Loop Policy Adapter - Config-driven loop policy evaluation.

v1.2.1: Now wired to consume config-driven loop rules per P0.7.
- Loads loop_rules from effective config
- Evaluates failure_class and context to return RETRY/TERMINATE/ESCALATE/WAIVER
- Escalation bootstrap: deterministic ESCALATION_REQUESTED on empty allowlist
"""

from __future__ import annotations

import os
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from .taxonomy import FailureClass, LoopAction, TerminalReason, TerminalOutcome
from .ledger import AttemptLedger


class EscalationArtifact:
    """Writes deterministic escalation artifacts per P0.8."""
    
    ARTIFACT_DIR = Path("artifacts/escalations/Policy_Engine")
    
    @classmethod
    def write(
        cls,
        reason: str,
        requested_authority: str = "CEO",
        ttl_seconds: int = 3600,
        context: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Write a deterministic escalation artifact.
        
        Returns:
            Path to the written artifact
        """
        artifact_dir = cls.ARTIFACT_DIR
        artifact_dir.mkdir(parents=True, exist_ok=True)
        
        # Create deterministic filename based on content hash
        import hashlib
        payload = {
            "reason": reason,
            "requested_authority": requested_authority,
            "ttl_seconds": ttl_seconds,
            "context": context or {},
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        # Use content hash for deterministic naming
        content_str = json.dumps(payload, sort_keys=True)
        content_hash = hashlib.sha256(content_str.encode()).hexdigest()[:16]
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        
        filename = f"ESCALATION_{timestamp}_{content_hash}.json"
        artifact_path = artifact_dir / filename
        
        with open(artifact_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)
        
        return artifact_path


class ConfigDrivenLoopPolicy:
    """
    Config-driven loop policy that consumes loop_rules.yaml.
    
    Decisions: RETRY, TERMINATE, ESCALATE, WAIVER
    """
    
    def __init__(self, loop_rules: List[Dict[str, Any]], escalation_config: Optional[Dict[str, Any]] = None):
        """
        Initialize with loop rules from effective config.
        
        Args:
            loop_rules: List of loop rule dicts from config
            escalation_config: Escalation settings from config
        """
        self.rules = sorted(loop_rules, key=lambda r: -r.get("priority", 0))
        self.escalation_config = escalation_config or {}
    
    def decide_next_action(
        self,
        ledger: AttemptLedger,
        now: Optional[datetime] = None
    ) -> Tuple[str, str]:
        """
        Decide the next action based on ledger history and config rules.
        
        Args:
            ledger: Attempt ledger with history
            now: Optional fixed datetime (unused in this policy variant)
        
        Returns:
            (LoopAction.value, rationale/reason)
        """

        history = ledger.history
        if not history:
            # Start of run
            return LoopAction.RETRY.value, "Start"
        
        last_attempt = history[-1]
        
        # 1. Check for Progress / Deadlock / Oscillation (algorithmic, not config-driven)
        if len(history) >= 2:
            prev_attempt = history[-2]
            if last_attempt.diff_hash and prev_attempt.diff_hash:
                if last_attempt.diff_hash == prev_attempt.diff_hash:
                    return LoopAction.TERMINATE.value, TerminalReason.NO_PROGRESS.value
        
        if len(history) >= 3:
            osc_attempt = history[-3]
            if last_attempt.diff_hash and osc_attempt.diff_hash:
                if last_attempt.diff_hash == osc_attempt.diff_hash:
                    return LoopAction.TERMINATE.value, TerminalReason.OSCILLATION_DETECTED.value
        
        # 2. Check success
        if last_attempt.success:
            return LoopAction.TERMINATE.value, TerminalReason.PASS.value
        
        # 3. Match against config-driven rules
        f_class = last_attempt.failure_class
        
        for rule in self.rules:
            match = rule.get("match", {})
            
            # Check failure_class match
            if "failure_class" in match:
                if match["failure_class"] != f_class:
                    continue
            
            # Check terminal_reason match
            if "terminal_reason" in match:
                if match["terminal_reason"] != last_attempt.terminal_reason:
                    continue
            
            # Rule matched - get decision
            decision = rule.get("decision", "TERMINATE")
            rule_id = rule.get("rule_id", "unknown")
            
            # Handle ESCALATE with bootstrap mode
            if decision == "ESCALATE":
                return self._handle_escalate(rule, f_class)
            
            # Map decision to LoopAction
            if decision == "RETRY":
                return LoopAction.RETRY.value, f"Rule {rule_id}: retry for {f_class}"
            elif decision == "TERMINATE":
                on_match = rule.get("on_match", {})
                reason = on_match.get("terminal_reason", TerminalReason.CRITICAL_FAILURE.value)
                return LoopAction.TERMINATE.value, reason
            elif decision == "WAIVER":
                return LoopAction.WAIVER.value, f"Rule {rule_id}: waiver requested"
            else:
                # Unknown decision - fail closed
                return LoopAction.TERMINATE.value, f"Unknown decision {decision} - fail closed"
        
        # No rule matched - default fallback
        return LoopAction.TERMINATE.value, "Default fall-through blocked"
    
    def _handle_escalate(self, rule: Dict[str, Any], failure_class: str) -> Tuple[str, str]:
        """
        Handle ESCALATE decision with bootstrap mode support.
        
        If allowlist is empty and bootstrap_mode is true:
        - Return ESCALATION_REQUESTED terminal outcome
        - Write escalation artifact
        - No external side effects
        """
        allowlist = self.escalation_config.get("allowlist", [])
        bootstrap_mode = self.escalation_config.get("bootstrap_mode", True)
        
        rule_id = rule.get("rule_id", "unknown")
        
        if not allowlist and bootstrap_mode:
            # P0.8: Bootstrap mode - write artifact, return deterministic outcome
            artifact_path = EscalationArtifact.write(
                reason=f"Escalation triggered by rule {rule_id} for {failure_class}",
                requested_authority="CEO",
                ttl_seconds=self.escalation_config.get("ttl_seconds", 3600),
                context={"rule_id": rule_id, "failure_class": failure_class}
            )
            
            return LoopAction.ESCALATE.value, f"{TerminalOutcome.ESCALATION_REQUESTED.value}:artifact={artifact_path}"
        
        # Normal escalation path (not implemented in bootstrap mode)
        return LoopAction.ESCALATE.value, f"Rule {rule_id}: escalation requested"


class LoopPolicy:
    """
    Phase A Policy: Now config-aware with fallback to hardcoded.
    """
    
    def __init__(self, effective_config: Optional[Dict[str, Any]] = None):
        """
        Initialize with optional effective config.
        
        If config provided, uses config-driven policy.
        Otherwise falls back to legacy hardcoded behavior.
        """
        self._config_policy: Optional[ConfigDrivenLoopPolicy] = None
        
        if effective_config:
            loop_rules = effective_config.get("loop_rules", [])
            escalation_config = effective_config.get("escalation", {})
            if loop_rules:
                self._config_policy = ConfigDrivenLoopPolicy(loop_rules, escalation_config)
    
    def decide_next_action(
        self,
        ledger: AttemptLedger,
        now: Optional[datetime] = None
    ) -> Tuple[str, str]:
        """
        Decide the next action based on the ledger history.
        
        Args:
            ledger: Attempt ledger with history
            now: Optional fixed datetime for deterministic waiver validation
        
        Returns: (LoopAction.value, rationale/reason)
        """
        # Use config-driven policy if available
        if self._config_policy:
            return self._config_policy.decide_next_action(ledger, now=now)
        
        # Legacy hardcoded fallback
        return self._hardcoded_decide(ledger)

    
    def _hardcoded_decide(self, ledger: AttemptLedger) -> Tuple[str, str]:
        """Legacy hardcoded policy logic (MVP fallback)."""
        history = ledger.history
        if not history:
            return LoopAction.RETRY.value, "Start"
            
        last_attempt = history[-1]
        
        # Check for Progress / Deadlock / Oscillation
        if len(history) >= 2:
            prev_attempt = history[-2]
            if last_attempt.diff_hash and prev_attempt.diff_hash:
                if last_attempt.diff_hash == prev_attempt.diff_hash:
                    return LoopAction.TERMINATE.value, TerminalReason.NO_PROGRESS.value
        
        if len(history) >= 3:
            osc_attempt = history[-3]
            if last_attempt.diff_hash and osc_attempt.diff_hash:
                if last_attempt.diff_hash == osc_attempt.diff_hash:
                    return LoopAction.TERMINATE.value, TerminalReason.OSCILLATION_DETECTED.value

        if last_attempt.success:
            return LoopAction.TERMINATE.value, TerminalReason.PASS.value
            
        f_class = last_attempt.failure_class
        
        if f_class == FailureClass.REVIEW_REJECTION.value:
            return LoopAction.RETRY.value, "Review rejection triggers retry"
            
        elif f_class == FailureClass.TEST_FAILURE.value:
            return LoopAction.RETRY.value, "Test failure triggers retry"
            
        elif f_class == FailureClass.TIMEOUT.value:
            if len(history) >= 2 and history[-2].failure_class == FailureClass.TIMEOUT.value:
                return LoopAction.TERMINATE.value, "Timeout retry limit exceeded"
            return LoopAction.RETRY.value, "Timeout triggers single retry"
            
        elif f_class == FailureClass.SYNTAX_ERROR.value:
            return LoopAction.TERMINATE.value, "Syntax error is fail-closed"
            
        elif f_class == FailureClass.VALIDATION_ERROR.value:
            return LoopAction.TERMINATE.value, "Validation error is fail-closed"
             
        elif f_class == FailureClass.UNKNOWN.value:
            return LoopAction.TERMINATE.value, "Unknown error is fail-closed"
            
        return LoopAction.TERMINATE.value, "Default fall-through blocked"
