"""
Self-Modification Protection - Prevent agents from modifying governance surfaces.

Per LifeOS_Autonomous_Build_Loop_Architecture_v0.3.md §2.4 and §5.5
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class ValidationResult:
    """Result of self-modification check."""
    allowed: bool
    reason: str
    evidence: Dict[str, Any] = field(default_factory=dict)


# Per spec §2.4 and §5.5: Hardcoded protected paths
# These CANNOT be modified by any agent regardless of mission instructions
PROTECTED_PATHS = [
    # Role prompts
    "config/agent_roles/*",
    # Model mapping
    "config/models.yaml",
    # Governance baseline (integrity manifest)
    "config/governance_baseline.yaml",
    # Envelope policy
    "scripts/opencode_gate_policy.py",
    # Packet transforms
    "runtime/orchestration/transforms/*",
    # This file itself (self-mod protection)
    "runtime/governance/self_mod_protection.py",
    # Architecture documents
    "docs/03_runtime/LifeOS_Autonomous_Build_Loop_Architecture_*.md",
    # Agent constitutions
    "GEMINI.md",
    "CLAUDE.md",
]


def is_protected(path: str) -> bool:
    """
    Check if path is a protected governance surface.
    
    Per spec §2.4: These protections are hardcoded and cannot be overridden.
    """
    # Normalize to forward slashes
    norm_path = path.replace("\\", "/")
    
    # Remove leading ./ if present
    if norm_path.startswith("./"):
        norm_path = norm_path[2:]
    
    for pattern in PROTECTED_PATHS:
        if fnmatch.fnmatch(norm_path, pattern):
            return True
    
    return False


def check_self_modification(
    path: str,
    agent_role: str,
    operation: str = "modify"
) -> ValidationResult:
    """
    Check if agent is allowed to modify the path.
    
    Per spec §2.4:
    - Builder/Steward agents CANNOT modify any artifact in §2.3
    - No agent may modify its own envelope definition
    - No agent may modify governance_baseline.yaml
    
    Returns ValidationResult with allowed=False if modification is blocked.
    """
    evidence = {
        "path": path,
        "agent_role": agent_role,
        "operation": operation,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Check if path is protected
    if is_protected(path):
        return ValidationResult(
            allowed=False,
            reason=f"Path is a protected governance surface: {path}",
            evidence={
                **evidence,
                "protection_rule": "hardcoded_denylist",
                "matching_patterns": [p for p in PROTECTED_PATHS if fnmatch.fnmatch(path.replace("\\", "/"), p)],
            },
        )
    
    # Role-specific restrictions could be added here
    # For now, if not in PROTECTED_PATHS, allow
    
    return ValidationResult(
        allowed=True,
        reason="Path is not a protected governance surface",
        evidence=evidence,
    )


def get_protected_paths() -> List[str]:
    """Return list of protected path patterns."""
    return list(PROTECTED_PATHS)


class SelfModProtector:
    """
    Enforcer for self-modification protection.
    
    Per spec §2.4: Checked BEFORE any filesystem or git operation.
    """
    
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
    
    def validate(
        self,
        path: str,
        agent_role: str,
        operation: str = "modify"
    ) -> ValidationResult:
        """
        Validate that operation is allowed on path.
        
        Raises no exception - returns ValidationResult.
        Caller must check allowed=False and escalate.
        """
        # Normalize path relative to repo root
        p = Path(path)
        if p.is_absolute():
            try:
                rel_path = p.relative_to(self.repo_root)
            except ValueError:
                # Path outside repo - not our concern
                return ValidationResult(
                    allowed=True,
                    reason="Path outside repository",
                    evidence={"path": path, "repo_root": str(self.repo_root)},
                )
        else:
            rel_path = p
        
        return check_self_modification(
            path=str(rel_path).replace("\\", "/"),
            agent_role=agent_role,
            operation=operation,
        )
