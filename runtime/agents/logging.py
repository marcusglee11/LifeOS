"""
Agent Call Logging - Hash chain logging with tamper-evident integrity.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1.4

This is the CANONICAL logging module per spec. The agent_logging.py file
is a compatibility shim that re-exports from this module.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .api import canonical_json


# Per v0.3 spec §5.1.4 - Hash Chain Genesis
HASH_CHAIN_GENESIS = hashlib.sha256(b"LIFEOS_LOG_CHAIN_GENESIS_V1").hexdigest()


@dataclass
class AgentCallLogEntry:
    """Log entry for an agent call. Per v0.3 spec §5.1.3."""
    
    call_id_deterministic: str
    call_id_audit: str
    timestamp: str
    role: str
    model_requested: str
    model_used: str
    model_version: str
    input_packet_hash: str
    prompt_hash: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    output_packet_hash: str
    status: str  # "success", "error", "timeout", "invalid_response"
    prev_log_hash: str
    entry_hash: str = ""  # Computed after creation


class AgentCallLogger:
    """
    Append-only hash chain logger for agent calls.
    
    Per v0.3 spec §5.1.4 and §5.8 (Evidence Integrity).
    """
    
    def __init__(self, log_dir: str = "logs/agent_calls"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._prev_hash: str = HASH_CHAIN_GENESIS
        self._entries: list[AgentCallLogEntry] = []
    
    def _compute_entry_hash(self, entry: AgentCallLogEntry) -> str:
        """Compute SHA-256 hash of entry including prev_log_hash."""
        entry_dict = asdict(entry)
        entry_dict.pop("entry_hash", None)  # Exclude entry_hash from computation
        content = canonical_json(entry_dict)
        return hashlib.sha256(content).hexdigest()
    
    def log_call(
        self,
        call_id_deterministic: str,
        call_id_audit: str,
        role: str,
        model_requested: str,
        model_used: str,
        model_version: str,
        input_packet_hash: str,
        prompt_hash: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: int,
        output_packet_hash: str,
        status: str,
    ) -> AgentCallLogEntry:
        """
        Log an agent call with hash chain integrity.
        
        Returns the logged entry with computed hashes.
        """
        entry = AgentCallLogEntry(
            call_id_deterministic=call_id_deterministic,
            call_id_audit=call_id_audit,
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=role,
            model_requested=model_requested,
            model_used=model_used,
            model_version=model_version,
            input_packet_hash=input_packet_hash,
            prompt_hash=prompt_hash,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            output_packet_hash=output_packet_hash,
            status=status,
            prev_log_hash=self._prev_hash,
        )
        
        entry.entry_hash = self._compute_entry_hash(entry)
        self._prev_hash = entry.entry_hash
        self._entries.append(entry)
        
        return entry
    
    def verify_chain(self) -> tuple[bool, list[str]]:
        """
        Verify integrity of the log chain.
        
        Returns:
            (is_valid, list_of_breaks)
        """
        breaks = []
        expected_prev = HASH_CHAIN_GENESIS
        
        for i, entry in enumerate(self._entries):
            if entry.prev_log_hash != expected_prev:
                breaks.append(
                    f"Entry {i}: expected prev_log_hash={expected_prev}, "
                    f"got {entry.prev_log_hash}"
                )
            
            computed = self._compute_entry_hash(entry)
            if entry.entry_hash != computed:
                breaks.append(
                    f"Entry {i}: entry_hash mismatch. "
                    f"Stored={entry.entry_hash}, computed={computed}"
                )
            
            expected_prev = entry.entry_hash
        
        return len(breaks) == 0, breaks
    
    @property
    def entries(self) -> list[AgentCallLogEntry]:
        """Return all logged entries."""
        return list(self._entries)
    
    @property
    def prev_hash(self) -> str:
        """Return current chain tip hash."""
        return self._prev_hash
