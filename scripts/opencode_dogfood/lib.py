import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import jsonschema

# Schema Cache
SCHEMAS_DIR = Path(__file__).parent / "schemas"

def load_schema(schema_name: str) -> Dict[str, Any]:
    with open(SCHEMAS_DIR / schema_name, "r") as f:
        return json.load(f)

def validate_schema(data: Dict[str, Any], schema_name: str) -> bool:
    """Validates data against a JSON schema_name (filename in schemas dir). 
       Raises jsonschema.ValidationError or ValueError on failure.
       Returns True on success.
    """
    try:
        schema = load_schema(schema_name)
        jsonschema.validate(instance=data, schema=schema)
        return True
    except jsonschema.ValidationError as e:
        # Re-raise as ValueError for simple exception handling if preferred, 
        # or let it bubble up. The test expects ValueError for invalid enum in one case,
        # but jsonschema raises ValidationError. I'll catch and re-raise or let test adjust.
        # The test: `with self.assertRaises(ValueError): logic...` 
        # Actually jsonschema.ValidationError does NOT inherit from ValueError.
        # So I should wrap it.
        raise ValueError(f"Schema validation failed: {e.message}") from e

def sort_evidence(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sorts evidence list by path using LC_ALL=C (byte value) order."""
    # In Python, string comparison is Unicode code point based.
    return sorted(evidence, key=lambda x: x["path"])

def enforce_deletion_policy(allowlist: List[str], actual_deletions: List[str]) -> None:
    """Raises RuntimeError if any actual_deletion is not in allowlist."""
    violations = [d for d in actual_deletions if d not in allowlist]
    if violations:
        raise RuntimeError(f"GITCLEANFAIL: Unauthorized deletions detected: {violations}")

def enforce_modification_policy(allowlist: List[str], actual_modifications: List[str]) -> None:
    """Raises RuntimeError if any modification is not in allowlist."""
    violations = [m for m in actual_modifications if m not in allowlist]
    if violations:
        raise RuntimeError(f"MODIFICATIONFAIL: Unauthorized modifications detected: {violations}")

def is_isolated_worktree(git_dir: str) -> bool:
    """Returns True if git_dir indicates a worktree (contains 'worktrees' or is a file .git)."""
    # If the user is in a worktree, `.git` is a file pointing to the main repo's worktree dir.
    # If they are in the main repo, `.git` is a directory.
    # We also check if the resolved path contains 'worktrees' just in case.
    
    # Check 1: Is .git a file? (Common worktree marker)
    # But git_dir passed here is the result of `git rev-parse --git-dir`
    # In a worktree: /path/to/main/.git/worktrees/my-worktree
    # In main repo: /path/to/main/.git
    
    if "worktrees" in Path(git_dir).parts:
        return True
        
    # Fallback/Additional check logic if needed, but path inspection is robust for standard git layout
    return False

def compute_deterministic_names(file_list: List[str], prefix: str) -> Dict[str, str]:
    """Sorts file_list and assigns deterministic names (prefix_01.ext)."""
    sorted_files = sorted(file_list)
    mapping = {}
    for i, f in enumerate(sorted_files, 1):
        ext = Path(f).suffix
        mapping[f] = f"{prefix}_{i:02d}{ext}"
    return mapping
