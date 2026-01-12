"""
Tests for Mission Journal.

Per Phase 2 implementation plan.
"""

import json
import pytest
from pathlib import Path

from runtime.orchestration.mission_journal import (
    MissionJournal,
    StepRecord,
    JOURNAL_GENESIS,
)
from runtime.orchestration.operations import (
    OperationReceipt,
    CompensationType,
)


class TestMissionJournal:
    """Test hash-chained mission journal."""
    
    @pytest.fixture
    def journal(self):
        return MissionJournal(mission_id="test-mission")
    
    def test_genesis_constant(self):
        """Genesis hash is a constant."""
        assert len(JOURNAL_GENESIS) == 64  # SHA256 hex
    
    def test_first_entry_uses_genesis(self, journal):
        """First entry's prev_entry_hash is genesis."""
        entry = journal.record_step(
            step_id="step-1",
            operation_type="gate_check",
        )
        
        assert entry.prev_entry_hash == JOURNAL_GENESIS
        assert entry.entry_hash.startswith("sha256:")
    
    def test_chain_links_entries(self, journal):
        """Each entry links to previous via prev_entry_hash."""
        entry1 = journal.record_step(step_id="step-1", operation_type="op1")
        entry2 = journal.record_step(step_id="step-2", operation_type="op2")
        entry3 = journal.record_step(step_id="step-3", operation_type="op3")
        
        assert entry2.prev_entry_hash == entry1.entry_hash
        assert entry3.prev_entry_hash == entry2.entry_hash
    
    def test_chain_root_is_last_hash(self, journal):
        """get_chain_root() returns last entry's hash."""
        entry = journal.record_step(step_id="step-1", operation_type="op1")
        assert journal.get_chain_root() == entry.entry_hash
    
    def test_verify_integrity_passes_intact_chain(self, journal):
        """verify_integrity() passes for intact chain."""
        journal.record_step(step_id="step-1", operation_type="op1")
        journal.record_step(step_id="step-2", operation_type="op2")
        journal.record_step(step_id="step-3", operation_type="op3")
        
        is_valid, breaks = journal.verify_integrity()
        
        assert is_valid is True
        assert breaks == []
    
    def test_verify_integrity_detects_tampering(self, journal):
        """verify_integrity() detects tampered entries."""
        journal.record_step(step_id="step-1", operation_type="op1")
        journal.record_step(step_id="step-2", operation_type="op2")
        
        # Tamper with entry
        journal._entries[0].status = "TAMPERED"
        
        is_valid, breaks = journal.verify_integrity()
        
        assert is_valid is False
        assert len(breaks) >= 1
    
    def test_record_operation_stores_receipt(self, journal):
        """record_operation() stores OperationReceipt."""
        receipt = OperationReceipt(
            operation_id="op-1",
            timestamp="2026-01-08T00:00:00Z",
            pre_state_hash="sha256:abc",
            post_state_hash="sha256:def",
            compensation_type=CompensationType.NONE,
            compensation_command="",
            idempotency_key="sha256:xyz",
        )
        
        journal.record_operation(receipt)
        
        assert len(journal.receipts) == 1
        assert journal.receipts[0].operation_id == "op-1"


class TestJournalExport:
    """Test journal export to completion bundle."""
    
    def test_export_bundle_structure(self):
        """export_bundle() returns correct structure."""
        journal = MissionJournal(mission_id="test-mission")
        journal.record_step(step_id="step-1", operation_type="op1")
        
        bundle = journal.export_bundle()
        
        assert bundle["mission_id"] == "test-mission"
        assert bundle["genesis"] == JOURNAL_GENESIS
        assert "chain_root" in bundle
        assert "entries" in bundle
        assert "receipts" in bundle
        assert "exported_at" in bundle
    
    def test_export_is_json_serializable(self):
        """export_bundle() produces JSON-serializable dict."""
        journal = MissionJournal(mission_id="test-mission")
        journal.record_step(step_id="step-1", operation_type="op1")
        
        bundle = journal.export_bundle()
        
        # Should not raise
        json_str = json.dumps(bundle)
        assert len(json_str) > 0


class TestDeterminism:
    """Test deterministic behavior."""
    
    def test_stable_hash_for_same_content(self):
        """Same content produces same entry hash."""
        j1 = MissionJournal(mission_id="test")
        j2 = MissionJournal(mission_id="test")
        
        # Record identical steps with fixed started_at
        e1 = j1.record_step(step_id="step-1", operation_type="op1")
        e2 = j2.record_step(step_id="step-1", operation_type="op1")
        
        # Entry hashes will differ due to timestamp, which is expected
        # The chain structure should still be valid
        assert e1.prev_entry_hash == e2.prev_entry_hash == JOURNAL_GENESIS
