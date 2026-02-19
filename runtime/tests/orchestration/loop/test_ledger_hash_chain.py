"""
Ledger Hash-Chain Verification Tests (W7-T01)

Tests for deterministic hash-chain linking, tamper detection,
fail-closed v1.1 enforcement, and tail-truncation detection.
"""
import pytest
import json
from pathlib import Path
from dataclasses import asdict

from runtime.orchestration.loop.ledger import (
    AttemptLedger,
    AttemptRecord,
    LedgerHeader,
    LedgerError,
    LedgerIntegrityError,
    _compute_record_hash,
)
from runtime.governance.HASH_POLICY_v1 import hash_json


@pytest.fixture
def ledger_path(tmp_path):
    return tmp_path / "ledger.jsonl"


def _mk_record(attempt_id: int = 1, **overrides) -> AttemptRecord:
    """Helper to build a minimal AttemptRecord with sensible defaults."""
    defaults = dict(
        attempt_id=attempt_id,
        timestamp="2026-02-16T00:00:00Z",
        run_id="run_test",
        policy_hash="phash",
        input_hash="ihash",
        actions_taken=["action1"],
        diff_hash="dhash",
        changed_files=["f1.py"],
        evidence_hashes={"e1": "h1"},
        success=True,
        failure_class=None,
        terminal_reason=None,
        next_action="terminate",
        rationale="test",
    )
    defaults.update(overrides)
    return AttemptRecord(**defaults)


# ── Test 1: Header hash is computed and persisted on initialize ──

class TestHeaderHash:
    def test_header_hash_computed_on_initialize(self, ledger_path):
        ledger = AttemptLedger(ledger_path)
        header = LedgerHeader(policy_hash="abc", handoff_hash="123", run_id="run1")
        ledger.initialize(header)

        with open(ledger_path) as f:
            data = json.loads(f.readline())

        assert data["schema_version"] == "v1.1"
        assert "header_hash" in data
        assert len(data["header_hash"]) == 64  # SHA-256 hex

        # Verify deterministic
        expected = hash_json({
            "type": "header",
            "schema_version": "v1.1",
            "policy_hash": "abc",
            "handoff_hash": "123",
            "run_id": "run1",
        })
        assert data["header_hash"] == expected

    def test_header_hash_deterministic(self):
        h1 = LedgerHeader(policy_hash="x", handoff_hash="y", run_id="r")
        h2 = LedgerHeader(policy_hash="x", handoff_hash="y", run_id="r")
        assert h1.header_hash == h2.header_hash

    def test_header_hash_changes_with_fields(self):
        h1 = LedgerHeader(policy_hash="x", handoff_hash="y", run_id="r1")
        h2 = LedgerHeader(policy_hash="x", handoff_hash="y", run_id="r2")
        assert h1.header_hash != h2.header_hash


# ── Test 2: 3-record append builds correct link chain ──

class TestChainLinking:
    def test_three_record_chain(self, ledger_path):
        ledger = AttemptLedger(ledger_path)
        header = LedgerHeader(policy_hash="p", handoff_hash="h", run_id="r")
        ledger.initialize(header)

        r1 = _mk_record(attempt_id=1)
        r2 = _mk_record(attempt_id=2)
        r3 = _mk_record(attempt_id=3)

        ledger.append(r1)
        ledger.append(r2)
        ledger.append(r3)

        # Record 1 links to header_hash
        assert ledger.history[0].prev_record_hash == header.header_hash
        # Record 2 links to record 1
        assert ledger.history[1].prev_record_hash == ledger.history[0].record_hash
        # Record 3 links to record 2
        assert ledger.history[2].prev_record_hash == ledger.history[1].record_hash

        # All have non-None record_hash
        for rec in ledger.history:
            assert rec.record_hash is not None
            assert len(rec.record_hash) == 64


# ── Test 3: Record hash determinism ──

class TestRecordHashDeterminism:
    def test_same_input_same_hash(self, ledger_path):
        """Same record data and prev_hash produce same record_hash."""
        record = _mk_record()
        d = asdict(record)
        h1 = _compute_record_hash(d, "prev_abc")
        h2 = _compute_record_hash(d, "prev_abc")
        assert h1 == h2

    def test_field_change_changes_hash(self, ledger_path):
        """Changing any field changes the hash."""
        r1 = _mk_record(success=True)
        r2 = _mk_record(success=False)
        h1 = _compute_record_hash(asdict(r1), "prev")
        h2 = _compute_record_hash(asdict(r2), "prev")
        assert h1 != h2

    def test_prev_hash_change_changes_hash(self):
        """Different prev_hash produces different record_hash."""
        record = _mk_record()
        d = asdict(record)
        h1 = _compute_record_hash(d, "prev_A")
        h2 = _compute_record_hash(d, "prev_B")
        assert h1 != h2


# ── Test 4: Tamper record field detected by verify_chain ──

class TestTamperDetection:
    def test_tamper_record_field_detected(self, ledger_path):
        ledger = AttemptLedger(ledger_path)
        header = LedgerHeader(policy_hash="p", handoff_hash="h", run_id="r")
        ledger.initialize(header)
        ledger.append(_mk_record(attempt_id=1))
        ledger.append(_mk_record(attempt_id=2))

        # Tamper with record 1's success field
        ledger.history[0].success = False

        valid, errors = ledger.verify_chain()
        assert valid is False
        assert any("record_hash mismatch" in e for e in errors)


# ── Test 5: Delete middle record detected ──

class TestMiddleDeletion:
    def test_delete_middle_record_detected(self, ledger_path):
        ledger = AttemptLedger(ledger_path)
        header = LedgerHeader(policy_hash="p", handoff_hash="h", run_id="r")
        ledger.initialize(header)
        ledger.append(_mk_record(attempt_id=1))
        ledger.append(_mk_record(attempt_id=2))
        ledger.append(_mk_record(attempt_id=3))

        # Delete middle record
        del ledger.history[1]

        valid, errors = ledger.verify_chain()
        assert valid is False
        assert any("prev_record_hash mismatch" in e for e in errors)


# ── Test 6: Tamper header field detected ──

class TestHeaderTamper:
    def test_tamper_header_field_detected(self, ledger_path):
        ledger = AttemptLedger(ledger_path)
        header = LedgerHeader(policy_hash="p", handoff_hash="h", run_id="r")
        ledger.initialize(header)
        ledger.append(_mk_record(attempt_id=1))

        # Tamper header
        ledger.header["policy_hash"] = "TAMPERED"

        valid, errors = ledger.verify_chain()
        assert valid is False
        assert any("header_hash mismatch" in e for e in errors)


# ── Test 7: v1.1 missing header_hash fails closed on hydrate ──

class TestFailClosedMissingHeaderHash:
    def test_v11_missing_header_hash_fails(self, ledger_path):
        with open(ledger_path, 'w') as f:
            json.dump({
                "type": "header",
                "schema_version": "v1.1",
                "policy_hash": "p",
                "handoff_hash": "h",
                "run_id": "r",
                # header_hash intentionally omitted
            }, f)
            f.write('\n')

        ledger = AttemptLedger(ledger_path)
        with pytest.raises(LedgerIntegrityError, match="missing header_hash"):
            ledger.hydrate()

    def test_v11_invalid_header_hash_fails(self, ledger_path):
        with open(ledger_path, 'w') as f:
            json.dump({
                "type": "header",
                "schema_version": "v1.1",
                "policy_hash": "p",
                "handoff_hash": "h",
                "run_id": "r",
                "header_hash": "bad_hash_value",
            }, f)
            f.write('\n')

        ledger = AttemptLedger(ledger_path)
        with pytest.raises(LedgerIntegrityError, match="header_hash mismatch"):
            ledger.hydrate()

    def test_unknown_schema_version_fails_closed(self, ledger_path):
        """Unknown schema versions fail closed and require header_hash."""
        with open(ledger_path, 'w') as f:
            json.dump({
                "type": "header",
                "schema_version": "legacy_mode",
                "policy_hash": "p",
                "handoff_hash": "h",
                "run_id": "r",
                # header_hash intentionally omitted
            }, f)
            f.write('\n')

        ledger = AttemptLedger(ledger_path)
        with pytest.raises(LedgerIntegrityError, match="missing header_hash"):
            ledger.hydrate()

    def test_schema_version_numeric_comparison_is_not_lexical(self, ledger_path):
        """v1.10 should be treated as chain-required (numeric comparison)."""
        ledger = AttemptLedger(ledger_path)
        header = LedgerHeader(
            policy_hash="p", handoff_hash="h", run_id="r", schema_version="v1.10"
        )
        ledger.initialize(header)

        reloaded = AttemptLedger(ledger_path)
        assert reloaded.hydrate() is True
        assert reloaded._chain_enabled is True

        reloaded.append(_mk_record(attempt_id=1))
        assert reloaded.history[0].record_hash is not None


# ── Test 8 & 9: Tail truncation detection ──

class TestTailTruncation:
    def test_truncated_chain_internally_valid(self, ledger_path):
        """Truncated chain without external expectation is internally valid prefix."""
        ledger = AttemptLedger(ledger_path)
        header = LedgerHeader(policy_hash="p", handoff_hash="h", run_id="r")
        ledger.initialize(header)
        ledger.append(_mk_record(attempt_id=1))
        ledger.append(_mk_record(attempt_id=2))
        ledger.append(_mk_record(attempt_id=3))

        # Record the real tip before truncation
        real_tip = ledger.history[-1].record_hash

        # Truncate last record (simulate tail truncation)
        del ledger.history[-1]

        # Without external expectations, prefix is internally valid
        valid, errors = ledger.verify_chain()
        assert valid is True

    def test_truncation_detected_with_expected_tip(self, ledger_path):
        """Tail truncation detected when expected_tip is provided."""
        ledger = AttemptLedger(ledger_path)
        header = LedgerHeader(policy_hash="p", handoff_hash="h", run_id="r")
        ledger.initialize(header)
        ledger.append(_mk_record(attempt_id=1))
        ledger.append(_mk_record(attempt_id=2))
        ledger.append(_mk_record(attempt_id=3))

        real_tip = ledger.history[-1].record_hash
        real_count = len(ledger.history)

        # Truncate last record
        del ledger.history[-1]

        valid, errors = ledger.verify_chain(
            expected_tip=real_tip, expected_count=real_count
        )
        assert valid is False
        assert any("chain tip mismatch" in e for e in errors)
        assert any("record count mismatch" in e for e in errors)


# ── Test 10: integrity_check returns False for tampered v1.1 ledger ──

class TestIntegrityCheckWithChain:
    def test_integrity_check_false_on_tamper(self, ledger_path):
        ledger = AttemptLedger(ledger_path)
        header = LedgerHeader(policy_hash="p", handoff_hash="h", run_id="r")
        ledger.initialize(header)
        ledger.append(_mk_record(attempt_id=1))

        # Tamper the on-disk record (change success field)
        with open(ledger_path, 'r') as f:
            lines = f.readlines()

        record_data = json.loads(lines[1])
        record_data["success"] = not record_data["success"]

        with open(ledger_path, 'w') as f:
            f.write(lines[0])
            json.dump(record_data, f)
            f.write('\n')

        ledger2 = AttemptLedger(ledger_path)
        assert ledger2.integrity_check() is False

    def test_append_blocked_when_existing_chain_is_corrupt(self, ledger_path):
        ledger = AttemptLedger(ledger_path)
        header = LedgerHeader(policy_hash="p", handoff_hash="h", run_id="r")
        ledger.initialize(header)
        ledger.append(_mk_record(attempt_id=1))

        # Corrupt in-memory chain state.
        ledger.history[0].record_hash = None

        with pytest.raises(LedgerIntegrityError, match="corrupted chain state"):
            ledger.append(_mk_record(attempt_id=2))


# ── Test 11-13: Legacy v1.0 compatibility ──

class TestLegacyV10:
    def test_hydrate_v10_ledger_succeeds(self, ledger_path):
        """v1.0 ledger hydrates without error (no chain validation)."""
        with open(ledger_path, 'w') as f:
            json.dump({
                "type": "header",
                "schema_version": "v1.0",
                "policy_hash": "abc",
                "handoff_hash": "123",
                "run_id": "run1",
            }, f)
            f.write('\n')
            json.dump({
                "attempt_id": 1, "timestamp": "", "run_id": "run1",
                "policy_hash": "abc", "input_hash": "123",
                "actions_taken": [], "diff_hash": None,
                "changed_files": [], "evidence_hashes": {},
                "success": True, "failure_class": None,
                "terminal_reason": None, "next_action": "terminate",
                "rationale": "ok",
            }, f)
            f.write('\n')

        ledger = AttemptLedger(ledger_path)
        assert ledger.hydrate() is True
        assert len(ledger.history) == 1
        assert ledger._chain_enabled is False

    def test_append_blocked_on_v10_ledger(self, ledger_path):
        """Append on hydrated v1.0 ledger raises LedgerError."""
        with open(ledger_path, 'w') as f:
            json.dump({
                "type": "header",
                "schema_version": "v1.0",
                "policy_hash": "abc",
                "handoff_hash": "123",
                "run_id": "run1",
            }, f)
            f.write('\n')

        ledger = AttemptLedger(ledger_path)
        ledger.hydrate()

        with pytest.raises(LedgerError, match="append blocked.*v1.0"):
            ledger.append(_mk_record(attempt_id=1))

    def test_v10_verify_chain_returns_true(self, ledger_path):
        """v1.0 ledger verify_chain returns (True, []) — no chain to verify."""
        with open(ledger_path, 'w') as f:
            json.dump({
                "type": "header",
                "schema_version": "v1.0",
                "policy_hash": "abc",
                "handoff_hash": "123",
                "run_id": "run1",
            }, f)
            f.write('\n')

        ledger = AttemptLedger(ledger_path)
        ledger.hydrate()

        valid, errors = ledger.verify_chain()
        assert valid is True
        assert errors == []

    def test_existing_record_compatible_with_optional_fields(self):
        """AttemptRecord(**data) remains compatible when new fields are absent."""
        data = {
            "attempt_id": 1, "timestamp": "", "run_id": "run1",
            "policy_hash": "abc", "input_hash": "123",
            "actions_taken": [], "diff_hash": None,
            "changed_files": [], "evidence_hashes": {},
            "success": True, "failure_class": None,
            "terminal_reason": None, "next_action": "terminate",
            "rationale": "ok",
        }
        # No prev_record_hash or record_hash — should still construct
        record = AttemptRecord(**data)
        assert record.prev_record_hash is None
        assert record.record_hash is None


# ── get_chain_tip convenience ──

class TestGetChainTip:
    def test_chain_tip_after_appends(self, ledger_path):
        ledger = AttemptLedger(ledger_path)
        header = LedgerHeader(policy_hash="p", handoff_hash="h", run_id="r")
        ledger.initialize(header)

        # Before any records, tip is header_hash
        assert ledger.get_chain_tip() == header.header_hash

        ledger.append(_mk_record(attempt_id=1))
        assert ledger.get_chain_tip() == ledger.history[0].record_hash

        ledger.append(_mk_record(attempt_id=2))
        assert ledger.get_chain_tip() == ledger.history[1].record_hash
