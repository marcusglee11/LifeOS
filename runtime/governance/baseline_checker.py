"""
Governance Baseline Checker - Verify governance surfaces against baseline.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §2.5
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


# Baseline path per v0.3 spec §2.5
GOVERNANCE_BASELINE_PATH = "config/governance_baseline.yaml"


class BaselineMissingError(Exception):
    """
    Raised when governance baseline file does not exist.
    
    Per v0.3 spec §2.5.3: If baseline missing => HALT, requires CEO ceremony.
    """
    
    def __init__(self, expected_path: str):
        self.expected_path = expected_path
        super().__init__(
            f"Governance baseline missing: {expected_path}\n"
            "This file must be created via the CEO-authorised Governance "
            "Baseline Ceremony (see spec §2.5.1). Auto-creation is forbidden."
        )


@dataclass
class MismatchRecord:
    """Record of a single file mismatch."""
    
    path: str
    expected_hash: str
    actual_hash: str


class BaselineMismatchError(Exception):
    """
    Raised when governance surfaces do not match baseline hashes.
    
    Per v0.3 spec §2.5.3: If mismatch => HALT + escalate.
    The orchestrator MUST NEVER auto-update the governance baseline.
    """
    
    def __init__(self, mismatches: list[MismatchRecord]):
        self.mismatches = mismatches
        # [v0.3 Audit-Grade]: Full SHA256 hashes, no truncation
        mismatch_details = "\n".join(
            f"  - {m.path}:\n      expected: {m.expected_hash}\n      actual:   {m.actual_hash}"
            for m in mismatches
        )
        super().__init__(
            f"Governance baseline mismatch detected:\n{mismatch_details}\n"
            "Resolution requires CEO action:\n"
            "  Option A: Revert unauthorized changes\n"
            "  Option B: Authorize changes via Council review + update baseline per §2.5.2"
        )


@dataclass
class BaselineManifest:
    """Parsed governance baseline per v0.3 spec §2.5."""
    
    baseline_version: str
    approved_by: str
    council_ruling_ref: Optional[str]
    hash_algorithm: str
    path_normalization: str
    artifacts: list[dict] = field(default_factory=list)


def _compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of file contents."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _load_baseline(baseline_path: Path) -> BaselineManifest:
    """Load and parse the governance baseline YAML."""
    with open(baseline_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    
    return BaselineManifest(
        baseline_version=data.get("baseline_version", ""),
        approved_by=data.get("approved_by", ""),
        council_ruling_ref=data.get("council_ruling_ref"),
        hash_algorithm=data.get("hash_algorithm", "SHA-256"),
        path_normalization=data.get("path_normalization", "relpath_from_repo_root"),
        artifacts=data.get("artifacts", []),
    )


def verify_governance_baseline(
    repo_root: Optional[Path] = None,
) -> BaselineManifest:
    """
    Verify governance surfaces against baseline.
    
    Per v0.3 spec §2.5.3:
    - If baseline missing => raise BaselineMissingError
    - If any surface hash mismatch => raise BaselineMismatchError
    - If all match => return the manifest
    
    This function NEVER auto-updates the baseline.
    This function NEVER proceeds if there's a mismatch.
    """
    if repo_root is None:
        repo_root = Path.cwd()
    
    baseline_path = repo_root / GOVERNANCE_BASELINE_PATH
    
    # Check baseline exists
    if not baseline_path.exists():
        raise BaselineMissingError(str(baseline_path))
    
    # Load baseline
    manifest = _load_baseline(baseline_path)
    
    # Verify each artifact
    mismatches: list[MismatchRecord] = []
    
    for artifact in manifest.artifacts:
        rel_path = artifact.get("path", "")
        expected_hash = artifact.get("sha256", "")
        
        if not rel_path or not expected_hash:
            continue
        
        full_path = repo_root / rel_path
        
        if not full_path.exists():
            # Missing file is a mismatch
            mismatches.append(MismatchRecord(
                path=rel_path,
                expected_hash=expected_hash,
                actual_hash="FILE_NOT_FOUND",
            ))
            continue
        
        actual_hash = _compute_file_hash(full_path)
        
        if actual_hash != expected_hash:
            mismatches.append(MismatchRecord(
                path=rel_path,
                expected_hash=expected_hash,
                actual_hash=actual_hash,
            ))
    
    if mismatches:
        raise BaselineMismatchError(mismatches)
    
    return manifest
