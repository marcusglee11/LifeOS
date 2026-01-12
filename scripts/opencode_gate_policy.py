#!/usr/bin/env python3
"""
OpenCode Gate Policy (CT-2 Phase 2 v1.3)
=========================================

Centralized policy constants and helpers for the OpenCode doc-steward gate.
No override mechanism. Fail-closed on ambiguity.
"""

import os
import subprocess
import hashlib
from typing import Tuple, List, Optional

# ============================================================================
# EXPLICIT ENUMERATIONS (No Globs)
# ============================================================================

# Index discovery scope (docs only, NOT all allowlist roots)
INDEX_DISCOVERY_SCOPE = ["docs/"]

# Allowlist roots (where steward may write)
ALLOWLIST_ROOTS = [
    "artifacts/review_packets/",
    "docs/",
]

# Denylist roots (terminal BLOCK, evaluated FIRST)
DENYLIST_ROOTS = [
    "config/",
    "docs/00_foundations/",
    "docs/01_governance/",
    "scripts/",
]

# Denylist exact files (case-normalized)
DENYLIST_EXACT_FILES = ["gemini.md"]

# Denylist extensions (blocked everywhere)
DENYLIST_EXTENSIONS = [".py"]

# Extension restrictions under docs/
ALLOWED_EXTENSIONS_DOCS = [".md"]
EXTENSION_EXCEPTIONS = []  # Must remain empty in Phase 2

# Writable index files (docs-scoped, governance excluded)
WRITABLE_INDEX_FILES = ["docs/index.md"]

# Evidence contract
EVIDENCE_ROOT = "artifacts/evidence/opencode_steward_certification/"
LOG_MAX_LINES = 500
LOG_MAX_BYTES = 100000  # 100KB

# ============================================================================
# REASON CODES
# ============================================================================
class ReasonCode:
    # Blocked operations
    PH2_DELETE_BLOCKED = "PH2_DELETE_BLOCKED"
    PH2_RENAME_BLOCKED = "PH2_RENAME_BLOCKED"
    PH2_COPY_BLOCKED = "PH2_COPY_BLOCKED"
    
    # Path security
    PATH_TRAVERSAL_BLOCKED = "PATH_TRAVERSAL_BLOCKED"
    PATH_ABSOLUTE_BLOCKED = "PATH_ABSOLUTE_BLOCKED"
    PATH_ESCAPE_BLOCKED = "PATH_ESCAPE_BLOCKED"
    SYMLINK_BLOCKED = "SYMLINK_BLOCKED"
    SYMLINK_CHECK_FAILED = "SYMLINK_CHECK_FAILED"  # Fail-closed on git ls-files failure
    
    # Denylist
    DENYLIST_ROOT_BLOCKED = "DENYLIST_ROOT_BLOCKED"
    DENYLIST_FILE_BLOCKED = "DENYLIST_FILE_BLOCKED"
    DENYLIST_EXT_BLOCKED = "DENYLIST_EXT_BLOCKED"
    
    # Allowlist
    OUTSIDE_ALLOWLIST_BLOCKED = "OUTSIDE_ALLOWLIST_BLOCKED"
    
    # Extension
    NON_MD_EXTENSION_BLOCKED = "NON_MD_EXTENSION_BLOCKED"
    
    # Review packets
    REVIEW_PACKET_NOT_ADD_ONLY = "REVIEW_PACKET_NOT_ADD_ONLY"
    NON_MD_IN_REVIEW_PACKETS = "NON_MD_IN_REVIEW_PACKETS"
    
    # CI/Diff
    DIFF_COMMAND_FAILED = "DIFF_COMMAND_FAILED"
    DIFF_EXEC_FAILED = "DIFF_EXEC_FAILED"
    REFS_UNAVAILABLE = "REFS_UNAVAILABLE"
    MERGE_BASE_FAILED = "MERGE_BASE_FAILED"
    
    # Index
    INDEX_DISCOVERY_EMPTY = "INDEX_DISCOVERY_EMPTY"
    INDEX_DISCOVERY_AMBIGUOUS = "INDEX_DISCOVERY_AMBIGUOUS"
    
    # Packet
    PACKET_PATHS_MISSING = "PACKET_PATHS_MISSING"

# ============================================================================
# PATH NORMALIZATION
# ============================================================================
def normalize_path(path: str) -> str:
    """Normalize path for policy matching.
    
    - Backslashes → forward slashes
    - Strip leading './'
    - Collapse repeated slashes
    - Lowercase (for matching only)
    """
    norm = path.replace("\\", "/")
    while "//" in norm:
        norm = norm.replace("//", "/")
    if norm.startswith("./"):
        norm = norm[2:]
    return norm.lower()

# ============================================================================
# PATH SECURITY
# ============================================================================
def check_path_security(path: str, repo_root: str) -> Tuple[bool, Optional[str]]:
    """Check path for traversal/absolute attacks.
    
    Returns (safe, reason_code or None).
    """
    norm = normalize_path(path)
    
    # Absolute path check (Unix or Windows)
    if norm.startswith("/"):
        return (False, ReasonCode.PATH_ABSOLUTE_BLOCKED)
    if len(norm) > 1 and norm[1] == ":":
        return (False, ReasonCode.PATH_ABSOLUTE_BLOCKED)
    
    # Traversal check (after normalization)
    if ".." in norm.split("/"):
        return (False, ReasonCode.PATH_TRAVERSAL_BLOCKED)
    
    # Realpath containment (if file exists)
    full_path = os.path.join(repo_root, path)
    if os.path.exists(full_path):
        try:
            real = os.path.realpath(full_path)
            repo_real = os.path.realpath(repo_root)
            if not real.startswith(repo_real):
                return (False, ReasonCode.PATH_ESCAPE_BLOCKED)
        except Exception:
            return (False, ReasonCode.PATH_ESCAPE_BLOCKED)
    
    return (True, None)

# ============================================================================
# SYMLINK DEFENSE
# ============================================================================
def check_symlink_git_index(path: str, repo_root: str) -> Tuple[bool, Optional[str]]:
    """Check if path is a symlink using git ls-files -s (mode 120000).
    
    Primary symlink detection using git index mode.
    Returns (is_symlink, reason_code or None).
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "-s", "--", path],
            capture_output=True, text=True, cwd=repo_root
        )
        # Fail-closed: nonzero return code means we cannot verify, so BLOCK
        if result.returncode != 0:
            return (True, ReasonCode.SYMLINK_CHECK_FAILED)
        if result.stdout.strip():
            # Format: mode SP hash SP stage TAB path
            # Symlink mode is 120000
            mode = result.stdout.strip().split()[0]
            if mode == "120000":
                return (True, ReasonCode.SYMLINK_BLOCKED)
    except Exception:
        # Fail-closed: exception means we cannot verify, so BLOCK
        return (True, ReasonCode.SYMLINK_CHECK_FAILED)
    return (False, None)

def check_symlink_filesystem(path: str, repo_root: str) -> Tuple[bool, Optional[str]]:
    """Check if path is a symlink using filesystem (os.path.islink).
    
    Secondary symlink detection using filesystem.
    Returns (is_symlink, reason_code or None).
    """
    full_path = os.path.join(repo_root, path)
    
    # Check direct symlink
    if os.path.islink(full_path):
        return (True, ReasonCode.SYMLINK_BLOCKED)
    
    # Check path components for symlinks
    parts = path.replace("\\", "/").split("/")
    check_path = repo_root
    for part in parts[:-1]:  # All parent components
        check_path = os.path.join(check_path, part)
        if os.path.islink(check_path):
            return (True, ReasonCode.SYMLINK_BLOCKED)
    
    return (False, None)

def check_symlink(path: str, repo_root: str) -> Tuple[bool, Optional[str]]:
    """Check if path is a symlink using both git index and filesystem.
    
    Uses git index mode as primary signal, filesystem as secondary.
    Returns (is_symlink, reason_code or None).
    """
    # Primary: git index mode
    is_sym, reason = check_symlink_git_index(path, repo_root)
    if is_sym:
        return (True, reason)
    
    # Secondary: filesystem
    is_sym, reason = check_symlink_filesystem(path, repo_root)
    if is_sym:
        return (True, reason)
    
    return (False, None)

# ============================================================================
# DENYLIST/ALLOWLIST MATCHING
# ============================================================================
def matches_denylist(path: str) -> Tuple[bool, Optional[str]]:
    """Check if path matches denylist. Returns (matched, reason_code)."""
    norm = normalize_path(path)
    
    # Check exact files first
    if norm in DENYLIST_EXACT_FILES:
        return (True, ReasonCode.DENYLIST_FILE_BLOCKED)
    
    # Check roots
    for root in DENYLIST_ROOTS:
        if norm.startswith(root):
            return (True, ReasonCode.DENYLIST_ROOT_BLOCKED)
    
    # Check extensions
    ext = os.path.splitext(norm)[1].lower()
    if ext in DENYLIST_EXTENSIONS:
        return (True, ReasonCode.DENYLIST_EXT_BLOCKED)
    
    return (False, None)

def matches_allowlist(path: str) -> bool:
    """Check if path is under an allowed root."""
    norm = normalize_path(path)
    return any(norm.startswith(root) for root in ALLOWLIST_ROOTS)

def check_extension_under_docs(path: str) -> Tuple[bool, Optional[str]]:
    """Check if extension is allowed under docs/."""
    norm = normalize_path(path)
    if not norm.startswith("docs/"):
        return (True, None)  # Not under docs, extension check N/A
    
    ext = os.path.splitext(norm)[1].lower()
    if ext not in ALLOWED_EXTENSIONS_DOCS:
        return (False, ReasonCode.NON_MD_EXTENSION_BLOCKED)
    
    return (True, None)

# ============================================================================
# REVIEW PACKETS ADD-ONLY
# ============================================================================
def check_review_packets_addonly(path: str, git_status: str) -> Tuple[bool, Optional[str]]:
    """Check if review packet operation is allowed (add-only .md)."""
    norm = normalize_path(path)
    if not norm.startswith("artifacts/review_packets/"):
        return (True, None)  # Not in scope
    
    # Must be .md
    if not norm.endswith(".md"):
        return (False, ReasonCode.NON_MD_IN_REVIEW_PACKETS)
    
    # Must be Add only
    if git_status != "A":
        return (False, ReasonCode.REVIEW_PACKET_NOT_ADD_ONLY)
    
    return (True, None)

# ============================================================================
# GIT DIFF PARSING
# ============================================================================
def parse_git_status_z(output: str) -> List[tuple]:
    """Parse git diff --name-status -z output.
    
    Returns:
      A/M/D       -> (status, path)
      R100/C100   -> (status, old_path, new_path)
    """
    if not output:
        return []
    
    # Split by NUL
    parts = output.split('\0')
    result = []
    i = 0
    
    while i < len(parts):
        part = parts[i]
        if not part:
            i += 1
            continue
        
        # Status is first character(s), may have percentage (R100, C050)
        status_char = part[0]
        
        if status_char in ('R', 'C'):
            # Rename/Copy: status\told_path\0new_path
            # In -z format with --name-status: "R100\told" then "new" as next
            if '\t' in part:
                status_full, old_path = part.split('\t', 1)
            else:
                status_full = part
                old_path = parts[i + 1] if i + 1 < len(parts) else ""
                i += 1
            
            new_path = parts[i + 1] if i + 1 < len(parts) else ""
            result.append((status_char, old_path, new_path))
            i += 2  # Skip new_path entry
        else:
            # A/M/D: status\tpath
            if '\t' in part:
                status_full, path = part.split('\t', 1)
                result.append((status_full[0], path))
            i += 1
    
    return result

def detect_blocked_ops(parsed: List[tuple]) -> List[Tuple[str, str, str]]:
    """Check for blocked operations (D/R/C). Returns [(path_desc, op, reason)]."""
    blocked = []
    for entry in parsed:
        status = entry[0]
        if status == "D":
            blocked.append((entry[1], "delete", ReasonCode.PH2_DELETE_BLOCKED))
        elif status == "R":
            old_path, new_path = entry[1], entry[2]
            blocked.append((f"{old_path}->{new_path}", "rename", ReasonCode.PH2_RENAME_BLOCKED))
        elif status == "C":
            old_path, new_path = entry[1], entry[2]
            blocked.append((f"{old_path}->{new_path}", "copy", ReasonCode.PH2_COPY_BLOCKED))
    return blocked

# ============================================================================
# CI DIFF COMMAND
# ============================================================================
def get_diff_command() -> Tuple[Optional[List[str]], str]:
    """Return (diff_command, mode). Returns (None, reason) if fail-closed."""
    
    # GitHub Actions
    if os.environ.get("GITHUB_ACTIONS") == "true":
        base_ref = os.environ.get("GITHUB_BASE_REF")  # e.g., "main"
        head_sha = os.environ.get("GITHUB_SHA")
        
        if not base_ref or not head_sha:
            return (None, ReasonCode.REFS_UNAVAILABLE)
        
        # Compute merge-base (requires fetch: git fetch origin $GITHUB_BASE_REF)
        merge_base_cmd = ["git", "merge-base", f"origin/{base_ref}", head_sha]
        result = subprocess.run(merge_base_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            return (None, ReasonCode.MERGE_BASE_FAILED)
        
        merge_base = result.stdout.strip()
        return (["git", "diff", "--name-status", "-z", f"{merge_base}..{head_sha}"], "CI_GITHUB")
    
    # GitLab CI
    elif os.environ.get("CI_MERGE_REQUEST_TARGET_BRANCH_SHA"):
        base_sha = os.environ.get("CI_MERGE_REQUEST_TARGET_BRANCH_SHA")
        head_sha = os.environ.get("CI_COMMIT_SHA", "HEAD")
        return (["git", "diff", "--name-status", "-z", f"{base_sha}..{head_sha}"], "CI_GITLAB")
    
    # Local mode (staged changes)
    else:
        return (["git", "diff", "--cached", "--name-status", "-z"], "LOCAL")

def execute_diff_and_parse(repo_root: str = ".") -> Tuple[Optional[List[tuple]], str, Optional[str]]:
    """Execute git diff and parse results. Terminal fail-closed on any error.
    
    Returns:
        (parsed_entries, mode, error_reason)
        - On success: (entries, mode, None)
        - On failure: (None, mode, reason_code)
    """
    cmd, mode = get_diff_command()
    
    if cmd is None:
        # get_diff_command already determined fail-closed
        return (None, mode, mode)  # mode contains reason code
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=repo_root)
        if result.returncode != 0:
            return (None, mode, ReasonCode.DIFF_EXEC_FAILED)
        
        parsed = parse_git_status_z(result.stdout)
        return (parsed, mode, None)
    except Exception:
        return (None, mode, ReasonCode.DIFF_EXEC_FAILED)

# ============================================================================
# HASHING
# ============================================================================
def compute_hash(content: str) -> dict:
    """Compute SHA-256 hash of content. Returns {"algorithm": "sha256", "hex": "..."}."""
    h = hashlib.sha256(content.encode('utf-8')).hexdigest()
    return {"algorithm": "sha256", "hex": h}

def compute_file_hash(filepath: str) -> dict:
    """Compute SHA-256 hash of file. Returns {"algorithm": "sha256", "hex": "..."}."""
    h = hashlib.sha256()
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return {"algorithm": "sha256", "hex": h.hexdigest()}

# ============================================================================
# TRUNCATION
# ============================================================================
def truncate_log(content: str) -> Tuple[str, bool]:
    """Truncate log content to caps. Returns (content, was_truncated)."""
    lines = content.split('\n')
    observed_lines = len(lines)
    observed_bytes = len(content.encode('utf-8'))
    
    if observed_lines <= LOG_MAX_LINES and observed_bytes <= LOG_MAX_BYTES:
        return (content, False)
    
    # Truncate by lines first
    if observed_lines > LOG_MAX_LINES:
        lines = lines[:LOG_MAX_LINES]
    
    truncated = '\n'.join(lines)
    
    # Then by bytes
    truncated_bytes = truncated.encode('utf-8')
    if len(truncated_bytes) > LOG_MAX_BYTES:
        truncated_bytes = truncated_bytes[:LOG_MAX_BYTES]
        truncated = truncated_bytes.decode('utf-8', errors='ignore')
    
    footer = f"\n[TRUNCATED] cap_lines={LOG_MAX_LINES}, cap_bytes={LOG_MAX_BYTES}, observed_lines={observed_lines}, observed_bytes={observed_bytes}"
    return (truncated + footer, True)
