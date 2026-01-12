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
            "run_tests": self._handle_run_tests,
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
        """
        Handle llm_call operation.
        
        Wires to runtime.agents.api.call_agent() for actual LLM invocation.
        Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.1
        """
        from runtime.agents.api import call_agent, AgentCall
        
        # Extract params from operation
        role = operation.params.get("role")
        packet = operation.params.get("packet", {})
        model = operation.params.get("model", "auto")
        temperature = operation.params.get("temperature", 0.0)
        max_tokens = operation.params.get("max_tokens", 8192)
        
        if not role:
            raise OperationError("llm_call requires 'role' parameter")
        
        # Check role is allowed by envelope
        if ctx.envelope.allowed_roles and role not in ctx.envelope.allowed_roles:
            raise EnvelopeViolation(f"Role not allowed: {role}")
        
        # Build call
        call = AgentCall(
            role=role,
            packet=packet,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        # Execute call
        response = call_agent(call, run_id=ctx.run_id)
        
        return {
            "call_id": response.call_id,
            "content": response.content,
            "packet": response.packet,
            "model_used": response.model_used,
        }, {
            "handler": "llm_call",
            "model_used": response.model_used,
            "model_version": response.model_version,
            "latency_ms": response.latency_ms,
            "input_tokens": response.usage.get("input_tokens", 0),
            "output_tokens": response.usage.get("output_tokens", 0),
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
        from runtime.orchestration.transforms.base import execute_transform
        
        transform = operation.params.get("transform")
        input_packet = operation.params.get("input")
        
        if not transform:
            raise OperationError("packet_route requires 'transform'")
        if input_packet is None:
            raise OperationError("packet_route requires 'input'")
        
        context = {
            "run_id": ctx.run_id,
            "mission_id": ctx.mission_id,
            "step_id": ctx.step_id,
            "mission_type": ctx.mission_type,
        }
        
        output_packet, evidence = execute_transform(transform, input_packet, context)
        
        return {
            "transform": transform,
            "output": output_packet,
        }, {
            "handler": "packet_route",
            **evidence,
        }
    
    def _handle_gate_check(
        self,
        operation: Operation,
        ctx: ExecutionContext
    ) -> tuple[Any, Dict[str, Any]]:
        """Handle gate_check operation."""
        from runtime.orchestration.validation import gate_check, GateValidationError
        
        schema = operation.params.get("check")
        payload = operation.params.get("condition")
        
        if not schema:
            raise OperationError("gate_check requires 'check' (schema name)")
        if payload is None:
            raise OperationError("gate_check requires 'condition' (payload)")
        
        try:
            gate_check(payload, schema)
            passed = True
            error = None
        except GateValidationError as e:
            passed = False
            error = str(e)
        
        return {
            "check": schema,
            "passed": passed,
            "error": error,
        }, {
            "handler": "gate_check",
            "schema": schema,
            "passed": passed,
            "error": error,
        }
    
    def _handle_run_tests(
        self,
        operation: Operation,
        ctx: ExecutionContext
    ) -> tuple[Any, Dict[str, Any]]:
        """
        Handle run_tests operation.
        
        Executes pytest on specified test paths within envelope constraints.
        Per LifeOS Build Loop Phase 3 requirements.
        
        Params:
            test_paths: List of test file/directory paths (relative to repo_root)
            pytest_args: Optional list of additional pytest arguments
        """
        test_paths = operation.params.get("test_paths", ["tests/"])
        pytest_args = operation.params.get("pytest_args", ["-v", "-q"])
        
        # Validate test_paths are within allowed paths
        for test_path in test_paths:
            # Normalize path for comparison
            norm_path = test_path.replace("\\", "/")
            allowed = False
            for allowed_path in ctx.envelope.allowed_paths:
                allowed_norm = allowed_path.replace("\\", "/")
                if norm_path.startswith(allowed_norm) or allowed_norm.startswith(norm_path):
                    allowed = True
                    break
            
            if not allowed and ctx.envelope.allowed_paths:
                raise EnvelopeViolation(
                    f"Test path '{test_path}' not in allowed paths: {ctx.envelope.allowed_paths}"
                )
        
        # Build pytest command
        cmd = ["python", "-m", "pytest"] + pytest_args + test_paths
        
        # Execute pytest
        try:
            result = subprocess.run(
                cmd,
                cwd=str(ctx.repo_root),
                capture_output=True,
                text=True,
                timeout=ctx.envelope.timeout_seconds,
            )
            
            passed = result.returncode == 0
            
            return {
                "passed": passed,
                "exit_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "test_paths": test_paths,
            }, {
                "handler": "run_tests",
                "passed": passed,
                "exit_code": result.returncode,
                "stdout_lines": len(result.stdout.splitlines()),
                "stderr_lines": len(result.stderr.splitlines()),
            }
        
        except subprocess.TimeoutExpired as e:
            raise OperationFailed(
                f"Test execution timed out after {ctx.envelope.timeout_seconds}s"
            )
        except Exception as e:
            raise OperationFailed(f"Failed to execute tests: {str(e)}")
