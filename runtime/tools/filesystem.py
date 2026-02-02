"""
Filesystem Tool Handlers - Secure file operations with containment.

Per Plan_Tool_Invoke_MVP_v0.2:
- Strict containment: realpath comparison
- Symlink defense: reject if any path component is symlink
- Encoding: UTF-8 only, EncodingError on decode failure
- Deterministic list_dir ordering

Fail-Closed Boundary:
All filesystem errors (OSError, UnicodeDecodeError) are wrapped into
ToolErrorType.IO_ERROR or ToolErrorType.ENCODING_ERROR. No OS-level
exceptions propagate to callers.

See: docs/02_protocols/Filesystem_Error_Boundary_Protocol_v1.0.md
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from runtime.tools.schemas import (
    ToolInvokeResult,
    ToolOutput,
    Effects,
    FileEffect,
    ToolError,
    ToolErrorType,
    make_error_result,
    make_success_result,
)


# =============================================================================
# Containment Checking
# =============================================================================

class ContainmentError(Exception):
    """Raised when path escapes sandbox root."""
    pass


def _has_symlink_in_path(path: Path) -> bool:
    """
    Check if any component of path is a symlink.
    
    Includes the path itself and all parent components up to root.
    
    Returns:
        True if any component is a symlink
    """
    if not path.exists():
        # For non-existent paths, check parent components
        parent = path.parent
        if parent.exists():
            return _has_symlink_in_path(parent)
        return False
    
    # Check the path itself
    if path.is_symlink():
        return True
    
    # Check all parent components
    current = path
    checked = set()
    
    while current != current.parent:
        current_str = str(current)
        if current_str in checked:
            break
        checked.add(current_str)
        
        if current.exists() and current.is_symlink():
            return True
        
        current = current.parent
    
    return False


def check_containment(target_path: str, sandbox_root: Path) -> Path:
    """
    Verify path is safely contained within sandbox root.
    
    Steps:
    1. Resolve path relative to sandbox root if not absolute
    2. Canonicalize via realpath
    3. Check containment: target_real starts with root_real + os.sep
    4. Reject if any path component is a symlink
    
    Args:
        target_path: Requested path (absolute or relative)
        sandbox_root: Canonical sandbox root
        
    Returns:
        Canonical Path within sandbox
        
    Raises:
        ContainmentError: If path escapes or contains symlinks
    """
    # Resolve to absolute path
    path = Path(target_path)
    if not path.is_absolute():
        path = sandbox_root / path
    
    # Check for symlinks BEFORE resolving (to catch escape attempts)
    if _has_symlink_in_path(path):
        raise ContainmentError(
            f"Path contains symlink (denied): {target_path}"
        )
    
    # Canonicalize both paths
    root_real = sandbox_root.resolve()
    
    # For non-existent files, we need to resolve the parent and check
    if path.exists():
        target_real = path.resolve()
    else:
        # For new files, resolve parent and append filename
        parent = path.parent
        if parent.exists():
            target_real = parent.resolve() / path.name
        else:
            # Parent doesn't exist either - resolve what we can
            target_real = path.resolve()
    
    # Containment check: target must be under root
    root_str = str(root_real)
    target_str = str(target_real)
    
    # Must start with root + separator (or be equal to root for directories)
    if not (target_str.startswith(root_str + os.sep) or target_str == root_str):
        raise ContainmentError(
            f"Path escapes sandbox root: {target_path} -> {target_real}"
        )
    
    return target_real


def compute_file_hash(content: bytes) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content).hexdigest()


# =============================================================================
# Filesystem Handlers
# =============================================================================

def handle_read_file(args: Dict[str, Any], sandbox_root: Path) -> ToolInvokeResult:
    """
    Handle filesystem.read_file action.
    
    Args:
        args.path: File path to read (relative or absolute)
        
    Returns:
        ToolInvokeResult with file content in output.stdout
        
    Errors:
        NotFound: File does not exist
        EncodingError: File is not valid UTF-8
        ContainmentViolation: Path escapes sandbox
    """
    path_str = args.get("path")
    
    if not path_str:
        return make_error_result(
            tool="filesystem",
            action="read_file",
            error_type=ToolErrorType.SCHEMA_ERROR,
            message="Missing required argument: path",
            policy_allowed=True,
            policy_reason="ALLOWED",
        )
    
    # Containment check
    try:
        target_path = check_containment(path_str, sandbox_root)
    except ContainmentError as e:
        return make_error_result(
            tool="filesystem",
            action="read_file",
            error_type=ToolErrorType.POLICY_DENIED,
            message=str(e),
            policy_allowed=True,
            policy_reason="ALLOWED",
            details={"containment_error": True},
        )
    
    # Check file exists
    if not target_path.exists():
        return make_error_result(
            tool="filesystem",
            action="read_file",
            error_type=ToolErrorType.NOT_FOUND,
            message=f"File not found: {path_str}",
            policy_allowed=True,
            policy_reason="ALLOWED",
        )
    
    if not target_path.is_file():
        return make_error_result(
            tool="filesystem",
            action="read_file",
            error_type=ToolErrorType.IO_ERROR,
            message=f"Path is not a file: {path_str}",
            policy_allowed=True,
            policy_reason="ALLOWED",
        )
    
    # Read and decode
    try:
        content_bytes = target_path.read_bytes()
    except OSError as e:
        return make_error_result(
            tool="filesystem",
            action="read_file",
            error_type=ToolErrorType.IO_ERROR,
            message=f"Failed to read file: {e}",
            policy_allowed=True,
            policy_reason="ALLOWED",
        )
    
    # UTF-8 decode - fail-closed on decode failure
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError as e:
        return make_error_result(
            tool="filesystem",
            action="read_file",
            error_type=ToolErrorType.ENCODING_ERROR,
            message=f"File is not valid UTF-8: {e}",
            policy_allowed=True,
            policy_reason="ALLOWED",
        )
    
    # Build effects record
    file_hash = compute_file_hash(content_bytes)
    effects = Effects(
        files_read=[FileEffect(
            path=str(target_path.relative_to(sandbox_root)),
            size_bytes=len(content_bytes),
            sha256=file_hash,
        )]
    )
    
    return make_success_result(
        tool="filesystem",
        action="read_file",
        output=ToolOutput(stdout=content, stderr="", truncated=False),
        effects=effects,
        matched_rules=["filesystem.read_file"],
    )


def handle_write_file(args: Dict[str, Any], sandbox_root: Path) -> ToolInvokeResult:
    """
    Handle filesystem.write_file action.
    
    Args:
        args.path: File path to write (relative or absolute)
        args.content: Content to write (string, can be empty)
        
    Returns:
        ToolInvokeResult with sha256 and size_bytes in effects
        
    Errors:
        ContainmentViolation: Path escapes sandbox
        IOError: Write failed
    """
    path_str = args.get("path")
    content = args.get("content", "")  # Default to empty string
    
    if not path_str:
        return make_error_result(
            tool="filesystem",
            action="write_file",
            error_type=ToolErrorType.SCHEMA_ERROR,
            message="Missing required argument: path",
            policy_allowed=True,
            policy_reason="ALLOWED",
        )
    
    # Ensure content is a string
    if not isinstance(content, str):
        content = str(content) if content is not None else ""
    
    # Containment check
    try:
        target_path = check_containment(path_str, sandbox_root)
    except ContainmentError as e:
        return make_error_result(
            tool="filesystem",
            action="write_file",
            error_type=ToolErrorType.POLICY_DENIED,
            message=str(e),
            policy_allowed=True,
            policy_reason="ALLOWED",
            details={"containment_error": True},
        )
    
    # Encode to UTF-8
    content_bytes = content.encode("utf-8")
    
    # Create parent directories if needed
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return make_error_result(
            tool="filesystem",
            action="write_file",
            error_type=ToolErrorType.IO_ERROR,
            message=f"Failed to create parent directories: {e}",
            policy_allowed=True,
            policy_reason="ALLOWED",
        )
    
    # Write file
    try:
        target_path.write_bytes(content_bytes)
    except OSError as e:
        return make_error_result(
            tool="filesystem",
            action="write_file",
            error_type=ToolErrorType.IO_ERROR,
            message=f"Failed to write file: {e}",
            policy_allowed=True,
            policy_reason="ALLOWED",
        )
    
    # Build effects record
    file_hash = compute_file_hash(content_bytes)
    effects = Effects(
        files_written=[FileEffect(
            path=str(target_path.relative_to(sandbox_root)),
            size_bytes=len(content_bytes),
            sha256=file_hash,
        )]
    )
    
    return make_success_result(
        tool="filesystem",
        action="write_file",
        output=ToolOutput(stdout="", stderr="", truncated=False),
        effects=effects,
        matched_rules=["filesystem.write_file"],
    )


def handle_list_dir(args: Dict[str, Any], sandbox_root: Path) -> ToolInvokeResult:
    """
    Handle filesystem.list_dir action.
    
    Args:
        args.path: Directory path to list (relative or absolute, defaults to root)
        
    Returns:
        ToolInvokeResult with sorted entries in output.stdout (one per line)
        
    Path format: Relative paths from sandbox root (documented convention).
        
    Errors:
        NotFound: Directory does not exist
        ContainmentViolation: Path escapes sandbox
    """
    path_str = args.get("path", ".")  # Default to sandbox root
    
    # Containment check
    try:
        target_path = check_containment(path_str, sandbox_root)
    except ContainmentError as e:
        return make_error_result(
            tool="filesystem",
            action="list_dir",
            error_type=ToolErrorType.POLICY_DENIED,
            message=str(e),
            policy_allowed=True,
            policy_reason="ALLOWED",
            details={"containment_error": True},
        )
    
    # Check directory exists
    if not target_path.exists():
        return make_error_result(
            tool="filesystem",
            action="list_dir",
            error_type=ToolErrorType.NOT_FOUND,
            message=f"Directory not found: {path_str}",
            policy_allowed=True,
            policy_reason="ALLOWED",
        )
    
    if not target_path.is_dir():
        return make_error_result(
            tool="filesystem",
            action="list_dir",
            error_type=ToolErrorType.IO_ERROR,
            message=f"Path is not a directory: {path_str}",
            policy_allowed=True,
            policy_reason="ALLOWED",
        )
    
    # List entries with deterministic ordering (lexicographic)
    try:
        entries = list(target_path.iterdir())
    except OSError as e:
        return make_error_result(
            tool="filesystem",
            action="list_dir",
            error_type=ToolErrorType.IO_ERROR,
            message=f"Failed to list directory: {e}",
            policy_allowed=True,
            policy_reason="ALLOWED",
        )
    
    # Sort entries lexicographically by name
    entries = sorted(entries, key=lambda p: p.name)
    
    # Format as relative paths from sandbox root (documented convention)
    entry_lines = []
    for entry in entries:
        try:
            rel_path = entry.relative_to(sandbox_root)
            entry_lines.append(str(rel_path).replace("\\", "/"))
        except ValueError:
            # Should not happen due to containment, but fail safely
            entry_lines.append(entry.name)
    
    content = "\n".join(entry_lines)
    
    return make_success_result(
        tool="filesystem",
        action="list_dir",
        output=ToolOutput(stdout=content, stderr="", truncated=False),
        matched_rules=["filesystem.list_dir"],
    )
