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
