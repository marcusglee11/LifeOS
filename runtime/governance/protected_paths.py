"""
Protected Paths Registry - Hardcoded protection for governance and self-mod.

Per Phase 4D specification:
- Governance surfaces: Council-only modification
- Self-modification protection: Hardcoded files that control policy
- Agent identity: Model configs, role definitions

v1.0: Initial implementation for Phase 4D
"""

from typing import Dict, Optional

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
    # Normalize path separators
    normalized = path.replace("\\", "/")

    # Check exact matches first (files)
    if normalized in PROTECTED_PATHS:
        reason = PROTECTED_PATHS[normalized]
        return True, f"PROTECTED: {reason}"

    # Check directory prefixes
    for protected_path, reason in PROTECTED_PATHS.items():
        if protected_path.endswith("/"):
            # Directory protection
            if normalized.startswith(protected_path):
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
    # Normalize path separators
    normalized = path.replace("\\", "/")

    # Check if in allowed paths
    for allowed_prefix in ALLOWED_CODE_PATHS:
        if normalized.startswith(allowed_prefix):
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
