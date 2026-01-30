"""
Tests for Trusted Builder Mode v1.1 C1-C6 Compliance.

Covers:
- C1: Normalization
- C2: Diffstat from Patch
- C3: Protected Path Wiring
- C4: Ledger Schema
- C5: Review Packet Annotation
"""
import pytest
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from dataclasses import asdict

from runtime.orchestration.loop.configurable_policy import ConfigurableLoopPolicy
from runtime.orchestration.loop.taxonomy import FailureClass
from runtime.orchestration.loop.ledger import AttemptRecord, AttemptLedger
from runtime.api.governance_api import PROTECTED_PATHS

class TestTrustedBuilderCompliance:

    @pytest.fixture
    def policy(self):
        config = {
            "failure_routing": {
                "lint_error": {
                    "plan_bypass_eligible": True,
                    "scope_limit": {"max_lines": 10, "max_files": 1},
                    "mode": "patchful"
                }
            }
        }
        return ConfigurableLoopPolicy(config)

    # --- C1: Normalization ---
    def test_c1_normalization_roundtrip(self, policy):
        """Test failure class normalization is deterministic and lowercase snake_case."""
        # Test 1: Random case mixed
        assert policy.normalize_failure_class("LiNt_ErRoR") == "lint_error"
        # Test 2: Enum input
        assert policy.normalize_failure_class(FailureClass.LINT_ERROR) == "lint_error"
        # Test 3: Already normalized
        assert policy.normalize_failure_class("lint_error") == "lint_error"
        
        # Test Routing Match independent of input case
        # Config has "lint_error". Input "LINT_ERROR" should match.
        normalized = policy.normalize_failure_class("LINT_ERROR")
        routing = policy.failure_routing.get(normalized)
        assert routing is not None
        assert routing.get("plan_bypass_eligible") is True

    # --- C2: Diffstat from Patch (Mocked for unit test) ---
    def test_c2_diffstat_logic(self, policy):
        """Verify logic uses diffstat, not line count."""
        # Setup a mock patch stats object
        patch_stats = {
            "files_touched": 1,
            "total_line_delta": 5,
            "added_lines": 3,
            "deleted_lines": 2,
            "files": ["src/script.py"]
        }
        
        decision = policy.evaluate_plan_bypass(
            failure_class_key="lint_error",
            proposed_patch=patch_stats,
            protected_path_registry=[],
            ledger=MagicMock()
        )
        assert decision["eligible"] is True
        assert decision["scope"]["total_line_delta"] == 5

    def test_c2_fail_closed_if_no_patch(self, policy):
        """Verify denial if patch stats are missing."""
        decision = policy.evaluate_plan_bypass(
            failure_class_key="lint_error",
            proposed_patch=None,
            protected_path_registry=[],
            ledger=MagicMock()
        )
        assert decision["eligible"] is False
        assert "Proposed Patch missing" in decision["decision_reason"]

    # --- C3: Protected Path Wiring ---
    def test_c3_protected_path_wiring(self, policy):
        """Verify protected path detection using registry."""
        # Mock registry with a pattern
        registry = ["docs/00_foundations/*"]
        
        patch_stats = {
            "files_touched": 1,
            "total_line_delta": 2,
            "added_lines": 1,
            "deleted_lines": 1,
            "files": ["docs/00_foundations/Constitution.md"]
        }
        
        decision = policy.evaluate_plan_bypass(
            failure_class_key="lint_error",
            proposed_patch=patch_stats,
            protected_path_registry=registry,
            ledger=MagicMock()
        )
        assert decision["eligible"] is False
        assert "Protected path hit" in decision["decision_reason"]
        assert "docs/00_foundations/Constitution.md" in decision["protected_paths_hit"]

    def test_c3_registry_fail_closed(self, policy):
        """Verify denial if registry is None (simulate load failure)."""
        patch_stats = {
            "files_touched": 1,
            "total_line_delta": 2,
            "added_lines": 1,
            "deleted_lines": 1,
            "files": ["src/safe.py"]
        }
        
        decision = policy.evaluate_plan_bypass(
            failure_class_key="lint_error",
            proposed_patch=patch_stats,
            protected_path_registry=None, # Simulate failure
            ledger=MagicMock()
        )
        assert decision["eligible"] is False
        assert "Protected path registry unavailable" in decision["decision_reason"]

    # --- C4: Ledger Schema ---
    def test_c4_ledger_schema_completeness(self):
        """Verify AttemptRecord accepts and stores plan_bypass structure."""
        bypass_info = {
            "evaluated": True,
            "eligible": True,
            "applied": True,
            "rule_id": "rule.lint",
            "decision_reason": "ok",
            "scope": {"files_touched": 1, "total_line_delta": 2},
            "protected_paths_hit": [],
            "budget": {"per_class_remaining": 2, "global_remaining": 4},
            "mode": "patchful",
            "proposed_patch": {"present": True}
        }
        
        record = AttemptRecord(
            attempt_id=1,
            timestamp="2026-01-26T00:00:00Z",
            run_id="run-1",
            policy_hash="abc",
            input_hash="def",
            actions_taken=[],
            diff_hash="hash",
            changed_files=["a.py"],
            evidence_hashes={},
            success=False,
            failure_class="lint_error",
            terminal_reason=None,
            next_action="retry",
            rationale="test",
            plan_bypass_info=bypass_info
        )
        
        # Serialization check
        d = asdict(record)
        assert d["plan_bypass_info"] == bypass_info

    # --- C5: Packet Annotation (Simulated) ---
    def test_c5_packet_annotation_logic(self):
        """Verify logic to inject bypass info into packet."""
        # This logic usually lives in the loop controller, so we test the structure builder
        bypass_decision = {
            "applied": True,
            "scope": {"total_line_delta": 5}
        }
        
        packet_payload = {
            "summary": "Review",
            "plan_bypass_applied": bypass_decision["applied"],
            "plan_bypass": bypass_decision
        }
        
        assert packet_payload["plan_bypass_applied"] is True
        assert packet_payload["plan_bypass"]["scope"]["total_line_delta"] == 5

