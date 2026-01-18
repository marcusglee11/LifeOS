import pytest
import json
from pathlib import Path
from runtime.orchestration.loop.ledger import AttemptLedger, AttemptRecord, LedgerHeader, LedgerIntegrityError

@pytest.fixture
def ledger_path(tmp_path):
    return tmp_path / "ledger.jsonl"

def test_ledger_initialization(ledger_path):
    ledger = AttemptLedger(ledger_path)
    header = LedgerHeader(policy_hash="abc", handoff_hash="123", run_id="run1")
    ledger.initialize(header)
    
    assert ledger_path.exists()
    with open(ledger_path) as f:
        lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["type"] == "header"
        assert data["run_id"] == "run1"

def test_ledger_append_and_hydrate(ledger_path):
    ledger = AttemptLedger(ledger_path)
    header = LedgerHeader(policy_hash="abc", handoff_hash="123", run_id="run1")
    ledger.initialize(header)
    
    record = AttemptRecord(
        attempt_id=1,
        timestamp="2026-01-01T00:00:00Z",
        run_id="run1",
        policy_hash="abc",
        input_hash="123",
        actions_taken=["cmd1"],
        diff_hash="d1",
        changed_files=["f1"],
        evidence_hashes={"e1": "h1"},
        success=False,
        failure_class="test_failure",
        terminal_reason=None,
        next_action="retry",
        rationale="test"
    )
    
    ledger.append(record)
    
    # New instance to hydrate
    ledger2 = AttemptLedger(ledger_path)
    assert ledger2.hydrate() is True
    assert ledger2.header["run_id"] == "run1"
    assert len(ledger2.history) == 1
    assert ledger2.history[0].attempt_id == 1
    assert ledger2.history[0].failure_class == "test_failure"

def test_ledger_integrity_gap(ledger_path):
    ledger = AttemptLedger(ledger_path)
    header = LedgerHeader(policy_hash="abc", handoff_hash="123", run_id="run1")
    ledger.initialize(header)
    
    r1 = AttemptRecord(attempt_id=1, timestamp="", run_id="run1", policy_hash="", input_hash="", actions_taken=[], diff_hash="", changed_files=[], evidence_hashes={}, success=False, failure_class="", terminal_reason=None, next_action="", rationale="")
    r3 = AttemptRecord(attempt_id=3, timestamp="", run_id="run1", policy_hash="", input_hash="", actions_taken=[], diff_hash="", changed_files=[], evidence_hashes={}, success=False, failure_class="", terminal_reason=None, next_action="", rationale="")
    
    ledger.append(r1)
    
    # Append check
    from runtime.orchestration.loop.ledger import LedgerError
    with pytest.raises(LedgerError):
        ledger.append(r3)

def test_ledger_corrupt_file(ledger_path):
    with open(ledger_path, 'w') as f:
        f.write('{"type": "header"}\n')
        f.write('NOT JSON\n')
        
    ledger = AttemptLedger(ledger_path)
    with pytest.raises(LedgerIntegrityError):
        ledger.hydrate()
