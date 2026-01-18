"""
Context Resolver v1.0
=====================

Resolves context for mission synthesis.
Explicit-only: No inference, no globbing, no repo-wide search.
Fail-closed: Unresolvable hints halt execution.

Per Mission Synthesis Engine MVP.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Baseline context files (always included if they exist)
BASELINE_CONTEXT = [
    "docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md",
    "GEMINI.md",
]

# Allowed prefixes for context hints (envelope containment)
ALLOWED_PREFIXES = [
    "docs/",
    "config/",
    "runtime/",
    "artifacts/",
    "scripts/",
]


class ContextResolutionError(Exception):
    """Raised when context resolution fails (fail-closed)."""
    pass


@dataclass(frozen=True)
class ResolvedContext:
    """Resolved context for a task."""
    task_id: str
    resolved_paths: tuple[str, ...]
    baseline_paths: tuple[str, ...]
    unresolved_hints: tuple[str, ...]  # For audit; empty if all resolved


def _validate_hint_envelope(hint: str, repo_root: Path) -> Optional[str]:
    """
    Validate hint is within allowed envelope.
    
    Returns error message if invalid, None if valid.
    """
    # Normalize path
    norm = hint.replace("\\", "/")
    if norm.startswith("./"):
        norm = norm[2:]
    
    # Check prefix allowlist
    if not any(norm.startswith(prefix) for prefix in ALLOWED_PREFIXES):
        # Special case: allow root-level known files like GEMINI.md
        if norm not in ["GEMINI.md", "CLAUDE.md", "README.md"]:
            return f"Hint '{hint}' not in allowed prefixes: {ALLOWED_PREFIXES}"
    
    # Check for path traversal
    if ".." in norm:
        return f"Hint '{hint}' contains path traversal"
    
    # Check for absolute path
    if norm.startswith("/") or (len(norm) > 1 and norm[1] == ":"):
        return f"Hint '{hint}' is absolute path"
    
    return None


def _resolve_hint(hint: str, repo_root: Path) -> Optional[Path]:
    """
    Resolve a single context hint to a path.
    
    Returns resolved Path if file exists, None otherwise.
    """
    # Normalize
    norm = hint.replace("\\", "/")
    if norm.startswith("./"):
        norm = norm[2:]
    
    full_path = repo_root / norm
    
    # Must exist as file
    if full_path.is_file():
        return full_path
    
    return None


def resolve_context(
    task_id: str,
    context_hints: List[str],
    repo_root: Path,
    fail_on_unresolved: bool = True,
) -> ResolvedContext:
    """
    Resolve context for a task.
    
    Rules:
    1. Only use explicit context_hints
    2. Add baseline context files (if they exist)
    3. Enforce allowlist/containment per envelope
    4. Fail-closed if any hint cannot be resolved safely
    
    Args:
        task_id: Task identifier
        context_hints: List of repo-relative paths from TaskSpec
        repo_root: Repository root path
        fail_on_unresolved: If True, raise on unresolved hints
        
    Returns:
        ResolvedContext with resolved paths
        
    Raises:
        ContextResolutionError: If resolution fails and fail_on_unresolved=True
    """
    resolved: List[str] = []
    unresolved: List[str] = []
    errors: List[str] = []
    
    # Validate and resolve hints
    for hint in context_hints:
        # Envelope validation
        envelope_error = _validate_hint_envelope(hint, repo_root)
        if envelope_error:
            errors.append(envelope_error)
            continue
        
        # Resolution
        path = _resolve_hint(hint, repo_root)
        if path:
            resolved.append(hint)
        else:
            unresolved.append(hint)
    
    # Resolve baseline context
    baseline_resolved: List[str] = []
    for baseline in BASELINE_CONTEXT:
        path = _resolve_hint(baseline, repo_root)
        if path:
            baseline_resolved.append(baseline)
    
    # Fail-closed on errors
    if errors:
        raise ContextResolutionError(
            f"Context resolution failed for task '{task_id}': "
            + "; ".join(errors)
        )
    
    # Fail-closed on unresolved (if enabled)
    if fail_on_unresolved and unresolved:
        raise ContextResolutionError(
            f"Context resolution failed for task '{task_id}': "
            f"Unresolved hints: {unresolved}"
        )
    
    return ResolvedContext(
        task_id=task_id,
        resolved_paths=tuple(resolved),
        baseline_paths=tuple(baseline_resolved),
        unresolved_hints=tuple(unresolved),
    )
