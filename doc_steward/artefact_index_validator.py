"""
Artefact index validator.

For any directory containing ARTEFACT_INDEX.json:
- Validate schema compliance (using whatever schema is currently canonical)
- Validate all referenced paths exist
- Validate supersession chain consistency
- Validate "no orphan active files" (every non-archive file is indexed)

Fail-closed for indexed directories.
"""
import json
from pathlib import Path
from typing import Dict, List, Set, Any


def check_artefact_index(repo_root: str, directory: str = None) -> list[str]:
    """
    Validate ARTEFACT_INDEX.json files in the repository.

    Args:
        repo_root: Path to repository root
        directory: Optional specific directory to check (if None, scans all dirs)

    Returns:
        List of error strings for violations (empty if valid)
    """
    errors: list[str] = []
    repo_path = Path(repo_root).resolve()

    if directory:
        # Check specific directory
        dir_path = repo_path / directory
        if not dir_path.exists():
            return [f"Directory does not exist: {directory}"]

        index_path = dir_path / "ARTEFACT_INDEX.json"
        if index_path.exists():
            errors.extend(_validate_single_index(repo_path, dir_path, index_path))
    else:
        # Scan for all ARTEFACT_INDEX.json files
        docs_path = repo_path / "docs"
        if docs_path.exists():
            for index_path in docs_path.rglob("ARTEFACT_INDEX.json"):
                dir_path = index_path.parent
                errors.extend(_validate_single_index(repo_path, dir_path, index_path))

    return errors


def _validate_single_index(repo_path: Path, dir_path: Path, index_path: Path) -> list[str]:
    """
    Validate a single ARTEFACT_INDEX.json file.

    Args:
        repo_path: Repository root path
        dir_path: Directory containing the index
        index_path: Path to ARTEFACT_INDEX.json

    Returns:
        List of error strings
    """
    errors: list[str] = []
    rel_index = index_path.relative_to(repo_path)

    # Load and parse JSON
    try:
        with open(index_path, 'r', encoding='utf-8') as f:
            index_data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"{rel_index}: Invalid JSON: {e}")
        return errors
    except Exception as e:
        errors.append(f"{rel_index}: Failed to read: {e}")
        return errors

    # Validate schema
    errors.extend(_validate_schema(index_data, rel_index))

    # Extract artefact paths
    artefacts = index_data.get("artefacts", {})
    if isinstance(artefacts, dict):
        indexed_paths = _extract_artefact_paths(artefacts, repo_path)
    elif isinstance(artefacts, list):
        # Support list format: [{"path": "...", ...}, ...]
        indexed_paths = _extract_artefact_paths_from_list(artefacts, repo_path)
    else:
        errors.append(f"{rel_index}: 'artefacts' must be object or array")
        return errors

    # Validate all referenced paths exist
    errors.extend(_validate_paths_exist(indexed_paths, repo_path, rel_index))

    # Validate supersession chain consistency
    errors.extend(_validate_supersession_chains(artefacts, indexed_paths, rel_index))

    # Validate no orphan active files (all non-archive files in dir are indexed)
    errors.extend(_validate_no_orphans(dir_path, indexed_paths, repo_path, rel_index))

    return errors


def _validate_schema(data: Dict[str, Any], context: Path) -> list[str]:
    """
    Validate ARTEFACT_INDEX.json schema compliance.

    Args:
        data: Parsed JSON data
        context: Path for error messages

    Returns:
        List of error strings
    """
    errors: list[str] = []

    # Check required top-level fields
    if "meta" not in data:
        errors.append(f"{context}: Missing required field: 'meta'")

    if "artefacts" not in data:
        errors.append(f"{context}: Missing required field: 'artefacts'")

    # Validate meta section
    if "meta" in data:
        meta = data["meta"]
        if not isinstance(meta, dict):
            errors.append(f"{context}: 'meta' must be an object")
        else:
            # Check recommended meta fields (not strictly required)
            if "version" not in meta:
                errors.append(f"{context}: Recommended field missing in 'meta': 'version'")

    return errors


def _extract_artefact_paths(artefacts: Dict[str, Any], repo_path: Path) -> Set[Path]:
    """
    Extract file paths from artefacts dict (object format).

    Args:
        artefacts: Artefacts dictionary
        repo_path: Repository root

    Returns:
        Set of resolved file paths
    """
    paths = set()

    for key, value in artefacts.items():
        # Skip comment keys
        if key.startswith("_comment"):
            continue

        # Handle both string values and object values with "path" field
        if isinstance(value, str):
            path = repo_path / value
            paths.add(path)
        elif isinstance(value, dict) and "path" in value:
            path = repo_path / value["path"]
            paths.add(path)

    return paths


def _extract_artefact_paths_from_list(artefacts: List[Dict[str, Any]], repo_path: Path) -> Set[Path]:
    """
    Extract file paths from artefacts list (array format).

    Args:
        artefacts: Artefacts list
        repo_path: Repository root

    Returns:
        Set of resolved file paths
    """
    paths = set()

    for item in artefacts:
        if isinstance(item, dict) and "path" in item:
            path = repo_path / item["path"]
            paths.add(path)

    return paths


def _validate_paths_exist(paths: Set[Path], repo_path: Path, context: Path) -> list[str]:
    """
    Validate that all indexed paths exist.

    Args:
        paths: Set of file paths to check
        repo_path: Repository root
        context: Path for error messages

    Returns:
        List of error strings
    """
    errors: list[str] = []

    for path in sorted(paths):
        if not path.exists():
            rel_path = path.relative_to(repo_path) if path.is_relative_to(repo_path) else path
            errors.append(f"{context}: Indexed path does not exist: {rel_path}")

    return errors


def _validate_supersession_chains(artefacts: Any, indexed_paths: Set[Path], context: Path) -> list[str]:
    """
    Validate supersession chain consistency.

    Args:
        artefacts: Artefacts data (dict or list)
        indexed_paths: Set of indexed file paths
        context: Path for error messages

    Returns:
        List of error strings
    """
    errors: list[str] = []

    # Build map of path -> artefact data
    path_to_artefact: Dict[str, Any] = {}

    if isinstance(artefacts, dict):
        for key, value in artefacts.items():
            if key.startswith("_comment"):
                continue
            if isinstance(value, dict) and "path" in value:
                path_to_artefact[value["path"]] = value
    elif isinstance(artefacts, list):
        for item in artefacts:
            if isinstance(item, dict) and "path" in item:
                path_to_artefact[item["path"]] = item

    # Validate chains
    for path_str, artefact in path_to_artefact.items():
        # Check superseded_by references
        if "superseded_by" in artefact:
            superseded_by = artefact["superseded_by"]
            if superseded_by and superseded_by not in path_to_artefact:
                errors.append(
                    f"{context}: {path_str} references non-indexed superseded_by: {superseded_by}"
                )

        # Check supersedes references
        if "supersedes" in artefact:
            supersedes = artefact["supersedes"]
            if isinstance(supersedes, str):
                supersedes = [supersedes]
            if isinstance(supersedes, list):
                for superseded_path in supersedes:
                    if superseded_path and superseded_path not in path_to_artefact:
                        errors.append(
                            f"{context}: {path_str} references non-indexed supersedes: {superseded_path}"
                        )

    return errors


def _validate_no_orphans(dir_path: Path, indexed_paths: Set[Path], repo_path: Path, context: Path) -> list[str]:
    """
    Validate that all non-archive files in directory are indexed.

    Args:
        dir_path: Directory containing the index
        indexed_paths: Set of indexed file paths
        repo_path: Repository root
        context: Path for error messages

    Returns:
        List of error strings
    """
    errors: list[str] = []

    # Deterministic exemptions
    EXEMPT_FILES = {"README.md", "ARTEFACT_INDEX.json"}

    # Find all markdown files in directory (non-recursive, excluding archive/)
    for item in dir_path.iterdir():
        # Skip archive directory
        if item.is_dir() and item.name == "archive":
            continue

        # Only check markdown files at root level
        if item.is_file() and item.suffix == ".md":
            # Check if exempt
            if item.name in EXEMPT_FILES:
                continue

            # Check if indexed
            if item.resolve() not in indexed_paths:
                rel_path = item.relative_to(repo_path)
                errors.append(
                    f"{context}: Orphan active file not in index: {rel_path}"
                )

    return errors
