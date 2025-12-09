"""
FP-4.x CND-2: Hash Policy v1
Council-defined hash function for all AMU₀ and INDEX integrity.
Changes to this policy require explicit Council approval.
"""
import hashlib
import json
from typing import Any


# Canonical hash algorithm - Council-approved
HASH_ALGORITHM = "sha256"


def hash_bytes(data: bytes) -> str:
    """
    Compute SHA-256 hash of raw bytes.
    
    Args:
        data: Raw bytes to hash.
        
    Returns:
        Hex-encoded SHA-256 hash.
    """
    return hashlib.sha256(data).hexdigest()


def hash_json(obj: Any) -> str:
    """
    Compute SHA-256 hash of a JSON-serializable object.
    
    Uses deterministic JSON encoding (sorted keys, no extra whitespace).
    
    Args:
        obj: JSON-serializable object.
        
    Returns:
        Hex-encoded SHA-256 hash.
    """
    canonical = json.dumps(obj, sort_keys=True, separators=(',', ':'))
    return hash_bytes(canonical.encode('utf-8'))


def hash_file(path: str) -> str:
    """
    Compute SHA-256 hash of a file's contents.
    
    Args:
        path: Path to the file.
        
    Returns:
        Hex-encoded SHA-256 hash.
    """
    with open(path, 'rb') as f:
        return hash_bytes(f.read())


def verify_hash(data: bytes, expected_hash: str) -> bool:
    """
    Verify that data matches expected hash.
    
    Args:
        data: Raw bytes to verify.
        expected_hash: Expected hex-encoded hash.
        
    Returns:
        True if hash matches, False otherwise.
    """
    return hash_bytes(data) == expected_hash


# Policy metadata
POLICY_VERSION = "1.0"
POLICY_COUNCIL_APPROVED = True
