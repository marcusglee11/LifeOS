"""
Link checker for LifeOS documentation.

Policy: Canonical Surface Only (for now)
- Only checks links within CANONICAL_ROOTS directories
- Skips external, anchor-only, and template token links
- Deterministic and auditable (explicit allowlist, no heuristics)
"""
import os
import re
from pathlib import Path

# Explicit allowlist - no heuristics
CANONICAL_ROOTS = ["00_foundations", "01_governance"]


def check_links(
    doc_root: str,
    canonical_roots: list[str] | None = None,
) -> list[str]:
    """
    Check internal links within canonical docs only.
    
    Args:
        doc_root: Path to docs/ directory
        canonical_roots: List of subdirectory names to check (default: CANONICAL_ROOTS)
    
    Returns:
        List of error strings for broken links
    """
    if canonical_roots is None:
        canonical_roots = CANONICAL_ROOTS
    
    errors: list[str] = []
    doc_root = os.path.abspath(doc_root)
    doc_root_path = Path(doc_root)
    
    # Only walk directories in canonical_roots
    for root_name in canonical_roots:
        root_dir = doc_root_path / root_name
        if not root_dir.exists():
            continue
        
        for md_file in root_dir.rglob("*.md"):
            errors.extend(_check_file_links(md_file, doc_root_path))
    
    return errors


def _check_file_links(filepath: Path, doc_root: Path) -> list[str]:
    """Check all internal links in a single markdown file."""
    errors: list[str] = []
    
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        return errors  # Skip unreadable files
    
    # Find all markdown links: [text](target)
    links = re.findall(r'\[.*?\]\((.*?)\)', content)
    
    for link in links:
        error = _validate_link(link, filepath, doc_root)
        if error:
            errors.append(error)
    
    return errors


def _validate_link(link: str, source_file: Path, doc_root: Path) -> str | None:
    """
    Validate a single link. Returns error string or None if valid.
    
    Skips:
    - External links (http://, https://, mailto:, file:)
    - Anchor-only links (#...)
    - Template tokens ({...})
    """
    # Skip external links
    if link.startswith(("http://", "https://", "mailto:", "file:")):
        return None
    
    # Skip anchor-only links
    if link.startswith("#"):
        return None
    
    # Skip template tokens (e.g., {relative_repo_path})
    # Must match {token} pattern, not just any brace character
    if re.search(r"\{[^}]+\}", link):
        return None
    
    # Remove anchor from link for path resolution
    clean_link = link.split("#")[0]
    if not clean_link:
        return None  # Was anchor-only after split
    
    # Normalize path separators
    clean_link = clean_link.replace("\\", "/")
    
    # Resolve relative to source file's directory
    source_dir = source_file.parent
    target_path = (source_dir / clean_link).resolve()
    
    # Check target exists
    if not target_path.exists():
        rel_source = source_file.relative_to(doc_root)
        return f"Broken link in {rel_source}: {link}"
    
    # Verify target is within docs/ (fail closed on escape)
    try:
        target_path.relative_to(doc_root.parent)  # Allow resolution to repo root
    except ValueError:
        rel_source = source_file.relative_to(doc_root)
        return f"Link escapes repo in {rel_source}: {link}"
    
    return None
