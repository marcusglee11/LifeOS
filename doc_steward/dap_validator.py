"""
DAP (Deterministic Artefact Protocol) validator for LifeOS documentation.

Policy: Canonical Surface Only (for now)
- Only validates files within CANONICAL_ROOTS directories
- Deterministic and auditable (explicit allowlist, no heuristics)
"""
import os
import re
from pathlib import Path

# Explicit allowlist - matches link_checker.py
CANONICAL_ROOTS = ["00_foundations", "01_governance"]


def check_dap_compliance(
    doc_root: str,
    canonical_roots: list[str] | None = None,
) -> list[str]:
    """
    Check DAP naming compliance within canonical docs only.
    
    Args:
        doc_root: Path to docs/ directory
        canonical_roots: List of subdirectory names to check (default: CANONICAL_ROOTS)
    
    Returns:
        List of error strings for DAP violations
    """
    if canonical_roots is None:
        canonical_roots = CANONICAL_ROOTS
    
    errors: list[str] = []
    doc_root_path = Path(doc_root).resolve()
    
    # Pattern: Name_vX.Y.md or Name_vX.Y.Z.md
    version_pattern = re.compile(r'_[vV]\d+(?:\.\d+)*\.md$')
    
    # Only walk directories in canonical_roots
    for root_name in canonical_roots:
        root_dir = doc_root_path / root_name
        if not root_dir.exists():
            continue
        
        for md_file in root_dir.rglob("*.md"):
            filename = md_file.name
            rel_path = md_file.relative_to(doc_root_path)
            
            # Skip INDEX.md files (intentionally unversioned per convention)
            if filename == "INDEX.md":
                continue
            
            # Check version suffix
            if not version_pattern.search(filename):
                errors.append(f"DAP violation (no version suffix): {rel_path}")
            
            # Check spaces in filename
            if ' ' in filename:
                errors.append(f"DAP violation (spaces in name): {rel_path}")
    
    return errors
