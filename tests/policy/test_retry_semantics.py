"""
T4: Loop RETRY Semantics Tests

Tests for config-driven RETRY semantics per P0.7:
- Loop rule returns RETRY and controller performs another attempt
- Invalid loop decision fails closed
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from dataclasses import dataclass
from typing import Optional, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runtime.orchestration.loop.policy import LoopPolicy, ConfigDrivenLoopPolicy
from runtime.orchestration.loop.taxonomy import LoopAction, FailureClass


@dataclass
class MockAttemptRecord:
    """Mock attempt record for testing."""
    attempt_id: int = 1
    success: bool = False
    failure_class: Optional[str] = None
    terminal_reason: Optional[str] = None
    diff_hash: Optional[str] = None


class MockLedger:
    """Mock ledger for testing."""
    def __init__(self, records: List[MockAttemptRecord] = None):
        self.history = records or []


class TestRetrySemanticsEndToEnd:
    """T4: Loop RETRY semantics tests."""
    
    def test_retry_decision_triggers_retry_action(self):
        """RETRY decision from config produces RETRY action."""
        loop_rules = [
            {
                "rule_id": "loop.test-failure",
                "decision": "RETRY",
                "priority": 100,
                "match": {"failure_class": "test_failure"}
            }
        ]
        
        policy = ConfigDrivenLoopPolicy(loop_rules)
        
        # Create ledger with failed attempt
        record = MockAttemptRecord(
            attempt_id=1,
            success=False,
            failure_class=FailureClass.TEST_FAILURE.value,
            diff_hash="abc123"
        )
        ledger = MockLedger([record])
        
        action, reason = policy.decide_next_action(ledger)
        
        assert action == LoopAction.RETRY.value
        assert "retry" in reason.lower()
    
    def test_terminate_decision_triggers_terminate_action(self):
        """TERMINATE decision from config produces TERMINATE action."""
        loop_rules = [
            {
                "rule_id": "loop.syntax-error",
                "decision": "TERMINATE",
                "priority": 100,
                "match": {"failure_class": "syntax_error"},
                "on_match": {"terminal_reason": "critical_failure"}
            }
        ]
        
        policy = ConfigDrivenLoopPolicy(loop_rules)
        
        record = MockAttemptRecord(
            attempt_id=1,
            success=False,
            failure_class=FailureClass.SYNTAX_ERROR.value,
            diff_hash="abc123"
        )
        ledger = MockLedger([record])
        
        action, reason = policy.decide_next_action(ledger)
        
        assert action == LoopAction.TERMINATE.value
    
    def test_escalate_with_empty_allowlist_triggers_escalation_requested(self, tmp_path):
        """ESCALATE with empty allowlist produces ESCALATION_REQUESTED."""
        loop_rules = [
            {
                "rule_id": "loop.timeout",
                "decision": "ESCALATE",
                "priority": 100,
                "match": {"failure_class": "timeout"}
            }
        ]
        escalation_config = {
            "allowlist": [],
            "bootstrap_mode": True,
            "ttl_seconds": 3600
        }
        
        policy = ConfigDrivenLoopPolicy(loop_rules, escalation_config)
        
        record = MockAttemptRecord(
            attempt_id=1,
            success=False,
            failure_class=FailureClass.TIMEOUT.value,
            diff_hash="abc123"
        )
        ledger = MockLedger([record])
        
        action, reason = policy.decide_next_action(ledger)
        
        assert action == LoopAction.ESCALATE.value
        assert "ESCALATION_REQUESTED" in reason
    
    def test_config_driven_retry_vs_hardcoded(self):
        """Config-driven policy produces same RETRY for matching failure."""
        # Create effective config
        effective_config = {
            "loop_rules": [
                {
                    "rule_id": "loop.test-failure",
                    "decision": "RETRY",
                    "priority": 100,
                    "match": {"failure_class": "test_failure"}
                }
            ],
            "escalation": {"allowlist": [], "bootstrap_mode": True}
        }
        
        # Config-driven policy
        config_policy = LoopPolicy(effective_config)
        
        # Hardcoded policy (no config)
        hardcoded_policy = LoopPolicy(None)
        
        record = MockAttemptRecord(
            attempt_id=1,
            success=False,
            failure_class=FailureClass.TEST_FAILURE.value,
            diff_hash="abc123"
        )
        ledger = MockLedger([record])
        
        config_action, _ = config_policy.decide_next_action(ledger)
        hardcoded_action, _ = hardcoded_policy.decide_next_action(ledger)
        
        # Both should produce RETRY for test_failure
        assert config_action == LoopAction.RETRY.value
        assert hardcoded_action == LoopAction.RETRY.value
    
    def test_unknown_failure_class_handled(self):
        """Unknown failure class falls through to default handling."""
        loop_rules = [
            {
                "rule_id": "loop.specific",
                "decision": "RETRY",
                "priority": 100,
                "match": {"failure_class": "test_failure"}
            }
        ]
        
        policy = ConfigDrivenLoopPolicy(loop_rules)
        
        # Use a failure class not matched by rules
        record = MockAttemptRecord(
            attempt_id=1,
            success=False,
            failure_class="some_other_failure",
            diff_hash="abc123"
        )
        ledger = MockLedger([record])
        
        action, reason = policy.decide_next_action(ledger)
        
        # Should fall through to default TERMINATE
        assert action == LoopAction.TERMINATE.value
        assert "fall-through" in reason.lower()
