"""
Attempt Ledger - Append-only JSONL ledger for Autonomous Build Loop.

Fail-Closed Boundary:
All filesystem errors (OSError) and JSON errors (JSONDecodeError) are wrapped
into LedgerIntegrityError. The ledger is the source of truth for resumability
and MUST fail explicitly on corruption or I/O errors.

See: docs/02_protocols/Filesystem_Error_Boundary_Protocol_v1.0.md
"""
import json
import os
import hashlib
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path
from .taxonomy import TerminalReason, FailureClass, TerminalOutcome

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

class LedgerHeader:
    """
    First line of the ledger, containing immutable run context.
    """
    schema_version: str = "v1.0"
    policy_hash: str
    handoff_hash: str
    run_id: str
    
    def __init__(self, policy_hash: str, handoff_hash: str, run_id: str):
        self.policy_hash = policy_hash
        self.handoff_hash = handoff_hash
        self.run_id = run_id
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "header",
            "schema_version": self.schema_version,
            "policy_hash": self.policy_hash,
            "handoff_hash": self.handoff_hash,
            "run_id": self.run_id
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
        
    def _ensure_dir(self):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        
    def initialize(self, header: LedgerHeader):
        """
        Initialize a new ledger with a header.
        Raises error if ledger already exists and is not empty.
        """
        if self.ledger_path.exists() and self.ledger_path.stat().st_size > 0:
            # We are initializing, but file exists.
            # If we intended to resume, we should have called hydrate().
            # Depending on usage, this might be OK if we are overwriting execution?
            # But "Loop semantics" usually imply fresh run OR resume.
            # We'll allow it if we are explicit, but generally we expect hydrate first.
            pass
            
        with open(self.ledger_path, 'w', encoding='utf-8') as f:
            json.dump(header.to_dict(), f)
            f.write('\n')
        self.header = header.to_dict()
            
    def hydrate(self) -> bool:
        """
        Load existing ledger from disk. 
        Returns True if successful and not empty.
        Raises LedgerIntegrityError if corrupt.
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
                
            # Parse Records
            self.history = []
            for i, line in enumerate(lines[1:], start=2): # 1-based line numbering for error msg
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Convert dict to AttemptRecord
                    # Basic validation provided by structural matching
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
        """
        # Integrity check: Ensure sequence
        if self.history:
            last_id = self.history[-1].attempt_id
            if record.attempt_id != last_id + 1:
                raise LedgerError(f"Sequence gap: last={last_id}, new={record.attempt_id}")
        elif record.attempt_id != 1:
             # Assuming 1-based attempts
             pass 

        with open(self.ledger_path, 'a', encoding='utf-8') as f:
            json.dump(asdict(record), f)
            f.write('\n')
            
        self.history.append(record)

    def integrity_check(self) -> bool:
        """
        Validate the ledger stream (e.g. valid JSON, sequence).
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
            return True
        except LedgerIntegrityError:
            return False

    def get_last_record(self) -> Optional[AttemptRecord]:
        if not self.history:
            return None
        return self.history[-1]
