"""
Tool Registry - Central dispatch for tool invocations.

Per Plan_Tool_Invoke_MVP_v0.2:
- Maps (tool, action) → handler callable
- Schema validation before policy gate
- Policy gate before dispatch
- Deterministic registration and dispatch order
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

from runtime.tools.schemas import (
    ToolInvokeRequest,
    ToolInvokeResult,
    PolicyDecision,
    ToolOutput,
    Effects,
    ToolError,
    ToolErrorType,
    make_error_result,
    make_timestamp_utc,
)
from runtime.api.governance_api import (
    resolve_sandbox_root,
    check_tool_action_allowed,
    GovernanceUnavailable,
    PolicyDenied,
)


# Type alias for handler functions
HandlerFn = Callable[[Dict[str, Any], Path], ToolInvokeResult]


class ToolRegistry:
    """
    Registry for tool handlers.
    
    Handles schema validation, policy gating, and dispatch.
    """
    
    def __init__(self, sandbox_root: Optional[Path] = None):
        """
        Initialize registry.
        
        Args:
            sandbox_root: Override sandbox root (for testing).
                         If None, resolved from environment.
        """
        self._handlers: Dict[Tuple[str, str], HandlerFn] = {}
        self._sandbox_root = sandbox_root
        self._sandbox_root_resolved = False
        self._sandbox_root_error: Optional[str] = None
    
    def register(self, tool: str, action: str, handler: HandlerFn) -> None:
        """
        Register a handler for a tool/action pair.
        
        Args:
            tool: Tool name
            action: Action name
            handler: Handler function(args, sandbox_root) -> ToolInvokeResult
        """
        self._handlers[(tool, action)] = handler
    
    def _resolve_sandbox_root(self) -> Tuple[Optional[Path], Optional[str]]:
        """
        Resolve sandbox root, caching the result.
        
        Returns:
            Tuple of (root_path, error_message)
            If successful, error_message is None.
            If failed, root_path is None.
        """
        if self._sandbox_root is not None:
            return self._sandbox_root, None
        
        if self._sandbox_root_resolved:
            return self._sandbox_root, self._sandbox_root_error
        
        try:
            self._sandbox_root = resolve_sandbox_root()
            self._sandbox_root_resolved = True
            return self._sandbox_root, None
        except GovernanceUnavailable as e:
            self._sandbox_root_error = str(e)
            self._sandbox_root_resolved = True
            return None, self._sandbox_root_error
    
    def dispatch(self, request: ToolInvokeRequest) -> ToolInvokeResult:
        """
        Dispatch a tool invocation request.
        
        Order of operations:
        1. Schema validation
        2. Sandbox root resolution
        3. Policy gate check
        4. Handler lookup
        5. Handler execution
        
        Returns:
            ToolInvokeResult with appropriate status and fields
        """
        request_id = request.get_request_id()
        
        # 1. Schema validation
        validation = request.validate()
        if not validation.ok:
            return make_error_result(
                tool=request.tool or "",
                action=request.action or "",
                error_type=ToolErrorType.SCHEMA_ERROR,
                message=f"Schema validation failed: {', '.join(validation.errors)}",
                policy_allowed=False,
                policy_reason="DENIED: Schema validation failed",
                request_id=request_id,
                details={"errors": validation.errors},
            )
        
        # 2. Sandbox root resolution
        sandbox_root, root_error = self._resolve_sandbox_root()
        if sandbox_root is None:
            return make_error_result(
                tool=request.tool,
                action=request.action,
                error_type=ToolErrorType.GOVERNANCE_UNAVAILABLE,
                message=root_error or "Sandbox root unavailable",
                policy_allowed=False,
                policy_reason="DENIED: Governance unavailable",
                request_id=request_id,
            )
        
        # 3. Policy gate check
        allowed, policy = check_tool_action_allowed(request)
        if not allowed:
            return make_error_result(
                tool=request.tool,
                action=request.action,
                error_type=ToolErrorType.POLICY_DENIED,
                message=policy.decision_reason,
                policy_allowed=False,
                policy_reason=policy.decision_reason,
                request_id=request_id,
            )
        
        # 4. Handler lookup
        handler_key = (request.tool, request.action)
        handler = self._handlers.get(handler_key)
        
        if handler is None:
            # This should not happen if policy gate is correct, but fail-closed
            return make_error_result(
                tool=request.tool,
                action=request.action,
                error_type=ToolErrorType.POLICY_DENIED,
                message=f"No handler registered for {request.tool}.{request.action}",
                policy_allowed=False,
                policy_reason="DENIED: No handler registered",
                request_id=request_id,
            )
        
        # 5. Handler execution
        try:
            result = handler(request.args, sandbox_root)
            # Ensure request_id is echoed back
            if request_id and result.request_id is None:
                result.request_id = request_id
            return result
        except Exception as e:
            return make_error_result(
                tool=request.tool,
                action=request.action,
                error_type=ToolErrorType.IO_ERROR,
                message=f"Handler execution failed: {str(e)}",
                policy_allowed=True,
                policy_reason="ALLOWED",
                request_id=request_id,
                details={"exception_type": type(e).__name__},
            )
    
    def get_registered_handlers(self) -> list[Tuple[str, str]]:
        """Return list of registered (tool, action) pairs (sorted for determinism)."""
        return sorted(self._handlers.keys())


# =============================================================================
# Global Registry Singleton
# =============================================================================

_global_registry: Optional[ToolRegistry] = None


def get_registry(sandbox_root: Optional[Path] = None) -> ToolRegistry:
    """
    Get or create the global tool registry.
    
    Args:
        sandbox_root: Override sandbox root (for testing)
        
    Returns:
        ToolRegistry instance with builtins registered
    """
    global _global_registry
    
    if _global_registry is None or sandbox_root is not None:
        registry = ToolRegistry(sandbox_root=sandbox_root)
        _register_builtins(registry)
        
        if sandbox_root is None:
            _global_registry = registry
        
        return registry
    
    return _global_registry


def _register_builtins(registry: ToolRegistry) -> None:
    """Register builtin handlers for filesystem and pytest."""
    # Import handlers here to avoid circular imports
    from runtime.tools.filesystem import (
        handle_read_file,
        handle_write_file,
        handle_list_dir,
    )
    from runtime.tools.pytest_runner import handle_pytest_run
    
    # Register filesystem handlers
    registry.register("filesystem", "read_file", handle_read_file)
    registry.register("filesystem", "write_file", handle_write_file)
    registry.register("filesystem", "list_dir", handle_list_dir)
    
    # Register pytest handler
    registry.register("pytest", "run", handle_pytest_run)


def reset_global_registry() -> None:
    """Reset the global registry (for testing)."""
    global _global_registry
    _global_registry = None
