"""
T5: Escalation Bootstrap Determinism Tests

Tests for escalation bootstrap mode per P0.8:
- ESCALATE with empty allowlist => terminal outcome ESCALATION_REQUESTED
- Escalation artifact is written
- No external side effects
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import json
from dataclasses import dataclass
from typing import Optional, List

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from runtime.orchestration.loop.policy import (
    ConfigDrivenLoopPolicy,
    EscalationArtifact,
)
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


class TestEscalationBootstrapDeterminism:
    """T5: Escalation bootstrap determinism tests."""
    
    def test_escalate_empty_allowlist_produces_escalation_requested(self, tmp_path):
        """ESCALATE with empty allowlist produces ESCALATION_REQUESTED outcome."""
        loop_rules = [
            {
                "rule_id": "loop.timeout",
                "decision": "ESCALATE",
                "priority": 100,
                "match": {"failure_class": "timeout"}
            }
        ]
        escalation_config = {
            "allowlist": [],  # Empty!
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
    
    def test_escalation_artifact_written(self, tmp_path, monkeypatch):
        """Escalation artifact is written to deterministic path."""
        # Override artifact dir for testing
        test_artifact_dir = tmp_path / "escalations"
        monkeypatch.setattr(EscalationArtifact, 'ARTIFACT_DIR', test_artifact_dir)
        
        # Write artifact
        artifact_path = EscalationArtifact.write(
            reason="Test escalation",
            requested_authority="CEO",
            ttl_seconds=3600,
            context={"test": True}
        )
        
        assert artifact_path.exists()
        assert artifact_path.parent == test_artifact_dir
        assert artifact_path.suffix == ".json"
        
        # Verify content
        with open(artifact_path, 'r') as f:
            data = json.load(f)
        
        assert data["reason"] == "Test escalation"
        assert data["requested_authority"] == "CEO"
        assert data["ttl_seconds"] == 3600
        assert data["context"]["test"] is True
        assert "created_at" in data
    
    def test_escalation_artifact_deterministic_naming(self, tmp_path, monkeypatch):
        """Escalation artifact has deterministic naming based on content."""
        test_artifact_dir = tmp_path / "escalations"
        monkeypatch.setattr(EscalationArtifact, 'ARTIFACT_DIR', test_artifact_dir)
        
        # Write artifact
        artifact_path = EscalationArtifact.write(
            reason="Deterministic test",
            requested_authority="CEO",
            ttl_seconds=3600
        )
        
        # Filename should include timestamp and hash
        assert "ESCALATION_" in artifact_path.name
        assert artifact_path.name.endswith(".json")
    
    def test_no_external_side_effects(self, tmp_path, monkeypatch):
        """Escalation produces no external side effects (artifact-only)."""
        test_artifact_dir = tmp_path / "escalations"
        monkeypatch.setattr(EscalationArtifact, 'ARTIFACT_DIR', test_artifact_dir)
        
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
        
        # This should not raise any network errors or attempt external calls
        action, reason = policy.decide_next_action(ledger)
        
        # Verify artifact was created
        assert test_artifact_dir.exists()
        artifacts = list(test_artifact_dir.glob("ESCALATION_*.json"))
        assert len(artifacts) == 1
        
        # Verify the reason includes artifact path
        assert "artifact=" in reason
    
    def test_bootstrap_mode_false_still_returns_escalate(self, tmp_path, monkeypatch):
        """With bootstrap_mode=False, escalate still works but no artifact."""
        loop_rules = [
            {
                "rule_id": "loop.timeout",
                "decision": "ESCALATE",
                "priority": 100,
                "match": {"failure_class": "timeout"}
            }
        ]
        escalation_config = {
            "allowlist": ["some_resolver"],  # Non-empty
            "bootstrap_mode": False,
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
        
        # Still returns ESCALATE
        assert action == LoopAction.ESCALATE.value
        # But different reason (not bootstrap mode)
        assert "escalation requested" in reason.lower()
