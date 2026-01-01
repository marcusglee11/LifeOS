#!/usr/bin/env python3
"""
LifeOS Governance Artefact Index Validator

Validates docs/01_governance/ARTEFACT_INDEX.json against the following rules:
1. Valid JSON with "artefacts" object
2. All artefact IDs are non-empty strings
3. All paths are non-empty strings
4. All paths are repo-root relative (start with "docs/01_governance/")
5. All paths use forward slashes only (no backslashes)
6. All paths are not absolute (Unix or Windows)
7. All paths contain no traversal segments ("..")
8. All paths point to existing files

Usage:
    python tools/validate_governance_index.py [--repo-root PATH]

Exit codes:
    0 - Validation passed
    1 - Validation failed
"""

import argparse
import json
import sys
from pathlib import Path


def validate_index(repo_root: Path) -> list[str]:
    """Validate the governance artefact index. Returns list of error messages."""
    errors: list[str] = []
    index_path = repo_root / "docs" / "01_governance" / "ARTEFACT_INDEX.json"

    # Check index file exists
    if not index_path.is_file():
        errors.append(f"Index file not found: {index_path}")
        return errors

    # Parse JSON
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in index file: {e}")
        return errors

    # Check structure
    if not isinstance(data, dict):
        errors.append("Index must be a JSON object")
        return errors

    if "artefacts" not in data:
        errors.append("Index must contain 'artefacts' key")
        return errors

    if "meta" not in data:
        errors.append("Index must contain 'meta' key")
        return errors

    meta = data["meta"]
    if not isinstance(meta, dict) or "version" not in meta:
        errors.append("'meta' must contain 'version'")
        return errors

    artefacts = data["artefacts"]
    if not isinstance(artefacts, dict):
        errors.append("'artefacts' must be an object")
        return errors

    # Validate each artefact entry
    for artefact_id, artefact_path in artefacts.items():
        prefix = f"[{artefact_id}]"

        # Validate ID
        if not isinstance(artefact_id, str) or not artefact_id.strip():
            errors.append(f"{prefix} Artefact ID must be a non-empty string")
            continue

        # Validate path is non-empty string
        if not isinstance(artefact_path, str) or not artefact_path.strip():
            errors.append(f"{prefix} Path must be a non-empty string")
            continue

        # Check for backslashes
        if "\\" in artefact_path:
            errors.append(f"{prefix} Path must use forward slashes only: {artefact_path}")
            continue

        # Check not absolute (Unix)
        if artefact_path.startswith("/"):
            errors.append(f"{prefix} Path must not be absolute (Unix): {artefact_path}")
            continue

        # Check not absolute (Windows - drive letter)
        if len(artefact_path) >= 2 and artefact_path[1] == ":":
            errors.append(f"{prefix} Path must not be absolute (Windows): {artefact_path}")
            continue

        # Check for traversal segments
        if ".." in artefact_path.split("/"):
            errors.append(f"{prefix} Path must not contain traversal segments (..): {artefact_path}")
            continue

        # Check path starts with allowed docs directories
        allowed_prefixes = ("docs/00_foundations/", "docs/01_governance/")
        if not artefact_path.startswith(allowed_prefixes):
            errors.append(f"{prefix} Path must start with one of {allowed_prefixes}: {artefact_path}")
            continue

        # Check file exists
        full_path = repo_root / artefact_path
        if not full_path.is_file():
            errors.append(f"{prefix} File does not exist: {artefact_path}")
            continue

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate LifeOS governance artefact index"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path.cwd(),
        help="Repository root directory (default: current directory)",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    print(f"Validating governance index at: {repo_root}")

    errors = validate_index(repo_root)

    if errors:
        print("\n[FAILED] Validation FAILED:\n")
        for error in errors:
            print(f"  * {error}")
        print()
        return 1
    else:
        print("\n[PASSED] Validation passed: All artefacts valid and files exist.\n")
        return 0


if __name__ == "__main__":
    sys.exit(main())
