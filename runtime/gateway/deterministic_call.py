"""
FP-4.x CND-1: Deterministic Call Gateway
Central gateway for subprocess and network operations.
All external calls must route through this gateway for determinism.
"""
import json
import hashlib
from typing import Literal, Dict, Any, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

from runtime.util.atomic_write import atomic_write_json


class DeterministicCallError(Exception):
    """Raised when a deterministic call fails validation or execution."""
    pass


@dataclass
class CallSpec:
    """Specification for a deterministic call."""
    kind: Literal["subprocess", "http"]
    target: str
    args: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def compute_hash(self) -> str:
        """Compute deterministic hash of this call spec."""
        canonical = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass
class CallResult:
    """Result of a deterministic call."""
    success: bool
    output: Any
    error: Optional[str]
    call_hash: str


class DeterministicGateway:
    """
    Gateway for deterministic external calls.
    
    All subprocess and network operations must route through
    this gateway to maintain determinism guarantees.
    
    Currently stubbed for Tier-1. Actual execution will be
    added in Tier-2 with full determinism validation.
    """
    
    ALLOWED_KINDS = frozenset(["subprocess", "http"])
    
    def __init__(self, ledger_path: Optional[str] = None):
        """
        Initialize the gateway.
        
        Args:
            ledger_path: Path to write call ledger (for audit).
        """
        self.ledger_path = Path(ledger_path) if ledger_path else None
        self._call_count = 0
    
    def validate_spec(self, spec: CallSpec) -> None:
        """
        Validate a call specification.
        
        Args:
            spec: The call spec to validate.
            
        Raises:
            DeterministicCallError: If spec is invalid.
        """
        if spec.kind not in self.ALLOWED_KINDS:
            raise DeterministicCallError(
                f"Invalid call kind: {spec.kind}. "
                f"Allowed: {self.ALLOWED_KINDS}"
            )
        
        if not spec.target:
            raise DeterministicCallError("Call target cannot be empty")
        
        # Validate args are JSON-serializable (no closures, lambdas)
        try:
            json.dumps(spec.args, sort_keys=True)
        except (TypeError, ValueError) as e:
            raise DeterministicCallError(
                f"Call args must be JSON-serializable: {e}"
            )
    
    def call(self, spec: CallSpec) -> CallResult:
        """
        Execute a deterministic call.
        
        For Tier-1, this is a stub that validates and logs
        but does not execute actual subprocess/network calls.
        
        Args:
            spec: The call specification.
            
        Returns:
            CallResult with stubbed output.
            
        Raises:
            DeterministicCallError: If spec is invalid.
        """
        self.validate_spec(spec)
        
        call_hash = spec.compute_hash()
        self._call_count += 1
        
        # Log to ledger if configured
        if self.ledger_path:
            self._log_call(spec, call_hash)
        
        # Tier-1: Stub execution
        # In Tier-2, this will route to actual deterministic executors
        return CallResult(
            success=True,
            output={"stub": True, "message": "Tier-1 stub - no actual execution"},
            error=None,
            call_hash=call_hash
        )
    
    def _log_call(self, spec: CallSpec, call_hash: str) -> None:
        """Log call to the ledger file."""
        entry = {
            "call_number": self._call_count,
            "call_hash": call_hash,
            "spec": spec.to_dict()
        }
        
        # Append to ledger (load existing + append + write)
        ledger = []
        if self.ledger_path.exists():
            with open(self.ledger_path, 'r') as f:
                ledger = json.load(f)
        
        ledger.append(entry)
        atomic_write_json(self.ledger_path, ledger)


def deterministic_call(
    kind: Literal["subprocess", "http"],
    target: str,
    args: Optional[Dict[str, Any]] = None,
    gateway: Optional[DeterministicGateway] = None
) -> CallResult:
    """
    Convenience function for deterministic calls.
    
    Args:
        kind: Type of call ("subprocess" or "http").
        target: Target command or URL.
        args: Additional arguments.
        gateway: Optional gateway instance (creates new if not provided).
        
    Returns:
        CallResult from the gateway.
    """
    if gateway is None:
        gateway = DeterministicGateway()
    
    spec = CallSpec(kind=kind, target=target, args=args or {})
    return gateway.call(spec)
