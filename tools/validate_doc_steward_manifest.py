#!/usr/bin/env python3
"""
validate_doc_steward_manifest.py — CLI validator for doc_ingest manifests.

Usage:
    python tools/validate_doc_steward_manifest.py <manifest_path> [--repo-root PATH]

Exit codes:
    0  manifest is valid
    1  manifest is invalid (errors printed to stderr)
    2  usage error
"""

import argparse
import json
import sys
from pathlib import Path


def _get_repo_root(repo_root_arg: str | None) -> Path:
    if repo_root_arg:
        return Path(repo_root_arg).resolve()
    import subprocess

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("Error: cannot determine repo root via git", file=sys.stderr)
        sys.exit(2)
    return Path(result.stdout.strip()).resolve()


def validate(manifest_path: Path, repo_root: Path) -> list[str]:
    """
    Return list of error strings (empty = valid).
    Validates against runtime/stewardship/doc_ingest invariants.
    """
    errors: list[str] = []

    # Load manifest
    try:
        data = json.loads(manifest_path.read_bytes())
    except (json.JSONDecodeError, OSError) as exc:
        return [f"Cannot parse manifest JSON: {exc}"]

    if not isinstance(data, dict):
        return ["Manifest must be a JSON object."]

    # Import enums and constants from doc_ingest
    sys.path.insert(0, str(repo_root))
    try:
        from runtime.stewardship.doc_ingest import (
            _FILENAME_PATTERN,
            _FORBIDDEN_MANIFEST_FIELDS,
            _REQUIRED_HEADERS,
            _REQUIRED_MANIFEST_FIELDS,
            SCHEMA_ID,
            SCHEMA_VERSION,
            VALID_BINDING_CLASSES,
            VALID_CANONICALITY_VALUES,
        )
    except ImportError as exc:
        return [f"Cannot import doc_ingest module: {exc}"]

    # Forbidden fields
    for bad in _FORBIDDEN_MANIFEST_FIELDS:
        if bad in data:
            errors.append(f"Forbidden field present: '{bad}'")

    # Required fields
    missing = _REQUIRED_MANIFEST_FIELDS - set(data.keys())
    if missing:
        errors.append(f"Missing required fields: {sorted(missing)}")
        return errors  # Cannot continue without required fields

    # Schema identity
    if data.get("schema") != SCHEMA_ID:
        errors.append(f"schema must be '{SCHEMA_ID}', got: {data.get('schema')!r}")
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"schema_version must be '{SCHEMA_VERSION}', got: {data.get('schema_version')!r}"
        )

    # Enum checks
    if data.get("binding_class") not in VALID_BINDING_CLASSES:
        errors.append(
            f"binding_class '{data.get('binding_class')}' not in {sorted(VALID_BINDING_CLASSES)}"
        )
    if data.get("canonicality") not in VALID_CANONICALITY_VALUES:
        errors.append(
            f"canonicality '{data.get('canonicality')}' not in {sorted(VALID_CANONICALITY_VALUES)}"
        )

    # commit block
    commit = data.get("commit", {})
    if not isinstance(commit, dict):
        errors.append("'commit' must be an object")
    else:
        if "enabled" not in commit:
            errors.append("commit.enabled is required")
        elif not isinstance(commit["enabled"], bool):
            errors.append("commit.enabled must be a boolean")
        if "message" not in commit:
            errors.append("commit.message is required")

    # source_path existence
    raw_source = data.get("source_path", "")
    import os

    source_path = Path(raw_source) if os.path.isabs(raw_source) else repo_root / raw_source
    if not source_path.exists():
        errors.append(f"source_path does not exist: {raw_source}")

    # dest_path naming convention
    raw_dest = data.get("dest_path", "")
    dest_name = Path(raw_dest).name
    if not _FILENAME_PATTERN.match(dest_name):
        errors.append(
            f"dest_path filename '{dest_name}' does not match naming convention "
            f"(expected: Name_vX.Y[.Z].md)"
        )

    # target_index_path existence
    raw_index = data.get("target_index_path", "")
    if raw_index:
        index_path = Path(raw_index) if os.path.isabs(raw_index) else repo_root / raw_index
        if not index_path.exists():
            errors.append(f"target_index_path does not exist: {raw_index}")

    # supersedes existence
    for sup in data.get("supersedes", []):
        sup_path = Path(sup) if os.path.isabs(sup) else repo_root / sup
        if not sup_path.exists():
            errors.append(f"supersedes target does not exist: {sup}")

    # source metadata headers (only check if file exists)
    if source_path.exists() and not errors:
        try:
            text = source_path.read_text(encoding="utf-8")
            for hdr in _REQUIRED_HEADERS:
                if hdr not in text:
                    errors.append(f"Source file missing required header: {hdr}")
        except OSError as exc:
            errors.append(f"Cannot read source_path: {exc}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a doc_ingest manifest file.")
    parser.add_argument("manifest", type=Path, help="Path to manifest JSON file")
    parser.add_argument(
        "--repo-root",
        type=str,
        default=None,
        help="Repo root (default: detected via git)",
    )
    args = parser.parse_args()

    if not args.manifest.exists():
        print(f"Error: manifest file not found: {args.manifest}", file=sys.stderr)
        return 2

    repo_root = _get_repo_root(args.repo_root)
    errors = validate(args.manifest, repo_root)

    if errors:
        print(f"INVALID: {args.manifest}", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"VALID: {args.manifest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
