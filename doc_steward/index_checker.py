"""
Index checker for LifeOS documentation.

Policy: Canonical Surface Only (for now)
- Only checks for unindexed files within CANONICAL_ROOTS directories
- Deterministic and auditable (explicit allowlist, no heuristics)
"""
import os
import re
from pathlib import Path

# Explicit allowlist - matches link_checker.py and dap_validator.py
CANONICAL_ROOTS = ["00_foundations", "01_governance"]


def check_index(
    doc_root: str,
    index_path: str,
    canonical_roots: list[str] | None = None,
) -> list[str]:
    """
    Check index completeness within canonical docs only.
    
    Args:
        doc_root: Path to docs/ directory
        index_path: Path to INDEX.md file
        canonical_roots: List of subdirectory names to check (default: CANONICAL_ROOTS)
    
    Returns:
        List of error strings for missing or unindexed files
    """
    if canonical_roots is None:
        canonical_roots = CANONICAL_ROOTS
    
    errors: list[str] = []
    
    if not os.path.exists(index_path):
        return [f"Index file missing: {index_path}"]
    
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract links from index [Label](path)
    links = re.findall(r'\[.*?\]\((.*?)\)', content)
    indexed_files: set[str] = set()
    
    doc_root_path = Path(doc_root).resolve()
    index_dir = Path(index_path).resolve().parent
    
    for link in links:
        if link.startswith(('http', 'file:', 'mailto:')):
            continue
        
        # Handle anchors
        clean_link = link.split('#')[0]
        if not clean_link:
            continue
        
        # Resolve relative to index location
        abs_path = (index_dir / clean_link).resolve()
        
        if not abs_path.exists():
            errors.append(f"Indexed file missing: {clean_link}")
        else:
            # Check if it is inside doc_root
            try:
                rel_path = abs_path.relative_to(doc_root_path)
                indexed_files.add(str(rel_path).replace('\\', '/'))
            except ValueError:
                pass  # Not inside doc_root
    
    # Check for unindexed files - ONLY within canonical roots
    for root_name in canonical_roots:
        root_dir = doc_root_path / root_name
        if not root_dir.exists():
            continue
        
        for md_file in root_dir.rglob("*.md"):
            # Skip the index file itself
            if md_file.resolve() == Path(index_path).resolve():
                continue
            
            # Skip INDEX.md files in subdirectories
            if md_file.name == "INDEX.md":
                continue
            
            rel_path = str(md_file.relative_to(doc_root_path)).replace('\\', '/')
            if rel_path not in indexed_files:
                errors.append(f"Unindexed file: {rel_path}")
    
    return errors
