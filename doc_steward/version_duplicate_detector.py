"""
Version duplicate detector.

Scans for *_vX.Y.md patterns and reports groups where >1 file exists outside archives.
This is warn-only and informational; it never blocks CI/validators.

If ARTEFACT_INDEX exists for a directory, the report also notes whether lineage is recorded.
"""
import re
from pathlib import Path
from typing import Dict, List
import json

# Pattern to match versioned files: *_vX.Y.md or *_vX.Y.Z.md
VERSION_PATTERN = re.compile(r'^(.+)_v(\d+\.\d+(?:\.\d+)?)\.md$')


def scan_version_duplicates(repo_root: str) -> Dict[str, List[str]]:
    """
    Scan for version duplicate groups in active (non-archive) paths.

    Args:
        repo_root: Path to repository root

    Returns:
        Dictionary mapping base name to list of file paths (only includes groups with >1 file)
    """
    repo_path = Path(repo_root).resolve()
    docs_path = repo_path / "docs"

    if not docs_path.exists():
        return {}

    # Collect all versioned files outside archives
    versioned_files: Dict[str, List[Path]] = {}

    for md_file in docs_path.rglob("*.md"):
        # Skip files in archive paths
        if _is_in_archive(md_file, docs_path):
            continue

        # Check if filename matches version pattern
        match = VERSION_PATTERN.match(md_file.name)
        if match:
            base_name = match.group(1)
            version = match.group(2)

            if base_name not in versioned_files:
                versioned_files[base_name] = []

            versioned_files[base_name].append(md_file)

    # Filter to only groups with >1 file
    duplicate_groups = {
        base: [str(f.relative_to(repo_path)) for f in files]
        for base, files in versioned_files.items()
        if len(files) > 1
    }

    return duplicate_groups


def check_version_duplicates_with_lineage(repo_root: str) -> List[str]:
    """
    Generate a report of version duplicates with lineage information.

    Args:
        repo_root: Path to repository root

    Returns:
        List of report lines (warnings, not errors)
    """
    repo_path = Path(repo_root).resolve()
    duplicate_groups = scan_version_duplicates(repo_root)

    if not duplicate_groups:
        return ["No version duplicate groups found in active paths."]

    report: List[str] = []
    report.append(f"Found {len(duplicate_groups)} version duplicate group(s) in active paths:")
    report.append("")

    for base_name in sorted(duplicate_groups.keys()):
        files = duplicate_groups[base_name]
        report.append(f"  Base: {base_name}")
        for file_path in sorted(files):
            report.append(f"    - {file_path}")

            # Check if directory has ARTEFACT_INDEX and if lineage is recorded
            file_full_path = repo_path / file_path
            dir_path = file_full_path.parent
            index_path = dir_path / "ARTEFACT_INDEX.json"

            if index_path.exists():
                lineage_status = _check_lineage_in_index(index_path, file_full_path.name)
                if not lineage_status:
                    report.append(f"      [WARNING] Missing lineage in ARTEFACT_INDEX")

        report.append("")

    return report


def _is_in_archive(path: Path, docs_path: Path) -> bool:
    """
    Check if a path is inside any archive directory.

    Args:
        path: Path to check
        docs_path: Root docs directory

    Returns:
        True if path is inside any /archive/ or docs/99_archive/
    """
    # Check if path is under docs/99_archive/
    try:
        path.relative_to(docs_path / "99_archive")
        return True
    except ValueError:
        pass

    # Check if any parent directory is named "archive"
    for parent in path.parents:
        if parent.name == "archive":
            return True
        if parent == docs_path:
            break

    return False


def _check_lineage_in_index(index_path: Path, filename: str) -> bool:
    """
    Check if a file's lineage is recorded in ARTEFACT_INDEX.

    Args:
        index_path: Path to ARTEFACT_INDEX.json
        filename: Name of the file to check

    Returns:
        True if lineage is recorded (has superseded_by or supersedes fields)
    """
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)

        # Look for the file in artefacts list
        artefacts = index_data.get("artefacts", [])
        for artefact in artefacts:
            path = artefact.get("path", "")
            if path.endswith(filename):
                # Check if it has lineage fields
                has_lineage = (
                    "superseded_by" in artefact or
                    "supersedes" in artefact
                )
                return has_lineage

        return False
    except Exception:
        # If we can't read/parse the index, assume no lineage
        return False
