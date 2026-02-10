"""
Canonical Serialization - Deterministic JSON for reproducible artifacts.

This module provides the single source of truth for canonical JSON serialization
per LifeOS determinism requirements:

1. Encoding: UTF-8, no BOM
2. Whitespace: None (compact)
3. Key ordering: Lexicographically sorted
4. Array ordering: Preserved
5. No NaN/Infinity (fail-closed)

All hashes and artifacts MUST use these functions to ensure reproducibility.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Union


def canonical_json(obj: Any) -> bytes:
    """
    Produce canonical JSON bytes for deterministic hashing.

    Per LifeOS determinism requirements:
    1. Encoding: UTF-8, no BOM
    2. Whitespace: None (compact)
    3. Key ordering: Lexicographically sorted
    4. Array ordering: Preserved
    5. No NaN/Infinity (fail-closed)

    Args:
        obj: Object to serialize

    Returns:
        Canonical JSON as UTF-8 bytes

    Raises:
        ValueError: If obj contains NaN or Infinity values
    """
    return json.dumps(
        obj,
        separators=(",", ":"),
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,  # Fail-closed: reject NaN/Infinity
    ).encode("utf-8")


def canonical_json_str(obj: Any) -> str:
    """
    Produce canonical JSON string for deterministic output.

    Same as canonical_json() but returns string instead of bytes.

    Args:
        obj: Object to serialize

    Returns:
        Canonical JSON as string
    """
    return canonical_json(obj).decode("utf-8")


def compute_hash(obj: Any, algorithm: str = "sha256") -> str:
    """
    Compute hash of an object using canonical JSON serialization.

    Args:
        obj: Object to hash
        algorithm: Hash algorithm (sha256, sha384, sha512)

    Returns:
        Hash string in format "algorithm:hexdigest"

    Raises:
        ValueError: If obj contains NaN/Infinity or unknown algorithm
    """
    if algorithm not in ("sha256", "sha384", "sha512"):
        raise ValueError(f"Unknown hash algorithm: {algorithm}")

    hasher = hashlib.new(algorithm)
    hasher.update(canonical_json(obj))
    return f"{algorithm}:{hasher.hexdigest()}"


def compute_sha256(obj: Any) -> str:
    """
    Compute SHA256 hash of an object.

    Convenience wrapper for compute_hash with sha256.

    Args:
        obj: Object to hash

    Returns:
        SHA256 hash string in format "sha256:hexdigest"
    """
    return compute_hash(obj, "sha256")


def canonical_dump(obj: Any, fp: Any, indent: int = 0) -> None:
    """
    Write canonical JSON to a file-like object.

    Args:
        obj: Object to serialize
        fp: File-like object with write() method
        indent: Indentation level (0 = compact, 2 = pretty)
    """
    if indent > 0:
        # Pretty print with sorted keys
        json.dump(
            obj,
            fp,
            separators=(",", ": "),
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            indent=indent,
        )
    else:
        # Compact
        fp.write(canonical_json_str(obj))


def canonical_dumps(obj: Any, indent: int = 0) -> str:
    """
    Serialize object to canonical JSON string.

    Args:
        obj: Object to serialize
        indent: Indentation level (0 = compact, 2 = pretty)

    Returns:
        Canonical JSON string
    """
    if indent > 0:
        return json.dumps(
            obj,
            separators=(",", ": "),
            sort_keys=True,
            ensure_ascii=False,
            allow_nan=False,
            indent=indent,
        )
    return canonical_json_str(obj)


def verify_canonical(json_str: str, obj: Any) -> bool:
    """
    Verify that a JSON string matches canonical form of an object.

    Args:
        json_str: JSON string to verify
        obj: Object to compare against

    Returns:
        True if json_str matches canonical form of obj
    """
    try:
        expected = canonical_json_str(obj)
        return json_str == expected
    except (ValueError, TypeError):
        return False
