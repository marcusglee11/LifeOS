"""
Tool Invoke Schemas - Request/Response contracts for tool execution.

Per Plan_Tool_Invoke_MVP_v0.2 and Agent Instruction Block.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import json


# =============================================================================
# Request Schema
# =============================================================================

@dataclass
class ToolInvokeRequest:
    """
    Request schema for tool invocation.
    
    All fields validated before dispatch.
    """
    tool: str
    action: str
    args: Dict[str, Any] = field(default_factory=dict)
    meta: Optional[Dict[str, Any]] = None
    
    def get_request_id(self) -> Optional[str]:
        """Extract request_id from meta if present."""
        if self.meta:
            return self.meta.get("request_id")
        return None
    
    def validate(self) -> "SchemaValidationResult":
        """
        Validate request fields.
        
        Returns validation result with ok=True if valid.
        """
        errors = []
        
        if not self.tool or not isinstance(self.tool, str):
            errors.append("tool must be a non-empty string")
        
        if not self.action or not isinstance(self.action, str):
            errors.append("action must be a non-empty string")
        
        if not isinstance(self.args, dict):
            errors.append("args must be a dictionary")
        
        if self.meta is not None and not isinstance(self.meta, dict):
            errors.append("meta must be a dictionary if provided")
        
        return SchemaValidationResult(
            ok=len(errors) == 0,
            errors=errors
        )


@dataclass
class SchemaValidationResult:
    """Result of schema validation."""
    ok: bool
    errors: List[str] = field(default_factory=list)


# =============================================================================
# Policy Decision
# =============================================================================

@dataclass
class PolicyDecision:
    """
    Policy gate decision.
    
    Per spec: allowed, decision_reason, matched_rules (optional).
    """
    allowed: bool
    decision_reason: str
    matched_rules: Optional[List[str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, omitting None values."""
        result = {
            "allowed": self.allowed,
            "decision_reason": self.decision_reason,
        }
        if self.matched_rules is not None:
            result["matched_rules"] = self.matched_rules
        return result


# =============================================================================
# Effect Records
# =============================================================================

@dataclass
class FileEffect:
    """
    Record of a file operation effect.
    
    Per spec: size_bytes (int, not bytes), sha256 (full, not truncated).
    """
    path: str
    size_bytes: int
    sha256: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass
class ProcessEffect:
    """
    Record of a process execution effect.
    
    Per spec: cmd, exit_code, duration_ms.
    """
    cmd: List[str]
    exit_code: int
    duration_ms: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cmd": self.cmd,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
        }


@dataclass
class Effects:
    """
    Container for all effect records.
    
    Optional sections omitted if empty.
    """
    files_written: Optional[List[FileEffect]] = None
    files_read: Optional[List[FileEffect]] = None
    process: Optional[ProcessEffect] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {}
        if self.files_written:
            result["files_written"] = [f.to_dict() for f in self.files_written]
        if self.files_read:
            result["files_read"] = [f.to_dict() for f in self.files_read]
        if self.process:
            result["process"] = self.process.to_dict()
        return result


# =============================================================================
# Output Capture
# =============================================================================

# Output cap: 64KB combined stdout+stderr
OUTPUT_CAP_BYTES = 65536

@dataclass
class ToolOutput:
    """
    Captured output from tool execution.
    
    Per spec: stdout, stderr, truncated.
    Truncation semantics: stdout filled first, then stderr with remaining budget.
    """
    stdout: str
    stderr: str
    truncated: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "truncated": self.truncated,
        }


def truncate_output(stdout: str, stderr: str, cap: int = OUTPUT_CAP_BYTES) -> ToolOutput:
    """
    Deterministic truncation of output.
    
    Allocation rule: stdout filled first, then stderr with remaining budget.
    This is deterministic and documented per spec.
    
    Args:
        stdout: Raw stdout content
        stderr: Raw stderr content
        cap: Maximum combined bytes (default 64KB)
    
    Returns:
        ToolOutput with truncated flag set appropriately
    """
    stdout_bytes = stdout.encode("utf-8", errors="replace")
    stderr_bytes = stderr.encode("utf-8", errors="replace")
    
    total_size = len(stdout_bytes) + len(stderr_bytes)
    
    if total_size <= cap:
        return ToolOutput(stdout=stdout, stderr=stderr, truncated=False)
    
    # Deterministic allocation: stdout first, stderr with remainder
    stdout_budget = min(len(stdout_bytes), cap)
    stderr_budget = cap - stdout_budget
    
    truncated_stdout = stdout_bytes[:stdout_budget].decode("utf-8", errors="replace")
    truncated_stderr = stderr_bytes[:stderr_budget].decode("utf-8", errors="replace")
    
    return ToolOutput(stdout=truncated_stdout, stderr=truncated_stderr, truncated=True)


# =============================================================================
# Error Types
# =============================================================================

class ToolErrorType:
    """Canonical error type constants."""
    POLICY_DENIED = "PolicyDenied"
    GOVERNANCE_UNAVAILABLE = "GovernanceUnavailable"
    SCHEMA_ERROR = "SchemaError"
    NOT_FOUND = "NotFound"
    ENCODING_ERROR = "EncodingError"
    IO_ERROR = "IOError"
    TIMEOUT = "Timeout"
    CONTAINMENT_VIOLATION = "ContainmentViolation"


@dataclass
class ToolError:
    """
    Error record for failed tool invocations.
    
    Per spec: type, message, details (optional/bounded).
    """
    type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "type": self.type,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


# =============================================================================
# Result Schema
# =============================================================================

@dataclass
class ToolInvokeResult:
    """
    Result schema for tool invocation.
    
    Per spec: ALL required fields must exist when applicable.
    - ok: bool (always present)
    - tool, action: str (always present)
    - timestamp_utc: str ISO 8601 (always present)
    - policy: PolicyDecision (always present)
    - output: ToolOutput (always present)
    - effects: Effects (optional, present when side effects occurred)
    - error: ToolError (only if ok=false)
    - request_id: str (echoed back if present in request)
    """
    ok: bool
    tool: str
    action: str
    timestamp_utc: str
    policy: PolicyDecision
    output: ToolOutput
    effects: Optional[Effects] = None
    error: Optional[ToolError] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        result = {
            "ok": self.ok,
            "tool": self.tool,
            "action": self.action,
            "timestamp_utc": self.timestamp_utc,
            "policy": self.policy.to_dict(),
            "output": self.output.to_dict(),
        }
        
        if self.request_id is not None:
            result["request_id"] = self.request_id
        
        if self.effects is not None:
            effects_dict = self.effects.to_dict()
            if effects_dict:  # Only include if non-empty
                result["effects"] = effects_dict
        
        if self.error is not None:
            result["error"] = self.error.to_dict()
        
        return result
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON."""
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)


def make_timestamp_utc() -> str:
    """Generate ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def make_error_result(
    tool: str,
    action: str,
    error_type: str,
    message: str,
    policy_allowed: bool = False,
    policy_reason: str = "",
    request_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> ToolInvokeResult:
    """
    Factory for error results.
    
    Ensures all required fields are present.
    """
    return ToolInvokeResult(
        ok=False,
        tool=tool,
        action=action,
        timestamp_utc=make_timestamp_utc(),
        policy=PolicyDecision(
            allowed=policy_allowed,
            decision_reason=policy_reason or error_type,
        ),
        output=ToolOutput(stdout="", stderr="", truncated=False),
        error=ToolError(type=error_type, message=message, details=details),
        request_id=request_id,
    )


def make_success_result(
    tool: str,
    action: str,
    output: ToolOutput,
    effects: Optional[Effects] = None,
    policy_reason: str = "ALLOWED",
    matched_rules: Optional[List[str]] = None,
    request_id: Optional[str] = None,
) -> ToolInvokeResult:
    """
    Factory for success results.
    
    Ensures all required fields are present.
    """
    return ToolInvokeResult(
        ok=True,
        tool=tool,
        action=action,
        timestamp_utc=make_timestamp_utc(),
        policy=PolicyDecision(
            allowed=True,
            decision_reason=policy_reason,
            matched_rules=matched_rules,
        ),
        output=output,
        effects=effects,
        request_id=request_id,
    )
