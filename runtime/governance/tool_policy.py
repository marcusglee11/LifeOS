"""
Tool Policy Gate - Governance enforcement for tool invocation.

v1.2.1: Now includes path_scope enforcement per P0.6 requirements.
- Hardcoded allowlist for MVP (with config-driven override support)
- Sandbox/Workspace root resolution with fail-closed semantics
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
# Scope Root Resolution
# =============================================================================

_WORKSPACE_ROOT: Optional[Path] = None
_SANDBOX_ROOT: Optional[Path] = None


def resolve_workspace_root() -> Path:
    """
    Resolve workspace root deterministically.
    
    Resolution order:
    1. LIFEOS_WORKSPACE_ROOT environment variable
    2. Git repository root (if in a git repo)
    3. Current working directory
    
    Returns:
        Canonical Path to workspace root
        
    Raises:
        GovernanceUnavailable: If root cannot be established
    """
    global _WORKSPACE_ROOT
    if _WORKSPACE_ROOT is not None:
        return _WORKSPACE_ROOT
    
    # Try environment variable first
    raw = os.environ.get("LIFEOS_WORKSPACE_ROOT")
    if raw:
        root = Path(raw)
        if root.exists() and root.is_dir():
            if not _has_symlink_in_path(root):
                _WORKSPACE_ROOT = root.resolve()
                return _WORKSPACE_ROOT
    
    # Try git root
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_root = Path(result.stdout.strip())
            if git_root.exists() and git_root.is_dir():
                if not _has_symlink_in_path(git_root):
                    _WORKSPACE_ROOT = git_root.resolve()
                    return _WORKSPACE_ROOT
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass
    
    # Fallback to cwd
    cwd = Path.cwd()
    if cwd.exists() and cwd.is_dir():
        _WORKSPACE_ROOT = cwd.resolve()
        return _WORKSPACE_ROOT
    
    raise GovernanceUnavailable("Cannot determine workspace root")


def resolve_sandbox_root() -> Path:
    """
    Resolve and validate sandbox root.
    
    Resolution order:
    1. LIFEOS_SANDBOX_ROOT environment variable
    2. Fail-closed if not set or invalid
    
    Root symlink policy: DENIED.
    If sandbox root is a symlink OR any path component is a symlink,
    raise GovernanceUnavailable.
    
    Returns:
        Canonical Path to sandbox root
        
    Raises:
        GovernanceUnavailable: If root cannot be established
    """
    global _SANDBOX_ROOT
    if _SANDBOX_ROOT is not None:
        return _SANDBOX_ROOT
    
    raw = os.environ.get("LIFEOS_SANDBOX_ROOT")
    
    if not raw:
        raise GovernanceUnavailable(
            "LIFEOS_SANDBOX_ROOT environment variable not set"
        )
    
    raw_path = Path(raw)
    
    # Check if raw path exists before resolving
    if not raw_path.exists():
        raise GovernanceUnavailable(
            f"Sandbox root does not exist: {raw}"
        )
    
    # Check for symlinks in the path components BEFORE resolving
    # This is the root symlink denial policy
    if _has_symlink_in_path(raw_path):
        raise GovernanceUnavailable(
            f"Sandbox root path contains symlink (denied): {raw}"
        )
    
    # Canonicalize via resolve() which calls realpath
    root = raw_path.resolve()
    
    # Verify it's a directory
    if not root.is_dir():
        raise GovernanceUnavailable(
            f"Sandbox root is not a directory: {root}"
        )
    
    _SANDBOX_ROOT = root
    return root


def _has_symlink_in_path(path: Path) -> bool:
    """
    Check if any component of path is a symlink.
    
    Includes the path itself and all parent components.
    
    Returns:
        True if any component is a symlink
    """
    # Check the path itself
    if path.is_symlink():
        return True
    
    # Check all parent components
    current = path
    checked = set()
    
    while current != current.parent:
        if str(current) in checked:
            break
        checked.add(str(current))
        
        if current.is_symlink():
            return True
        
        current = current.parent
    
    return False


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
        path: Optional path for filesystem operations
        config_rules: Optional config-driven rules (if None, uses hardcoded)
        
    Returns:
        Tuple of (allowed, PolicyDecision)
    """
    tool = request.tool
    action = request.action
    
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
