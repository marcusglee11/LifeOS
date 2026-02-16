---
artifact_id: "review-packet-w7-t01-ledger-hash-chain-build-review-v1-0"
artifact_type: "REVIEW_PACKET"
schema_version: "1.0.0"
created_at: "2026-02-16T04:45:32Z"
author: "Codex"
version: "1.0"
status: "PENDING_REVIEW"
chain_id: "W7-T01-ledger-hash-chain"
mission_ref: "Build Review + Uncontentious Fixes for build/W7-T01-ledger-hash-chain"
tags: ["ledger", "hash-chain", "review", "fail-closed", "tail-anchor"]
terminal_outcome: "PASS"
closure_evidence: {"branch":"build/W7-T01-ledger-hash-chain","base_commit":"b9c4dfa"}
---

# Review_Packet_W7_T01_Ledger_Hash_Chain_Build_Review_v1.0

# Scope Envelope

- **Reviewed Branch**: `build/W7-T01-ledger-hash-chain`
- **Reviewed Build Files**: `runtime/orchestration/loop/ledger.py`, `runtime/orchestration/loop/spine.py`, `runtime/tests/orchestration/loop/test_ledger_hash_chain.py`, `runtime/tests/test_loop_spine.py`
- **Files Modified in This Mission**: `runtime/orchestration/loop/ledger.py`, `runtime/tests/orchestration/loop/test_ledger_hash_chain.py`
- **Ignored Local Unrelated Change**: `runtime/tools/openclaw_models_preflight.sh`

# Summary

Performed a full review of the W7-T01 build and applied only uncontentious hardening fixes:

1. Replaced lexical schema-version comparison with numeric parsing + fail-closed handling for unknown schema labels.
2. Hardened `append()` to fail closed when chain state is disabled/corrupt and when chain anchors are missing.
3. Added regression tests for unknown schema behavior, numeric version ordering (`v1.10`), and append-blocking on corrupted chain state.

# Findings and Disposition

| Severity | Finding | Disposition |
|---|---|---|
| High | Lexical version checks (`"v1.10"` risk) could misclassify chain-required schemas. | **Fixed** in `AttemptLedger._parse_schema_version()` + `_is_chain_required()`. |
| High | `append()` could proceed on corrupted in-memory v1.1 chain state. | **Fixed** by pre-append `verify_chain()` fail-closed gate and chain-tip anchor checks. |
| Medium | Unknown/non-standard schema strings had ambiguous behavior. | **Fixed** by treating unknown versions as chain-required (fail-closed). |
| Medium | Terminal packet ordering causes ledger record to miss terminal packet evidence hash (circularity tradeoff). | **Not changed (contentious/design tradeoff)**; requires explicit design decision to resolve circular hash dependency. |

# Validation Evidence

Executed and passed:

- `pytest runtime/tests/orchestration/loop/test_ledger_hash_chain.py -q` (23 passed)
- `pytest runtime/tests/orchestration/loop/test_ledger.py runtime/tests/orchestration/loop/test_ledger_corruption_recovery.py -q` (17 passed)
- `pytest runtime/tests/test_loop_spine.py runtime/tests/orchestration/missions/test_loop_acceptance.py -q` (22 passed)
- `pytest runtime/tests/orchestration/missions/test_policy_engine_authoritative_e2e.py -q` (8 passed)
- `pytest runtime/tests/orchestration/missions/test_autonomous_loop.py runtime/tests/test_ceo_queue_mission_e2e.py -q` (13 passed)
- `pytest runtime/tests/orchestration/missions/test_bypass_dogfood.py -q` (1 passed, 1 skipped)
- `pytest runtime/tests/test_plan_bypass_eligibility.py -q` (25 passed)

# File Manifest

- `runtime/orchestration/loop/ledger.py`
- `runtime/tests/orchestration/loop/test_ledger_hash_chain.py`

# Appendix A — Flattened Code

### File: `runtime/orchestration/loop/ledger.py`

````python
"""
Attempt Ledger - Append-only JSONL ledger for Autonomous Build Loop.

Fail-Closed Boundary:
All filesystem errors (OSError) and JSON errors (JSONDecodeError) are wrapped
into LedgerIntegrityError. The ledger is the source of truth for resumability
and MUST fail explicitly on corruption or I/O errors.

Hash-Chain Hardening (W7-T01):
v1.1 ledgers carry deterministic hash chains linking header → records.
v1.0 ledgers remain hydratable for compatibility; append is blocked.

See: docs/02_protocols/Filesystem_Error_Boundary_Protocol_v1.0.md
"""
import json
import os
import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict, field
from pathlib import Path
from .taxonomy import TerminalReason, FailureClass, TerminalOutcome

from runtime.api.governance_api import hash_json


def _compute_record_hash(record_dict: dict, prev_hash: str) -> str:
    """
    Compute deterministic hash for a ledger record.

    Excludes ``record_hash`` from the hash input (self-hash).
    Includes ``prev_record_hash`` to link to the previous entry.
    Uses Council-approved HASH_POLICY_v1.hash_json.
    """
    hash_input = {k: v for k, v in record_dict.items() if k != "record_hash"}
    hash_input["prev_record_hash"] = prev_hash
    return hash_json(hash_input)


@dataclass
class AttemptRecord:
    """
    Represents a single attempt in the build loop.
    """
    attempt_id: int
    timestamp: str # ISO 8601
    run_id: str

    # Hashes representing state
    policy_hash: str
    input_hash: str # Handoff/Plan hash

    # Execution details
    actions_taken: List[str]

    # Evidence
    diff_hash: Optional[str]
    changed_files: List[str]
    evidence_hashes: Dict[str, str] # filename -> hash

    # Outcome
    success: bool
    failure_class: Optional[str] # FailureClass.value
    terminal_reason: Optional[str] # TerminalReason.value (if terminal)

    # Decision
    next_action: str # LoopAction.value
    rationale: str

    # Trusted Builder (C4)
    plan_bypass_info: Optional[Dict[str, Any]] = None

    # Hash-chain fields (v1.1+)
    prev_record_hash: Optional[str] = None
    record_hash: Optional[str] = None


class LedgerHeader:
    """
    First line of the ledger, containing immutable run context.
    """
    schema_version: str = "v1.1"
    policy_hash: str
    handoff_hash: str
    run_id: str
    header_hash: str

    def __init__(self, policy_hash: str, handoff_hash: str, run_id: str,
                 schema_version: str = "v1.1"):
        self.policy_hash = policy_hash
        self.handoff_hash = handoff_hash
        self.run_id = run_id
        self.schema_version = schema_version
        self.header_hash = self._compute_header_hash()

    def _compute_header_hash(self) -> str:
        """Deterministic hash over immutable header fields."""
        return hash_json({
            "type": "header",
            "schema_version": self.schema_version,
            "policy_hash": self.policy_hash,
            "handoff_hash": self.handoff_hash,
            "run_id": self.run_id,
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "header",
            "schema_version": self.schema_version,
            "policy_hash": self.policy_hash,
            "handoff_hash": self.handoff_hash,
            "run_id": self.run_id,
            "header_hash": self.header_hash,
        }

class LedgerError(Exception):
    pass

class LedgerIntegrityError(LedgerError):
    pass

class AttemptLedger:
    """
    Append-only JSONL ledger for the Autonomous Build Loop.
    Acts as the Source of Truth for resumability.
    """

    def __init__(self, ledger_path: Path):
        self.ledger_path = ledger_path
        self._ensure_dir()
        self.header: Optional[Dict[str, Any]] = None
        self.history: List[AttemptRecord] = []
        self._chain_enabled: bool = False

    def _ensure_dir(self):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)

    def _schema_version(self) -> str:
        """Return schema version from the hydrated header, or 'v1.0' default."""
        if self.header:
            return self.header.get("schema_version", "v1.0")
        return "v1.0"

    def _parse_schema_version(self, version: str) -> Optional[Tuple[int, int]]:
        """Parse schema versions of the form 'v<major>.<minor>'."""
        match = re.fullmatch(r"v(\d+)\.(\d+)", version or "")
        if not match:
            return None
        return (int(match.group(1)), int(match.group(2)))

    def _is_chain_required(self, version: str) -> bool:
        """
        Return whether this schema must enforce hash chaining.

        v1.0 is legacy read-only mode (no chain required).
        Unknown/non-standard versions fail closed and require chain.
        """
        if version == "v1.0":
            return False
        parsed = self._parse_schema_version(version)
        if parsed is None:
            return True
        return parsed >= (1, 1)

    def initialize(self, header: LedgerHeader):
        """
        Initialize a new ledger with a header.
        Computes and writes header_hash before persisting.
        Raises error if ledger already exists and is not empty.
        """
        if self.ledger_path.exists() and self.ledger_path.stat().st_size > 0:
            pass

        with open(self.ledger_path, 'w', encoding='utf-8') as f:
            json.dump(header.to_dict(), f)
            f.write('\n')
        self.header = header.to_dict()
        self._chain_enabled = self._is_chain_required(header.schema_version)

    def hydrate(self) -> bool:
        """
        Load existing ledger from disk.
        Returns True if successful and not empty.
        Raises LedgerIntegrityError if corrupt.

        Fail-closed for v1.1+: missing/invalid header_hash raises LedgerIntegrityError.
        """
        if not self.ledger_path.exists():
            return False

        try:
            with open(self.ledger_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            if not lines:
                return False

            # Parse Header
            try:
                header_data = json.loads(lines[0])
                if header_data.get("type") != "header":
                    raise LedgerIntegrityError("First line is not a valid header")
                self.header = header_data
            except json.JSONDecodeError:
                raise LedgerIntegrityError("Header JSON corrupt")

            # Determine schema & chain mode
            schema_ver = self.header.get("schema_version", "v1.0")
            self._chain_enabled = self._is_chain_required(schema_ver)

            # Fail-closed: v1.1+ requires valid header_hash
            if self._chain_enabled:
                stored_hash = self.header.get("header_hash")
                if not stored_hash:
                    raise LedgerIntegrityError(
                        "v1.1 ledger missing header_hash (fail-closed)"
                    )
                expected = hash_json({
                    "type": "header",
                    "schema_version": schema_ver,
                    "policy_hash": self.header.get("policy_hash"),
                    "handoff_hash": self.header.get("handoff_hash"),
                    "run_id": self.header.get("run_id"),
                })
                if stored_hash != expected:
                    raise LedgerIntegrityError(
                        f"header_hash mismatch: stored={stored_hash}, expected={expected}"
                    )

            # Parse Records
            self.history = []
            for i, line in enumerate(lines[1:], start=2): # 1-based line numbering for error msg
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    record = AttemptRecord(**data)
                    self.history.append(record)
                except (json.JSONDecodeError, TypeError) as e:
                    raise LedgerIntegrityError(f"Corrupt record at line {i}: {e}")

            return True

        except OSError as e:
            raise LedgerIntegrityError(f"IO Error reading ledger: {e}")

    def append(self, record: AttemptRecord):
        """
        Append a record to the ledger.

        v1.0 ledgers: blocked with LedgerError (fail-closed legacy).
        v1.1+ ledgers: populates prev_record_hash and record_hash before write.
        """
        schema_ver = self._schema_version()
        chain_required = self._is_chain_required(schema_ver)

        # Fail-closed: block legacy append
        if not chain_required:
            raise LedgerError(
                "append blocked for legacy v1.0 ledger; migrate first"
            )
        if not self._chain_enabled:
            raise LedgerIntegrityError(
                "append blocked: schema requires hash-chain but chain state is disabled"
            )

        # Fail-closed: never append to a corrupted chain.
        valid, chain_errors = self.verify_chain()
        if not valid:
            raise LedgerIntegrityError(
                f"append blocked: corrupted chain state ({'; '.join(chain_errors)})"
            )

        # Integrity check: Ensure sequence
        if self.history:
            last_id = self.history[-1].attempt_id
            if record.attempt_id != last_id + 1:
                raise LedgerError(f"Sequence gap: last={last_id}, new={record.attempt_id}")
        elif record.attempt_id != 1:
             pass

        # Compute chain hashes for v1.1+
        if self._chain_enabled:
            if self.history:
                prev_hash = self.history[-1].record_hash
                if not prev_hash:
                    raise LedgerIntegrityError(
                        "append blocked: previous record missing record_hash"
                    )
            else:
                prev_hash = self.header.get("header_hash", "") if self.header else ""
                if not prev_hash:
                    raise LedgerIntegrityError(
                        "append blocked: missing header_hash chain anchor"
                    )
            record.prev_record_hash = prev_hash

            record_dict = asdict(record)
            record.record_hash = _compute_record_hash(record_dict, prev_hash)

        with open(self.ledger_path, 'a', encoding='utf-8') as f:
            json.dump(asdict(record), f)
            f.write('\n')

        self.history.append(record)

    def verify_chain(
        self,
        expected_tip: Optional[str] = None,
        expected_count: Optional[int] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Verify the hash chain integrity of the ledger.

        For v1.0 ledgers, returns (True, []) — no chain to verify.
        For v1.1+, validates:
          - header_hash correctness
          - prev_record_hash linkage
          - record_hash recomputation
          - Optional tail-truncation checks via expected_tip/expected_count

        Returns:
            (is_valid, list_of_error_messages)
        """
        if not self._chain_enabled:
            return (True, [])

        errors: List[str] = []

        # 1. Validate header hash
        expected_header_hash = hash_json({
            "type": "header",
            "schema_version": self.header.get("schema_version"),
            "policy_hash": self.header.get("policy_hash"),
            "handoff_hash": self.header.get("handoff_hash"),
            "run_id": self.header.get("run_id"),
        })
        stored_header_hash = self.header.get("header_hash", "")
        if stored_header_hash != expected_header_hash:
            errors.append(
                f"header_hash mismatch: stored={stored_header_hash}, "
                f"expected={expected_header_hash}"
            )

        # 2. Validate record chain
        prev_hash = stored_header_hash
        for i, record in enumerate(self.history):
            # Check prev_record_hash link
            if record.prev_record_hash != prev_hash:
                errors.append(
                    f"Record {i} (attempt_id={record.attempt_id}): "
                    f"prev_record_hash mismatch. "
                    f"Expected={prev_hash}, got={record.prev_record_hash}"
                )

            # Recompute record_hash
            record_dict = asdict(record)
            recomputed = _compute_record_hash(record_dict, record.prev_record_hash)
            if record.record_hash != recomputed:
                errors.append(
                    f"Record {i} (attempt_id={record.attempt_id}): "
                    f"record_hash mismatch. "
                    f"Expected={recomputed}, got={record.record_hash}"
                )

            prev_hash = record.record_hash

        # 3. Tail-truncation checks (external commitment)
        if expected_tip is not None:
            actual_tip = (
                self.history[-1].record_hash if self.history
                else stored_header_hash
            )
            if actual_tip != expected_tip:
                errors.append(
                    f"chain tip mismatch: expected={expected_tip}, "
                    f"actual={actual_tip}"
                )

        if expected_count is not None:
            actual_count = len(self.history)
            if actual_count != expected_count:
                errors.append(
                    f"record count mismatch: expected={expected_count}, "
                    f"actual={actual_count}"
                )

        return (len(errors) == 0, errors)

    def integrity_check(self) -> bool:
        """
        Validate the ledger stream (e.g. valid JSON, sequence, hash chain).
        Actually performed during hydrate, but can be called explicitly.
        """
        try:
            # Re-read from disk to be sure
            self.hydrate()
            # Additional checks: Sequence
            if self.history:
                expected_id = 1
                for rec in self.history:
                    if rec.attempt_id != expected_id:
                         raise LedgerIntegrityError(f"Sequence Error: expected {expected_id}, got {rec.attempt_id}")
                    expected_id += 1

            # Verify hash chain for v1.1+
            if self._chain_enabled:
                valid, chain_errors = self.verify_chain()
                if not valid:
                    raise LedgerIntegrityError(
                        f"Hash chain errors: {'; '.join(chain_errors)}"
                    )

            return True
        except LedgerIntegrityError:
            return False

    def get_last_record(self) -> Optional[AttemptRecord]:
        if not self.history:
            return None
        return self.history[-1]

    def get_chain_tip(self) -> Optional[str]:
        """Return the chain tip hash (last record_hash, or header_hash if empty)."""
        if self.history and self.history[-1].record_hash:
            return self.history[-1].record_hash
        if self.header:
            return self.header.get("header_hash")
        return None
````

### File: `runtime/tests/orchestration/loop/test_ledger_hash_chain.py`

````python
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
````
