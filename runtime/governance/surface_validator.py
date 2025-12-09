"""
FP-4.x CND-3: Governance Surface Validator
Validates governance surfaces against manifest for immutability.
"""
import json
import os
from typing import List, Tuple
from pathlib import Path

from runtime.governance.HASH_POLICY_v1 import hash_file, hash_json


class GovernanceSurfaceError(Exception):
    """Raised when governance surface validation fails."""
    pass


def load_manifest(manifest_path: str) -> dict:
    """Load the governance surface manifest."""
    with open(manifest_path, 'r') as f:
        return json.load(f)


def validate_governance_surfaces(
    repo_root: str,
    manifest_path: str
) -> Tuple[bool, List[str]]:
    """
    Validate all governance surfaces against their manifest hashes.
    
    Args:
        repo_root: Path to repository root.
        manifest_path: Path to surface_manifest.json.
        
    Returns:
        Tuple of (is_valid, list of error messages).
    """
    errors = []
    manifest = load_manifest(manifest_path)
    
    for surface in manifest.get("surfaces", []):
        surface_path = Path(repo_root) / surface["path"]
        
        # Check existence
        if not surface_path.exists():
            errors.append(f"Missing governance surface: {surface['path']}")
            continue
        
        # If hash is specified in manifest, verify it
        if "hash" in surface:
            actual_hash = hash_file(str(surface_path))
            if actual_hash != surface["hash"]:
                errors.append(
                    f"Governance surface tampered: {surface['path']}. "
                    f"Expected {surface['hash']}, got {actual_hash}"
                )
    
    return (len(errors) == 0, errors)


def generate_manifest_signature(manifest_path: str) -> str:
    """
    Generate signature (hash) for the manifest itself.
    
    Args:
        manifest_path: Path to the manifest file.
        
    Returns:
        SHA-256 hash of the manifest file.
    """
    return hash_file(manifest_path)


def verify_manifest_signature(
    manifest_path: str,
    signature_path: str
) -> bool:
    """
    Verify manifest against its signature.
    
    Args:
        manifest_path: Path to surface_manifest.json.
        signature_path: Path to surface_manifest.sig.
        
    Returns:
        True if signature is valid.
    """
    if not os.path.exists(signature_path):
        return False
    
    with open(signature_path, 'r') as f:
        expected_sig = f.read().strip()
    
    actual_sig = generate_manifest_signature(manifest_path)
    return actual_sig == expected_sig
