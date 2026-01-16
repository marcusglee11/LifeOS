"""
Envelope Enforcer - Path containment and access validation.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §5.2.1
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ValidationResult:
    """Result of envelope validation. Per spec §5.2.1."""
    allowed: bool
    reason: str
    evidence: Dict[str, Any] = field(default_factory=dict)


class EnvelopeViolation(Exception):
    """Envelope constraint violated."""
    def __init__(self, result: ValidationResult):
        self.result = result
        super().__init__(result.reason)


class EnvelopeEnforcer:
    """
    Enforce envelope constraints for operations.
    
    Per spec §5.2.1:
    1. realpath_containment: Path must be within repo_root
    2. symlink_rejection: Reject symlinks if configured
    3. allowlist_match: Path must match allowed patterns
    4. denylist_exclusion: Path must not match denied patterns
    5. toctou_mitigation: Re-validate before execution
    """
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root.resolve()
    
    def validate_path_access(
        self,
        requested_path: str,
        operation: str,
        allowed_paths: List[str],
        denied_paths: List[str],
        reject_symlinks: bool = True
    ) -> ValidationResult:
        """
        Validate path access against envelope constraints.
        
        Per spec §5.2.1.
        """
        evidence = {
            "requested_path": requested_path,
            "operation": operation,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Normalize the path
        path = Path(requested_path)
        if not path.is_absolute():
            path = self.repo_root / path
        
        # 1. Realpath containment
        try:
            real_path = path.resolve()
        except (OSError, ValueError) as e:
            return ValidationResult(
                allowed=False,
                reason=f"Path resolution failed: {e}",
                evidence={**evidence, "error": str(e)},
            )
        
        evidence["real_path"] = str(real_path)
        
        try:
            real_path.relative_to(self.repo_root)
        except ValueError:
            return ValidationResult(
                allowed=False,
                reason=f"Path escapes repo root: {real_path}",
                evidence={**evidence, "repo_root": str(self.repo_root)},
            )
        
        # 2. Symlink rejection
        if reject_symlinks and self._has_symlink_in_path(path):
            return ValidationResult(
                allowed=False,
                reason=f"Symlink detected in path: {requested_path}",
                evidence={**evidence, "symlink_rejected": True},
            )
        
        # 3. Compute relative path for pattern matching
        try:
            rel_path = real_path.relative_to(self.repo_root)
            rel_path_str = str(rel_path).replace("\\", "/")
        except ValueError:
            rel_path_str = requested_path.replace("\\", "/")
        
        evidence["relative_path"] = rel_path_str
        
        # 4. Denylist exclusion (check first - deny takes precedence)
        for pattern in denied_paths:
            if self._matches_pattern(rel_path_str, pattern):
                return ValidationResult(
                    allowed=False,
                    reason=f"Path matches denied pattern: {pattern}",
                    evidence={**evidence, "denied_pattern": pattern},
                )
        
        # 5. Allowlist match
        if allowed_paths:
            matched = False
            for pattern in allowed_paths:
                if self._matches_pattern(rel_path_str, pattern):
                    matched = True
                    evidence["allowed_pattern"] = pattern
                    break
            
            if not matched:
                return ValidationResult(
                    allowed=False,
                    reason=f"Path does not match any allowed pattern",
                    evidence={**evidence, "allowed_patterns": allowed_paths},
                )
        
        return ValidationResult(
            allowed=True,
            reason="Access permitted",
            evidence=evidence,
        )
    
    def _has_symlink_in_path(self, path: Path) -> bool:
        """Check if any component of path is a symlink."""
        current = path
        checked = set()
        
        while current != current.parent:
            if str(current) in checked:
                break
            checked.add(str(current))
            
            if current.is_symlink():
                return True
            current = current.parent
        
        return path.is_symlink()
    
    def _matches_pattern(self, path: str, pattern: str) -> bool:
        """
        Match path against glob pattern.
        
        Supports:
        - * matches single directory level
        - ** matches multiple directory levels
        - ? matches single character
        """
        # Normalize both
        path = path.replace("\\", "/")
        pattern = pattern.replace("\\", "/")
        
        # Handle ** patterns
        if "**" in pattern:
            # Convert ** to fnmatch-compatible pattern
            # ** means "any number of directories"
            parts = pattern.split("**")
            regex_pattern = "*".join(parts)
            return fnmatch.fnmatch(path, regex_pattern)
        
        return fnmatch.fnmatch(path, pattern)
    
    def check_symlink_safety(self, path: str) -> bool:
        """
        Check if path is safe from symlink attacks.
        
        Per spec §5.2.1:
        1. Check if path itself is a symlink
        2. Check if any component of path is a symlink
        3. Verify realpath is within allowed root
        """
        p = Path(path)
        if not p.is_absolute():
            p = self.repo_root / p
        
        # Check for symlinks
        if self._has_symlink_in_path(p):
            return False
        
        # Check realpath containment
        try:
            real = p.resolve()
            real.relative_to(self.repo_root)
            return True
        except ValueError:
            return False


def validate_path_access(
    requested_path: str,
    operation: str,
    envelope: Dict[str, Any],
    repo_root: Path
) -> ValidationResult:
    """
    Convenience function for path validation.
    
    Per spec §5.2.1.
    """
    enforcer = EnvelopeEnforcer(repo_root)
    return enforcer.validate_path_access(
        requested_path=requested_path,
        operation=operation,
        allowed_paths=envelope.get("allowed_paths", []),
        denied_paths=envelope.get("denied_paths", []),
        reject_symlinks=envelope.get("reject_symlinks", True),
    )
