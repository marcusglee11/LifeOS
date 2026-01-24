"""
Tool Policy Gate - Governance enforcement for tool invocation.

v1.2.2: Now uses centralized workspace resolution from runtime.util.workspace.
- Hardcoded allowlist for MVP (with config-driven override support)
- Sandbox/Workspace root resolution via centralized utility
- Root symlink denial
- path_scope enforcement for filesystem ALLOW rules
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from runtime.tools.schemas import (
    ToolInvokeRequest,
    PolicyDecision,
    ToolErrorType,
)

# Import centralized workspace utilities
from runtime.util.workspace import (
    resolve_workspace_root as _util_resolve_workspace_root,
    resolve_sandbox_root as _util_resolve_sandbox_root,
    clear_workspace_cache as _util_clear_cache,
    _has_symlink_in_path,
)


# =============================================================================
# Hardcoded Allowlist (MVP fallback)
# =============================================================================

ALLOWED_ACTIONS = {
    "filesystem": ["read_file", "write_file", "list_dir"],
    "pytest": ["run"],
}


# =============================================================================
# Error Types
# =============================================================================

class GovernanceUnavailable(Exception):
    """Raised when governance cannot be established (fail-closed)."""
    pass


class PolicyDenied(Exception):
    """Raised when policy gate denies a request."""
    pass


class PathScopeViolation(Exception):
    """Raised when a path is outside the allowed scope."""
    pass


# =============================================================================
# Scope Root Resolution (delegated to runtime.util.workspace)
# =============================================================================

# Module-level cache references (for backward compatibility)
_WORKSPACE_ROOT: Optional[Path] = None
_SANDBOX_ROOT: Optional[Path] = None


def clear_workspace_cache() -> None:
    """Clear cached workspace and sandbox roots (for testing)."""
    global _WORKSPACE_ROOT, _SANDBOX_ROOT
    _WORKSPACE_ROOT = None
    _SANDBOX_ROOT = None
    _util_clear_cache()


def resolve_workspace_root() -> Path:
    """
    Resolve workspace root deterministically.

    Delegates to runtime.util.workspace for single source of truth.

    Returns:
        Canonical Path to workspace root

    Raises:
        GovernanceUnavailable: If root cannot be established
    """
    global _WORKSPACE_ROOT
    if _WORKSPACE_ROOT is not None:
        return _WORKSPACE_ROOT

    try:
        _WORKSPACE_ROOT = _util_resolve_workspace_root()
        return _WORKSPACE_ROOT
    except RuntimeError as e:
        raise GovernanceUnavailable(str(e))


def resolve_sandbox_root() -> Path:
    """
    Resolve and validate sandbox root.

    Delegates to runtime.util.workspace for single source of truth.

    Returns:
        Canonical Path to sandbox root

    Raises:
        GovernanceUnavailable: If root cannot be established
    """
    global _SANDBOX_ROOT
    if _SANDBOX_ROOT is not None:
        return _SANDBOX_ROOT

    try:
        _SANDBOX_ROOT = _util_resolve_sandbox_root()
        return _SANDBOX_ROOT
    except RuntimeError as e:
        raise GovernanceUnavailable(str(e))


# =============================================================================
# Path Scope Enforcement (P0.6)
# =============================================================================

def check_path_scope(
    target_path: Path,
    scope: str,
    request_path: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Check if a path is within the allowed scope.
    
    Args:
        target_path: The path to check
        scope: "WORKSPACE" or "SANDBOX"
        request_path: Original request path (for error messages)
        
    Returns:
        (allowed, reason) tuple
    """
    try:
        # Normalize the target path
        if not target_path.is_absolute():
            # Resolve relative to workspace
            try:
                workspace = resolve_workspace_root()
                target_path = (workspace / target_path).resolve()
            except GovernanceUnavailable:
                return False, "Cannot resolve workspace root for relative path"
        else:
            target_path = target_path.resolve()
        
        # Check for symlinks in target path
        if _has_symlink_in_path(target_path):
            return False, f"Target path contains symlink (denied): {request_path or target_path}"
        
        # Get scope root
        if scope == "WORKSPACE":
            try:
                scope_root = resolve_workspace_root()
            except GovernanceUnavailable as e:
                return False, f"Cannot resolve workspace root: {e}"
        elif scope == "SANDBOX":
            try:
                scope_root = resolve_sandbox_root()
            except GovernanceUnavailable as e:
                return False, f"Cannot resolve sandbox root: {e}"
        else:
            return False, f"Unknown scope: {scope}"
        
        # Check containment
        try:
            target_path.relative_to(scope_root)
            return True, f"Path within {scope} scope"
        except ValueError:
            return False, f"Path outside {scope} scope: {request_path or target_path}"
            
    except Exception as e:
        return False, f"Path scope check failed: {e}"


# =============================================================================
# Policy Gate
# =============================================================================

def is_tool_allowed(tool: str) -> bool:
    """Check if tool is in the allowlist."""
    return tool in ALLOWED_ACTIONS


def is_action_allowed(tool: str, action: str) -> bool:
    """Check if tool/action combination is in the allowlist."""
    if tool not in ALLOWED_ACTIONS:
        return False
    return action in ALLOWED_ACTIONS[tool]


def check_tool_action_allowed(
    request: ToolInvokeRequest,
    path: Optional[str] = None,
    config_rules: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[bool, PolicyDecision]:
    """
    Check if tool/action combination is allowed by policy.
    
    Args:
        request: The tool invocation request
        path: Optional path for filesystem operations (derived from request.args if not provided)
        config_rules: Optional config-driven rules (if None, uses hardcoded)
        
    Returns:
        Tuple of (allowed, PolicyDecision)
    """
    tool = request.tool
    action = request.action
    
    # P0.3: Derive path from request payload if not explicitly passed
    if path is None and tool == "filesystem":
        path = request.get_path()
    
    # Check tool in allowlist
    if tool not in ALLOWED_ACTIONS:
        return False, PolicyDecision(
            allowed=False,
            decision_reason=f"DENIED: Unknown tool '{tool}'",
            matched_rules=["tool_not_in_allowlist"],
        )
    
    # Check action in allowlist for tool
    if action not in ALLOWED_ACTIONS[tool]:
        return False, PolicyDecision(
            allowed=False,
            decision_reason=f"DENIED: Action '{action}' not allowed for tool '{tool}'",
            matched_rules=["action_not_in_allowlist"],
        )
    
    # P0.4: FAIL-CLOSED if filesystem operation missing path (after derivation)
    if tool == "filesystem" and action in ["read_file", "write_file", "list_dir"]:
        if not path:
            return False, PolicyDecision(
                allowed=False,
                decision_reason=f"DENIED: filesystem.{action} requires path (fail-closed)",
                matched_rules=["filesystem_path_required"],
            )
    
    # P0.6: Enforce path_scope for filesystem operations
    if tool == "filesystem" and path:
        # Default scope for hardcoded rules is WORKSPACE
        scope = "WORKSPACE"
        
        # If config_rules provided, find matching rule and get its scope
        if config_rules:
            for rule in config_rules:
                match = rule.get("match", {})
                if match.get("tool") == tool and match.get("action") == action:
                    scope = rule.get("path_scope", "WORKSPACE")
                    break
        
        # Check path scope
        target_path = Path(path)
        allowed, reason = check_path_scope(target_path, scope, path)
        
        if not allowed:
            return False, PolicyDecision(
                allowed=False,
                decision_reason=f"DENIED: {reason}",
                matched_rules=[f"path_scope_violation:{scope}"],
            )
    
    # Allowed
    return True, PolicyDecision(
        allowed=True,
        decision_reason="ALLOWED",
        matched_rules=[f"{tool}.{action}"],
    )


def get_allowed_tools() -> List[str]:
    """Return list of allowed tools (sorted for determinism)."""
    return sorted(ALLOWED_ACTIONS.keys())


def get_allowed_actions(tool: str) -> List[str]:
    """Return list of allowed actions for a tool (sorted for determinism)."""
    if tool not in ALLOWED_ACTIONS:
        return []
    return sorted(ALLOWED_ACTIONS[tool])
