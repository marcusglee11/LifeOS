"""
Workspace Root Resolution - Single source of truth for workspace path detection.

This module provides centralized, deterministic workspace root resolution
to eliminate duplicate implementations across the codebase.

Resolution order (fail-soft with clear fallbacks):
1. LIFEOS_WORKSPACE_ROOT environment variable
2. Git repository root (if in a git repo)
3. Current working directory

Per LifeOS governance requirements, symlinks are denied in sandbox paths.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional


# =============================================================================
# Module-level cache (with reset mechanism for testing)
# =============================================================================

_WORKSPACE_ROOT: Optional[Path] = None
_SANDBOX_ROOT: Optional[Path] = None


def clear_workspace_cache() -> None:
    """
    Clear cached workspace and sandbox roots.

    Call this in test fixtures to prevent cache pollution between tests.
    """
    global _WORKSPACE_ROOT, _SANDBOX_ROOT
    _WORKSPACE_ROOT = None
    _SANDBOX_ROOT = None


# =============================================================================
# Workspace Root Resolution
# =============================================================================

def resolve_workspace_root(use_cache: bool = True) -> Path:
    """
    Resolve workspace root deterministically.

    Resolution order:
    1. LIFEOS_WORKSPACE_ROOT environment variable
    2. Git repository root (if in a git repo)
    3. Current working directory

    Args:
        use_cache: If True, return cached value if available. Set to False
                   to force re-resolution.

    Returns:
        Canonical Path to workspace root

    Raises:
        RuntimeError: If root cannot be established (fail-closed)
    """
    global _WORKSPACE_ROOT

    if use_cache and _WORKSPACE_ROOT is not None:
        return _WORKSPACE_ROOT

    # Try environment variable first
    raw = os.environ.get("LIFEOS_WORKSPACE_ROOT")
    if raw:
        path = Path(raw)
        if path.exists() and path.is_dir():
            _WORKSPACE_ROOT = path.resolve()
            return _WORKSPACE_ROOT

    # Try git root
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=Path.cwd()
        )
        if result.returncode == 0:
            git_root = Path(result.stdout.strip())
            if git_root.exists() and git_root.is_dir():
                _WORKSPACE_ROOT = git_root.resolve()
                return _WORKSPACE_ROOT
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    # Fallback to cwd
    cwd = Path.cwd()
    if cwd.exists() and cwd.is_dir():
        _WORKSPACE_ROOT = cwd.resolve()
        return _WORKSPACE_ROOT

    raise RuntimeError("Cannot determine workspace root")


# =============================================================================
# Sandbox Root Resolution
# =============================================================================

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
    checked: set[str] = set()

    while current != current.parent:
        if str(current) in checked:
            break
        checked.add(str(current))

        if current.is_symlink():
            return True

        current = current.parent

    return False


def resolve_sandbox_root(use_cache: bool = True) -> Path:
    """
    Resolve and validate sandbox root.

    Resolution order:
    1. LIFEOS_SANDBOX_ROOT environment variable
    2. Fail-closed if not set or invalid

    Root symlink policy: DENIED.
    If sandbox root is a symlink OR any path component is a symlink,
    raise RuntimeError.

    Args:
        use_cache: If True, return cached value if available.

    Returns:
        Canonical Path to sandbox root

    Raises:
        RuntimeError: If root cannot be established or contains symlinks
    """
    global _SANDBOX_ROOT

    if use_cache and _SANDBOX_ROOT is not None:
        return _SANDBOX_ROOT

    raw = os.environ.get("LIFEOS_SANDBOX_ROOT")

    if not raw:
        raise RuntimeError(
            "LIFEOS_SANDBOX_ROOT environment variable not set"
        )

    raw_path = Path(raw)

    # Check if raw path exists before resolving
    if not raw_path.exists():
        raise RuntimeError(
            f"Sandbox root does not exist: {raw}"
        )

    # Check for symlinks in the path components BEFORE resolving
    # This is the root symlink denial policy
    if _has_symlink_in_path(raw_path):
        raise RuntimeError(
            f"Sandbox root path contains symlink (denied): {raw}"
        )

    # Canonicalize via resolve() which calls realpath
    root = raw_path.resolve()

    # Verify it's a directory
    if not root.is_dir():
        raise RuntimeError(
            f"Sandbox root is not a directory: {root}"
        )

    _SANDBOX_ROOT = root
    return root


# =============================================================================
# Convenience Functions
# =============================================================================

def get_config_dir() -> Path:
    """Get the config directory path (workspace_root / config)."""
    return resolve_workspace_root() / "config"


def get_policy_dir() -> Path:
    """Get the policy config directory path (workspace_root / config / policy)."""
    return resolve_workspace_root() / "config" / "policy"


def get_artifacts_dir() -> Path:
    """Get the artifacts directory path (workspace_root / artifacts)."""
    return resolve_workspace_root() / "artifacts"


def get_docs_dir() -> Path:
    """Get the docs directory path (workspace_root / docs)."""
    return resolve_workspace_root() / "docs"
