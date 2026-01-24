"""
Waiver Artifact Boundary - Deterministic waiver grant storage and validation.

Per Agent Instruction Block - provides:
- WaiverGrant dataclass for waiver representation
- write() to persist waiver grants to disk
- read() to load and validate waiver grants
- is_valid() to check if waiver exists and is not expired
- get_waiver_path() for deterministic artifact path derivation

Fail-closed invariant: Any parse/validation/expiry error => waiver NOT valid.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional


# Canonical waiver artifact directory (mirrors escalation pattern)
WAIVER_ARTIFACT_DIR = Path("artifacts/waivers/Policy_Engine")


class WaiverValidationError(ValueError):
    """Raised when waiver artifact fails validation."""
    pass


@dataclass
class WaiverGrant:
    """
    Represents a waiver grant artifact.
    
    All fields are required for a valid waiver.
    """
    schema_version: str
    waiver_id: str
    granted_by: str
    granted_at: str  # ISO-8601 UTC
    ttl_seconds: int
    expires_at: str  # ISO-8601 UTC
    reason: str
    context: Dict[str, Any]
    
    SCHEMA_VERSION = "1.0"
    
    @classmethod
    def create(
        cls,
        granted_by: str,
        reason: str,
        context: Dict[str, Any],
        ttl_seconds: int = 3600,
        now: Optional[datetime] = None
    ) -> "WaiverGrant":
        """
        Create a new waiver grant with deterministic fields.
        
        Args:
            granted_by: Authority granting the waiver (e.g., "CEO")
            reason: Human-readable reason for the waiver
            context: Binding context (failure_class, file paths, etc.)
            ttl_seconds: Time-to-live in seconds
            now: Optional fixed datetime for deterministic testing
        
        Returns:
            WaiverGrant instance
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        # Ensure now is timezone-aware
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        
        # Compute deterministic waiver_id from context
        context_str = json.dumps(context, sort_keys=True)
        waiver_id = hashlib.sha256(context_str.encode()).hexdigest()[:16]
        
        granted_at = now.isoformat()
        expires_at = (now + timedelta(seconds=ttl_seconds)).isoformat()
        
        return cls(
            schema_version=cls.SCHEMA_VERSION,
            waiver_id=waiver_id,
            granted_by=granted_by,
            granted_at=granted_at,
            ttl_seconds=ttl_seconds,
            expires_at=expires_at,
            reason=reason,
            context=context
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


def get_waiver_path(context: Dict[str, Any], base_dir: Optional[Path] = None) -> Path:
    """
    Derive deterministic waiver artifact path from context.
    
    The filename is derived from a hash of the context, ensuring
    the same context always maps to the same file.
    
    Args:
        context: Binding context dict
        base_dir: Optional override for artifact directory
    
    Returns:
        Path to the waiver artifact file
    """
    if base_dir is None:
        base_dir = WAIVER_ARTIFACT_DIR
    
    context_str = json.dumps(context, sort_keys=True)
    waiver_id = hashlib.sha256(context_str.encode()).hexdigest()[:16]
    
    return base_dir / f"WAIVER_{waiver_id}.json"


def write(artifact_path: Path, grant: WaiverGrant) -> None:
    """
    Write a waiver grant artifact to disk.
    
    Args:
        artifact_path: Path to write the artifact
        grant: WaiverGrant to persist
    
    The file is written with stable key ordering and newline termination.
    Parent directories are created if they don't exist.
    """
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    
    content = json.dumps(grant.to_dict(), sort_keys=True, indent=2)
    artifact_path.write_text(content + "\n", encoding="utf-8")


def read(artifact_path: Path) -> WaiverGrant:
    """
    Read and validate a waiver grant artifact from disk.
    
    Args:
        artifact_path: Path to the artifact file
    
    Returns:
        Validated WaiverGrant instance
    
    Raises:
        WaiverValidationError: If file is missing, unreadable, or invalid
    """
    if not artifact_path.exists():
        raise WaiverValidationError(f"Waiver artifact not found: {artifact_path}")
    
    try:
        content = artifact_path.read_text(encoding="utf-8")
        data = json.loads(content)
    except (OSError, json.JSONDecodeError) as e:
        raise WaiverValidationError(f"Failed to read waiver artifact: {e}")
    
    # Validate required fields
    required_fields = [
        "schema_version", "waiver_id", "granted_by", "granted_at",
        "ttl_seconds", "expires_at", "reason", "context"
    ]
    
    for field in required_fields:
        if field not in data:
            raise WaiverValidationError(f"Missing required field: {field}")
    
    # Validate schema version
    if data["schema_version"] != WaiverGrant.SCHEMA_VERSION:
        raise WaiverValidationError(
            f"Schema version mismatch: expected {WaiverGrant.SCHEMA_VERSION}, "
            f"got {data['schema_version']}"
        )
    
    # Validate types
    if not isinstance(data["ttl_seconds"], int):
        raise WaiverValidationError("ttl_seconds must be an integer")
    
    if not isinstance(data["context"], dict):
        raise WaiverValidationError("context must be a dict")
    
    return WaiverGrant(
        schema_version=data["schema_version"],
        waiver_id=data["waiver_id"],
        granted_by=data["granted_by"],
        granted_at=data["granted_at"],
        ttl_seconds=data["ttl_seconds"],
        expires_at=data["expires_at"],
        reason=data["reason"],
        context=data["context"]
    )


def is_valid(
    artifact_path: Path,
    context: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None
) -> bool:
    """
    Check if a waiver artifact exists, is valid, and has not expired.
    
    Fail-closed: Returns False for any error condition.
    
    Args:
        artifact_path: Path to the waiver artifact
        context: Optional context to verify binding (if provided, must match)
        now: Optional fixed datetime for deterministic testing
    
    Returns:
        True if waiver is valid and not expired, False otherwise
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Ensure now is timezone-aware
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    try:
        grant = read(artifact_path)
    except WaiverValidationError:
        return False
    
    # Check expiration
    try:
        expires_at = datetime.fromisoformat(grant.expires_at)
        # Handle timezone-naive expires_at by assuming UTC
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if now >= expires_at:
            return False  # Expired
    except (ValueError, TypeError):
        return False  # Invalid date format
    
    # Verify context binding if provided
    if context is not None:
        # Context must match (critical for security)
        context_str = json.dumps(context, sort_keys=True)
        expected_id = hashlib.sha256(context_str.encode()).hexdigest()[:16]
        
        if grant.waiver_id != expected_id:
            return False  # Context mismatch
    
    return True


def check_waiver_for_context(
    context: Dict[str, Any],
    now: Optional[datetime] = None,
    base_dir: Optional[Path] = None
) -> bool:
    """
    Convenience function to check if a valid waiver exists for a context.
    
    Args:
        context: Binding context dict
        now: Optional fixed datetime for deterministic testing
        base_dir: Optional override for artifact directory
    
    Returns:
        True if valid waiver exists, False otherwise
    """
    artifact_path = get_waiver_path(context, base_dir)
    return is_valid(artifact_path, context=context, now=now)
