"""
Pytest Runner Tool Handler - Execute pytest with safety controls.

Per Plan_Tool_Invoke_MVP_v0.2:
- Timeout enforcement (configurable, default 300s, tests use 5s)
- Output capture with 64KB combined cap
- Deterministic truncation: stdout first, then stderr
- Minimal structured output: cmd, exit_code, duration_ms, stdout, stderr, truncated
- NO parsing of test counts from stdout
"""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.tools.schemas import (
    ToolInvokeResult,
    ToolOutput,
    Effects,
    ProcessEffect,
    ToolError,
    ToolErrorType,
    OUTPUT_CAP_BYTES,
    truncate_output,
    make_error_result,
    make_success_result,
    make_timestamp_utc,
)


# =============================================================================
# Constants
# =============================================================================

DEFAULT_TIMEOUT_SECONDS = 300
TEST_TIMEOUT_SECONDS = 5  # Short timeout for tests


# =============================================================================
# Pytest Handler
# =============================================================================

def handle_pytest_run(args: Dict[str, Any], sandbox_root: Path) -> ToolInvokeResult:
    """
    Handle pytest.run action.
    
    Args:
        args.args: List of pytest arguments (optional)
        args.timeout: Timeout in seconds (optional, default 300)
        
    Returns:
        ToolInvokeResult with minimal structured output:
        - cmd: list[str]
        - exit_code: int
        - duration_ms: int
        - stdout: str
        - stderr: str
        - truncated: bool
        
    Truncation semantics (deterministic):
        - Combined cap: 64KB
        - Allocation: stdout filled first, then stderr with remainder
        
    Errors:
        Timeout: Process exceeded timeout
        IOError: Process execution failed
    """
    pytest_args = args.get("args", [])
    timeout = args.get("timeout", DEFAULT_TIMEOUT_SECONDS)
    
    # Validate args
    if not isinstance(pytest_args, list):
        return make_error_result(
            tool="pytest",
            action="run",
            error_type=ToolErrorType.SCHEMA_ERROR,
            message="args must be a list of strings",
            policy_allowed=True,
            policy_reason="ALLOWED",
        )
    
    import sys
    
    # Ensure all args are strings
    pytest_args = [str(arg) for arg in pytest_args]
    
    # Build command
    cmd = [sys.executable, "-m", "pytest"] + pytest_args
    
    # Execute pytest
    start_time = time.monotonic()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(sandbox_root),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        
        duration_ms = int((time.monotonic() - start_time) * 1000)
        
        # Apply deterministic truncation
        output = truncate_output(result.stdout, result.stderr, OUTPUT_CAP_BYTES)
        
        # Build process effect
        effects = Effects(
            process=ProcessEffect(
                cmd=cmd,
                exit_code=result.returncode,
                duration_ms=duration_ms,
            )
        )
        
        return make_success_result(
            tool="pytest",
            action="run",
            output=output,
            effects=effects,
            matched_rules=["pytest.run"],
        )
        
    except subprocess.TimeoutExpired as e:
        duration_ms = int((time.monotonic() - start_time) * 1000)
        
        # Capture partial output if available
        stdout = e.stdout or "" if hasattr(e, 'stdout') else ""
        stderr = e.stderr or "" if hasattr(e, 'stderr') else ""
        
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        
        output = truncate_output(stdout, stderr, OUTPUT_CAP_BYTES)
        
        # Build process effect for timeout
        effects = Effects(
            process=ProcessEffect(
                cmd=cmd,
                exit_code=-1,  # Indicate timeout
                duration_ms=duration_ms,
            )
        )
        
        return make_error_result(
            tool="pytest",
            action="run",
            error_type=ToolErrorType.TIMEOUT,
            message=f"Pytest execution timed out after {timeout}s",
            policy_allowed=True,
            policy_reason="ALLOWED",
            details={
                "cmd": cmd,
                "timeout_seconds": timeout,
                "duration_ms": duration_ms,
            },
        )
        
    except FileNotFoundError as e:
        return make_error_result(
            tool="pytest",
            action="run",
            error_type=ToolErrorType.IO_ERROR,
            message=f"Python/pytest not found: {e}",
            policy_allowed=True,
            policy_reason="ALLOWED",
            details={"cmd": cmd},
        )
        
    except Exception as e:
        return make_error_result(
            tool="pytest",
            action="run",
            error_type=ToolErrorType.IO_ERROR,
            message=f"Pytest execution failed: {str(e)}",
            policy_allowed=True,
            policy_reason="ALLOWED",
            details={"cmd": cmd, "exception_type": type(e).__name__},
        )
