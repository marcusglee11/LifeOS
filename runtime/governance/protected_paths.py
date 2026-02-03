"""
Protected Paths Registry - Hardcoded protection for governance and self-mod.

Per Phase 4D specification:
- Governance surfaces: Council-only modification
- Self-modification protection: Hardcoded files that control policy
- Agent identity: Model configs, role definitions

v1.0: Initial implementation for Phase 4D
v1.1: Hardening - canonical path normalization, escape prevention
"""

from typing import Dict, Optional
import posixpath

# =============================================================================
# Protected Paths Registry
# =============================================================================

PROTECTED_PATHS: Dict[str, str] = {
    # Governance surfaces - Council-only
    "docs/00_foundations/": "GOVERNANCE_FOUNDATION",
    "docs/01_governance/": "GOVERNANCE_RULINGS",
    "config/governance/": "GOVERNANCE_CONFIG",

    # Self-modification protection - Hardcoded
    "runtime/governance/self_mod_protection.py": "SELF_MOD_PROTECTION",
    "runtime/governance/envelope_enforcer.py": "ENVELOPE_ENFORCER",
    "runtime/governance/protected_paths.py": "PROTECTED_PATHS_REGISTRY",
    "runtime/governance/tool_policy.py": "TOOL_POLICY_GATE",
    "runtime/governance/syntax_validator.py": "SYNTAX_VALIDATOR",  # v1.1: Enforcement surface

    # Agent identity - Council-only
    "config/agent_roles/": "AGENT_IDENTITY",
    "config/models.yaml": "MODEL_CONFIG",
    "config/governance_baseline.yaml": "GOVERNANCE_BASELINE",

    # Build infrastructure - Self-protection
    "CLAUDE.md": "AGENT_INSTRUCTIONS",
    "GEMINI.md": "AGENT_INSTRUCTIONS",
}


# =============================================================================
# Allowed Code Paths (Phase 4D)
# =============================================================================

ALLOWED_CODE_PATHS = [
    "coo/",
    "runtime/",
    "tests/",
    "tests_doc/",
    "tests_recursive/",
]


# =============================================================================
# Exclusions within Allowed Paths
# =============================================================================

# Even though runtime/ is allowed, these specific files are protected
RUNTIME_EXCLUSIONS = [
    "runtime/governance/self_mod_protection.py",
    "runtime/governance/envelope_enforcer.py",
    "runtime/governance/protected_paths.py",
    "runtime/governance/tool_policy.py",
]


# =============================================================================
# Path Normalization (v1.1 Hardening)
# =============================================================================

def normalize_rel_path(path: str) -> tuple[bool, str, str]:
    """
    Normalize and validate a relative path for security.

    Normalization:
    - Replace backslashes with forward slashes
    - Collapse '.' and '..' segments deterministically
    - Ensure path is relative (not absolute)

    Rejection rules (fail-closed):
    - Absolute POSIX paths (starts with '/')
    - Windows drive paths (e.g., 'C:/', 'C:\\')
    - UNC paths (e.g., '\\\\server\\share')
    - Null bytes in path
    - Path traversal that escapes root (e.g., '../../etc/passwd')

    Args:
        path: Path to normalize (may be relative or absolute)

    Returns:
        (ok, normalized_path, reason) tuple
        - ok: True if path is valid relative path
        - normalized_path: Canonical form with '/' separators and collapsed dots
        - reason: Error description if ok=False, empty string if ok=True
    """
    # Check for null bytes (security)
    if '\x00' in path:
        return False, "", "PATH_CONTAINS_NULL_BYTE"

    # Replace backslashes with forward slashes
    normalized = path.replace('\\', '/')

    # Reject absolute POSIX paths
    if normalized.startswith('/'):
        return False, "", "ABSOLUTE_PATH_DENIED (POSIX: starts with /)"

    # Reject Windows drive letters (C:/, D:/, etc.)
    if len(normalized) >= 2 and normalized[1] == ':':
        return False, "", "ABSOLUTE_PATH_DENIED (Windows drive)"

    # Reject UNC paths (//server/share or \\server\share after normalization)
    if normalized.startswith('//'):
        return False, "", "ABSOLUTE_PATH_DENIED (UNC path)"

    # Normalize '.' and '..' using posixpath.normpath
    # This collapses redundant separators and up-level references
    try:
        collapsed = posixpath.normpath(normalized)
    except Exception as e:
        return False, "", f"PATH_NORMALIZATION_ERROR: {e}"

    # After normalization, reject paths that escape root
    # If normpath resulted in '..' at the start, it tried to escape
    if collapsed.startswith('..'):
        return False, "", "PATH_TRAVERSAL_DENIED (escapes root)"

    # Reject '.' as a standalone path (ambiguous)
    if collapsed == '.':
        return False, "", "PATH_IS_CURRENT_DIR"

    # Valid relative path
    return True, collapsed, ""


# =============================================================================
# Path Validation
# =============================================================================

def is_path_protected(path: str) -> tuple[bool, Optional[str]]:
    """
    Check if a path is protected from autonomous modification.

    Args:
        path: Path to check (relative to workspace root)

    Returns:
        (is_protected, reason) tuple
    """
    # Normalize path first (v1.1: canonical normalization)
    ok, normalized, error = normalize_rel_path(path)
    if not ok:
        # Path normalization failed (absolute, traversal, etc.)
        # Treat as protected (fail-closed: deny invalid paths)
        return True, f"INVALID_PATH: {error}"

    # Check exact matches first (files)
    if normalized in PROTECTED_PATHS:
        reason = PROTECTED_PATHS[normalized]
        return True, f"PROTECTED: {reason}"

    # Check directory prefixes (segment-safe: must match directory boundary)
    for protected_path, reason in PROTECTED_PATHS.items():
        if protected_path.endswith("/"):
            # Directory protection - use startswith to match prefix
            # normalized is already canonical, so 'runtime/governance/foo.py'.startswith('runtime/governance/')
            # will correctly match but 'runtime/governance_evil/foo.py' will not
            if normalized.startswith(protected_path):
                return True, f"PROTECTED: {reason}"
            # Also check if normalized equals the directory name without trailing slash
            if normalized == protected_path.rstrip('/'):
                return True, f"PROTECTED: {reason}"

    return False, None


def is_path_in_allowed_scope(path: str) -> tuple[bool, Optional[str]]:
    """
    Check if a path is within allowed code modification scope.

    Args:
        path: Path to check (relative to workspace root)

    Returns:
        (is_allowed, reason) tuple
    """
    # Normalize path first (v1.1: canonical normalization)
    ok, normalized, error = normalize_rel_path(path)
    if not ok:
        # Path normalization failed - treat as out of scope (fail-closed)
        return False, f"INVALID_PATH: {error}"

    # Check if in allowed paths (segment-safe: prefixes end with '/')
    # All ALLOWED_CODE_PATHS entries end with '/', so this is segment-safe
    for allowed_prefix in ALLOWED_CODE_PATHS:
        if normalized.startswith(allowed_prefix):
            return True, f"Within allowed scope: {allowed_prefix}"
        # Also check if normalized equals the directory name without trailing slash
        if normalized == allowed_prefix.rstrip('/'):
            return True, f"Within allowed scope: {allowed_prefix}"

    return False, f"PATH_OUTSIDE_ALLOWED_SCOPE: {path}"


def validate_write_path(path: str) -> tuple[bool, str]:
    """
    Validate if a path can be written to by autonomous agents.

    Policy:
    1. Protected paths are DENIED (highest priority)
    2. Allowed code paths are ALLOWED
    3. Everything else is DENIED

    Args:
        path: Path to validate

    Returns:
        (allowed, reason) tuple
    """
    # Check protected first (deny takes precedence)
    is_protected, protected_reason = is_path_protected(path)
    if is_protected:
        return False, protected_reason

    # Check allowed scope
    is_allowed, allowed_reason = is_path_in_allowed_scope(path)
    if not is_allowed:
        return False, allowed_reason

    # Allowed
    return True, "ALLOWED"


# =============================================================================
# Diff Budget Validation (Phase 4D)
# =============================================================================

MAX_DIFF_LINES = 300


def validate_diff_budget(diff_lines: int) -> tuple[bool, str]:
    """
    Validate diff is within budget.

    Args:
        diff_lines: Number of changed lines

    Returns:
        (within_budget, reason) tuple
    """
    if diff_lines > MAX_DIFF_LINES:
        return False, f"DIFF_BUDGET_EXCEEDED: {diff_lines} > {MAX_DIFF_LINES}"

    return True, f"Diff within budget: {diff_lines}/{MAX_DIFF_LINES} lines"
