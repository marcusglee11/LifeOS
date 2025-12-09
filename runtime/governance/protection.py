"""
FP-3.9: Governance Protections & Autonomy Ceilings
Enforces protected artefact registry and autonomy constraints.
"""
import os
import json
from typing import List, Optional, Set, Dict, Any
from dataclasses import dataclass


class GovernanceProtectionError(Exception):
    """Raised when a governance protection is violated."""
    pass


@dataclass
class AutonomyCeiling:
    """Defines autonomy limits for an operation."""
    max_files_modified: int = 40
    max_directories_modified: int = 6
    allow_new_modules: bool = True
    allow_new_tests: bool = True
    allow_doc_updates: bool = True
    prohibit_protected_paths: bool = True


@dataclass
class OperationScope:
    """Tracks the scope of an operation."""
    files_modified: Set[str]
    directories_modified: Set[str]
    protected_violations: List[str]
    
    @property
    def file_count(self) -> int:
        return len(self.files_modified)
    
    @property
    def directory_count(self) -> int:
        return len(self.directories_modified)


class GovernanceProtector:
    """
    Enforces governance protections and autonomy ceilings.
    
    Provides:
    - Protected artefact registry enforcement
    - Read-only path protection
    - Autonomy ceiling validation
    """
    
    def __init__(self, registry_path: Optional[str] = None):
        """
        Initialize Governance Protector.
        
        Args:
            registry_path: Path to protected_artefacts.json.
        """
        self.registry_path = registry_path
        self._protected_paths: List[str] = []
        self._autonomy_ceiling = AutonomyCeiling()
        
        if registry_path and os.path.exists(registry_path):
            self._load_registry(registry_path)
    
    def _load_registry(self, path: str) -> None:
        """Load protected artefacts registry."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self._protected_paths = data.get('protected_paths', [])
    
    def add_protected_path(self, path: str) -> None:
        """Add a path to the protected list."""
        if path not in self._protected_paths:
            self._protected_paths.append(path)
    
    def remove_protected_path(self, path: str) -> None:
        """Remove a path from the protected list."""
        if path in self._protected_paths:
            self._protected_paths.remove(path)
    
    def is_protected(self, path: str) -> bool:
        """
        Check if a path is protected.
        
        Args:
            path: Path to check.
        
        Returns:
            True if path is protected.
        """
        abs_path = os.path.abspath(path)
        norm_path = os.path.normpath(path)
        
        for protected in self._protected_paths:
            protected_abs = os.path.abspath(protected)
            protected_norm = os.path.normpath(protected)
            
            # Check exact match or if path is under protected directory
            if (abs_path == protected_abs or 
                norm_path == protected_norm or
                abs_path.startswith(protected_abs + os.sep) or
                norm_path.startswith(protected_norm + os.sep)):
                return True
        
        return False
    
    def validate_write(self, path: str) -> None:
        """
        Validate that a write is allowed.
        
        Args:
            path: Path to write to.
        
        Raises:
            GovernanceProtectionError: If path is protected.
        """
        if self.is_protected(path):
            raise GovernanceProtectionError(
                f"Write to protected path prohibited: {path}"
            )
    
    def set_autonomy_ceiling(self, ceiling: AutonomyCeiling) -> None:
        """Set the autonomy ceiling for operations."""
        self._autonomy_ceiling = ceiling
    
    def validate_operation_scope(
        self,
        scope: OperationScope
    ) -> tuple[bool, List[str]]:
        """
        Validate that an operation is within autonomy ceilings.
        
        Args:
            scope: The operation scope to validate.
        
        Returns:
            Tuple of (is_valid, list of violations).
        """
        violations = []
        
        # Check file count
        if scope.file_count > self._autonomy_ceiling.max_files_modified:
            violations.append(
                f"Files modified ({scope.file_count}) exceeds ceiling "
                f"({self._autonomy_ceiling.max_files_modified})"
            )
        
        # Check directory count
        if scope.directory_count > self._autonomy_ceiling.max_directories_modified:
            violations.append(
                f"Directories modified ({scope.directory_count}) exceeds ceiling "
                f"({self._autonomy_ceiling.max_directories_modified})"
            )
        
        # Check protected violations
        if self._autonomy_ceiling.prohibit_protected_paths and scope.protected_violations:
            violations.append(
                f"Protected paths touched: {', '.join(scope.protected_violations)}"
            )
        
        return (len(violations) == 0, violations)
    
    def validate_operation_scope_or_raise(self, scope: OperationScope) -> None:
        """
        Validate operation scope and raise if invalid.
        
        Args:
            scope: The operation scope to validate.
        
        Raises:
            GovernanceProtectionError: If scope exceeds ceilings.
        """
        is_valid, violations = self.validate_operation_scope(scope)
        if not is_valid:
            raise GovernanceProtectionError(
                "Autonomy ceiling violations:\n" + 
                "\n".join(f"  - {v}" for v in violations)
            )
    
    def validate_mission_scope(self, mission: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate a mission's scope against autonomy ceilings.
        
        Args:
            mission: Mission dictionary with 'safety' section.
        
        Returns:
            Tuple of (is_valid, list of violations).
        """
        violations = []
        safety = mission.get('safety', {})
        ceiling = safety.get('autonomy_ceiling', {})
        
        # Check that mission ceiling doesn't exceed our ceiling
        max_files = ceiling.get('max_files_modified', 0)
        if max_files > self._autonomy_ceiling.max_files_modified:
            violations.append(
                f"Mission max_files_modified ({max_files}) exceeds system ceiling "
                f"({self._autonomy_ceiling.max_files_modified})"
            )
        
        max_dirs = ceiling.get('max_directories_modified', 0)
        if max_dirs > self._autonomy_ceiling.max_directories_modified:
            violations.append(
                f"Mission max_directories_modified ({max_dirs}) exceeds system ceiling "
                f"({self._autonomy_ceiling.max_directories_modified})"
            )
        
        return (len(violations) == 0, violations)
    
    def get_protected_paths(self) -> List[str]:
        """Get list of protected paths."""
        return self._protected_paths.copy()
    
    def save_registry(self, path: Optional[str] = None, timestamp: Optional[str] = None) -> None:
        """
        Save the protected artefacts registry.
        
        Args:
            path: Path to save to (defaults to registry_path).
            timestamp: Optional timestamp to record in saved_at.
        """
        save_path = path or self.registry_path
        if not save_path:
            raise ValueError("No registry path specified")
        
        os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
        
        data = {
            "protected_paths": sorted(self._protected_paths),
        }
        
        if timestamp:
            data["saved_at"] = timestamp
        
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
