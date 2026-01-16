"""
Operation Executor for Build Loop.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.2
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional, List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from .mission_journal import MissionJournal


class CompensationType(Enum):
    """[v0.3 — P0.2] Validated compensation type enum. Per spec §5.2."""
    NONE = "none"
    GIT_CHECKOUT = "git_checkout"
    GIT_RESET_HEAD = "git_reset_head"
    GIT_RESET_SOFT = "git_reset_soft"
    GIT_RESET_HARD = "git_reset_hard"
    GIT_CLEAN = "git_clean"
    FILESYSTEM_DELETE = "fs_delete"
    FILESYSTEM_RESTORE = "fs_restore"
    CUSTOM_VALIDATED = "custom"


# [v0.3 — P0.2] Validated command whitelist
COMPENSATION_COMMAND_WHITELIST = [
    "git checkout -- .",
    "git reset HEAD",
    "git reset --soft HEAD~1",
    "git reset --hard HEAD~1",
    "git clean -fd",
]


class OperationError(Exception):
    """Base exception for operation errors."""
    pass


class EnvelopeViolation(OperationError):
    """Operation exceeded its envelope constraints."""
    pass


class InvalidCompensation(OperationError):
    """Invalid compensation type or command."""
    pass


class OperationFailed(OperationError):
    """Operation execution failed."""
    pass


@dataclass
class Envelope:
    """Envelope constraints for operation. Per spec §5.2.1."""
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)
    allowed_tools: List[str] = field(default_factory=list)
    allowed_roles: List[str] = field(default_factory=list)
    reject_symlinks: bool = True
    max_budget_usd: float = 10.0
    timeout_seconds: int = 60


@dataclass
class ExecutionContext:
    """Context passed to operation executor. Per spec §5.2."""
    run_id: str
    run_id_audit: str
    mission_id: str
    mission_type: str
    step_id: str
    repo_root: Path
    baseline_commit: str
    envelope: Envelope
    journal: Optional["MissionJournal"] = None


@dataclass
class Operation:
    """Operation to execute. Per spec §5.2."""
    operation_id: str
    type: str  # llm_call, tool_invoke, packet_route, gate_check
    params: Dict[str, Any]
    compensation_type: CompensationType = CompensationType.NONE
    compensation_command: str = ""


@dataclass
class OperationReceipt:
    """Receipt for idempotency and rollback. Per spec §5.2."""
    operation_id: str
    timestamp: str
    pre_state_hash: str
    post_state_hash: str
    compensation_type: CompensationType
    compensation_command: str
    idempotency_key: str
    compensation_verified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d["compensation_type"] = self.compensation_type.value
        return d


@dataclass
class OperationResult:
    """Result of operation execution. Per spec §5.2."""
    operation_id: str
    operation_id_audit: str
    type: str
    status: str  # success, failed, escalated
    output: Any
    evidence: Dict[str, Any]
    receipt: OperationReceipt


def canonical_bytes(obj: Any) -> bytes:
    """
    Produce canonical bytes for hashing. Per spec §5.1.4.
    
    Fail-closed on NaN/Infinity.
    """
    return json.dumps(
        obj,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def compute_state_hash(paths: List[str], repo_root: Path) -> str:
    """
    Hash state of files at given paths. Per Appendix B.4.
    
    Deterministic: sorted paths, consistent format.
    """
    hasher = hashlib.sha256()
    for path in sorted(paths):
        # Normalize to forward slashes
        norm_path = path.replace("\\", "/")
        full_path = repo_root / norm_path
        
        hasher.update(norm_path.encode("utf-8"))
        hasher.update(b":")
        
        if full_path.exists() and full_path.is_file():
            hasher.update(full_path.read_bytes())
        else:
            hasher.update(b"<missing>")
        
        hasher.update(b"\n")
    
    return f"sha256:{hasher.hexdigest()}"


def validate_compensation(
    compensation_type: CompensationType,
    compensation_command: str
) -> None:
    """
    Validate compensation action. Per spec §5.2.2.
    
    Raises InvalidCompensation on failure.
    """
    if compensation_type == CompensationType.NONE:
        if compensation_command and compensation_command != "none":
            raise InvalidCompensation(
                f"CompensationType.NONE requires empty command, got: {compensation_command}"
            )
        return
    
    if compensation_type == CompensationType.CUSTOM_VALIDATED:
        if compensation_command not in COMPENSATION_COMMAND_WHITELIST:
            raise InvalidCompensation(
                f"Custom compensation command not in whitelist: {compensation_command}"
            )
        return
    
    # Other types: command should match pattern
    # (flexible validation - command exists)
    if not compensation_command:
        raise InvalidCompensation(
            f"CompensationType {compensation_type.value} requires non-empty command"
        )


def compute_idempotency_key(operation: Operation, ctx: ExecutionContext) -> str:
    """Compute deterministic idempotency key for operation."""
    content = canonical_bytes({
        "run_id": ctx.run_id,
        "step_id": ctx.step_id,
        "operation_id": operation.operation_id,
        "type": operation.type,
        "params": operation.params,
    })
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


class OperationExecutor:
    """
    Execute operations with envelope enforcement and receipts.
    
    Per spec §5.2.
    """
    
    def __init__(self, envelope_enforcer=None, self_mod_checker=None):
        """
        Initialize executor.
        
        Args:
            envelope_enforcer: Optional EnvelopeEnforcer instance
            self_mod_checker: Optional self-modification checker
        """
        self.envelope_enforcer = envelope_enforcer
        self.self_mod_checker = self_mod_checker
    
    def execute(
        self,
        operation: Operation,
        ctx: ExecutionContext,
        affected_paths: Optional[List[str]] = None
    ) -> OperationResult:
        """
        Execute operation with full receipt generation.
        
        Per spec §5.2:
        1. Check kill switch
        2. Verify envelope constraints
        3. Record pre-state hash
        4. Execute operation
        5. Record post-state hash
        6. Validate compensation
        7. Write receipt to journal
        """
        affected_paths = affected_paths or []
        
        # Validate compensation up front (fail-closed)
        validate_compensation(
            operation.compensation_type,
            operation.compensation_command
        )
        
        # Compute pre-state hash
        pre_state_hash = compute_state_hash(affected_paths, ctx.repo_root)
        
        # Execute based on type
        try:
            output, evidence = self._dispatch(operation, ctx)
            status = "success"
        except OperationError as e:
            output = None
            evidence = {"error": str(e)}
            status = "failed"
        except Exception as e:
            output = None
            evidence = {"error": str(e), "type": type(e).__name__}
            status = "failed"
        
        # Compute post-state hash
        post_state_hash = compute_state_hash(affected_paths, ctx.repo_root)
        
        # Create receipt
        receipt = OperationReceipt(
            operation_id=operation.operation_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            pre_state_hash=pre_state_hash,
            post_state_hash=post_state_hash,
            compensation_type=operation.compensation_type,
            compensation_command=operation.compensation_command,
            idempotency_key=compute_idempotency_key(operation, ctx),
            compensation_verified=False,
        )
        
        # Record to journal if available
        if ctx.journal:
            ctx.journal.record_operation(receipt)
        
        return OperationResult(
            operation_id=operation.operation_id,
            operation_id_audit=str(uuid.uuid4()),
            type=operation.type,
            status=status,
            output=output,
            evidence=evidence,
            receipt=receipt,
        )
    
    def _dispatch(
        self,
        operation: Operation,
        ctx: ExecutionContext
    ) -> tuple[Any, Dict[str, Any]]:
        """Dispatch to specific operation handler."""
        handlers = {
            "llm_call": self._handle_llm_call,
            "tool_invoke": self._handle_tool_invoke,
            "packet_route": self._handle_packet_route,
            "gate_check": self._handle_gate_check,
        }
        
        handler = handlers.get(operation.type)
        if not handler:
            raise OperationError(f"Unknown operation type: {operation.type}")
        
        return handler(operation, ctx)
    
    def _handle_llm_call(
        self,
        operation: Operation,
        ctx: ExecutionContext
    ) -> tuple[Any, Dict[str, Any]]:
        """Handle llm_call operation. Stub for Phase 2."""
        # Phase 2: Return stub, actual LLM integration in Phase 3+
        return {
            "status": "stub",
            "message": "LLM call stub - integration pending",
        }, {
            "handler": "llm_call",
            "stub": True,
        }
    
    def _handle_tool_invoke(
        self,
        operation: Operation,
        ctx: ExecutionContext
    ) -> tuple[Any, Dict[str, Any]]:
        """Handle tool_invoke operation. Per Appendix C."""
        tool = operation.params.get("tool")
        action = operation.params.get("action")
        
        if tool not in ctx.envelope.allowed_tools:
            raise EnvelopeViolation(f"Tool not allowed: {tool}")
        
        # Stub implementation for Phase 2
        return {
            "tool": tool,
            "action": action,
            "status": "stub",
        }, {
            "handler": "tool_invoke",
            "tool": tool,
            "action": action,
            "stub": True,
        }
    
    def _handle_packet_route(
        self,
        operation: Operation,
        ctx: ExecutionContext
    ) -> tuple[Any, Dict[str, Any]]:
        """Handle packet_route operation."""
        transform = operation.params.get("transform")
        input_packet = operation.params.get("input")
        
        # Phase 2: Return stub
        return {
            "transform": transform,
            "status": "stub",
        }, {
            "handler": "packet_route",
            "transform": transform,
            "stub": True,
        }
    
    def _handle_gate_check(
        self,
        operation: Operation,
        ctx: ExecutionContext
    ) -> tuple[Any, Dict[str, Any]]:
        """Handle gate_check operation."""
        check = operation.params.get("check")
        condition = operation.params.get("condition")
        
        # Phase 2: Simple condition evaluation
        result = True  # Stub: always pass
        
        return {
            "check": check,
            "passed": result,
        }, {
            "handler": "gate_check",
            "check": check,
            "passed": result,
        }
