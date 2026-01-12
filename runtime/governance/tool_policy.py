"""
Tool Policy Gate - Governance enforcement for tool invocation.

Per Plan_Tool_Invoke_MVP_v0.2:
- Hardcoded allowlist for MVP
- Sandbox root resolution with fail-closed semantics
- Root symlink denial (REQUIRED CHOICE per instruction block)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple, List

from runtime.tools.schemas import (
    ToolInvokeRequest,
    PolicyDecision,
    ToolErrorType,
)


# =============================================================================
# Hardcoded Allowlist (MVP)
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


# =============================================================================
# Sandbox Root Resolution
# =============================================================================

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
    request: ToolInvokeRequest
) -> Tuple[bool, PolicyDecision]:
    """
    Check if tool/action combination is allowed by policy.
    
    Args:
        request: The tool invocation request
        
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
