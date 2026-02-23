"""
PlanCore canonicalization, SHA-256 hashing, and workspace tree OID resolution.

Provides:
- assert_no_floats: fail-closed float guard for canonical JSON
- canonicalize_plan_core: produce deterministic bytes from a PlanCore dict
- compute_plan_core_sha256: bare 64-char hex SHA-256 of canonical bytes
- resolve_tree_oid: git tree object ID for a given commit SHA
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from runtime.util.canonical import canonical_json


def assert_no_floats(obj: Any, _path: str = "") -> None:
    """
    Recursively assert that obj contains no float values.

    Raises:
        ValueError: If any float is found, with the path to the offending value.
    """
    if isinstance(obj, float):
        raise ValueError(f"Float value not allowed in canonical data (at {_path or 'root'}): {obj!r}")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            assert_no_floats(v, f"{_path}.{k}" if _path else k)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            assert_no_floats(v, f"{_path}[{i}]")


def canonicalize_plan_core(plan_core: dict) -> bytes:
    """
    Produce deterministic canonical JSON bytes from a PlanCore dict.

    Validates no floats before serialization (fail-closed).

    Args:
        plan_core: PlanCore dictionary.

    Returns:
        Canonical UTF-8 JSON bytes (RFC 8785 compliant for this data subset).

    Raises:
        ValueError: If plan_core contains float values.
    """
    assert_no_floats(plan_core)
    return canonical_json(plan_core)


def compute_plan_core_sha256(plan_core: dict) -> str:
    """
    Compute SHA-256 hash of a PlanCore dict as bare 64-char lowercase hex.

    Args:
        plan_core: PlanCore dictionary.

    Returns:
        64-character lowercase hex SHA-256 string.

    Raises:
        ValueError: If plan_core contains float values.
    """
    canonical_bytes = canonicalize_plan_core(plan_core)
    return hashlib.sha256(canonical_bytes).hexdigest()


def resolve_tree_oid(sha: str, repo_root: str | Path | None = None) -> str:
    """
    Resolve the git tree object ID (OID) for a given commit SHA.

    Uses `git show -s --format=%T <sha>` to get the tree OID.

    Args:
        sha: Commit SHA (full or abbreviated).
        repo_root: Optional path to the git repository root. Defaults to CWD.

    Returns:
        40-character hex tree OID string.

    Raises:
        ValueError: If git command fails or returns unexpected output.
    """
    cmd = ["git", "show", "-s", "--format=%T", sha]
    kwargs: dict = {
        "capture_output": True,
        "text": True,
    }
    if repo_root is not None:
        kwargs["cwd"] = str(repo_root)

    try:
        result = subprocess.run(cmd, **kwargs)
    except FileNotFoundError as e:
        raise ValueError(f"git not found: {e}") from e

    if result.returncode != 0:
        raise ValueError(
            f"git show failed for SHA {sha!r}: {result.stderr.strip()}"
        )

    oid = result.stdout.strip()
    if not oid:
        raise ValueError(f"git show returned empty output for SHA {sha!r}")

    # git tree OIDs are 40-char hex
    if len(oid) != 40 or not all(c in "0123456789abcdef" for c in oid.lower()):
        raise ValueError(f"Unexpected tree OID format for SHA {sha!r}: {oid!r}")

    return oid
