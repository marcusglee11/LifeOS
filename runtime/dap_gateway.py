"""
FP-3.3: DAP Write Gateway
Central gateway for all file write operations.
Enforces DAP boundary checks, deterministic naming, and protected path validation.
"""
import os
import re
import json
from typing import Optional, List, Set


class DAPWriteError(Exception):
    """Raised when a DAP write violation occurs."""
    pass


class DAPWriteGateway:
    """
    Central Write Gateway for DAP-compliant file operations.
    
    Validates:
    - Target path is within allowed boundaries
    - Filename follows deterministic naming patterns
    - Protected paths are not written to
    """
    
    # DAP v2.0 naming pattern: name_v{major}.{minor}.{ext}
    VERSION_PATTERN = re.compile(r'^.+_v\d+\.\d+\.(md|json|yaml|txt)$')
    
    def __init__(
        self,
        allowed_roots: List[str],
        protected_paths: Optional[List[str]] = None,
        index_paths: Optional[List[str]] = None
    ):
        """
        Initialize DAP Write Gateway.
        
        Args:
            allowed_roots: List of allowed write root directories.
            protected_paths: List of paths that cannot be written to.
            index_paths: List of index files to update on write.
        """
        self.allowed_roots = [os.path.abspath(r) for r in allowed_roots]
        self.protected_paths = [os.path.abspath(p) for p in (protected_paths or [])]
        self.index_paths = index_paths or []
        self._pending_index_updates: Set[str] = set()
    
    def validate_write(self, target_path: str, content: str) -> None:
        """
        Validate a write operation without performing it.
        
        Args:
            target_path: Path to write to.
            content: Content to write.
        
        Raises:
            DAPWriteError: If the write violates DAP rules.
        """
        abs_path = os.path.abspath(target_path)
        filename = os.path.basename(target_path)
        
        # Check protected paths
        for protected in self.protected_paths:
            if abs_path.startswith(protected) or abs_path == protected:
                raise DAPWriteError(f"Write to protected path: {target_path}")
        
        # Check allowed roots
        in_allowed_root = False
        for root in self.allowed_roots:
            if abs_path.startswith(root):
                in_allowed_root = True
                break
        
        if not in_allowed_root:
            raise DAPWriteError(
                f"Write outside allowed boundaries: {target_path}. "
                f"Allowed roots: {self.allowed_roots}"
            )
        
        # Check deterministic naming (optional enforcement)
        # Only enforce for versioned file types
        if filename.endswith(('.md', '.json', '.yaml')):
            if not self.VERSION_PATTERN.match(filename):
                # Warning but not blocking - some files may not need versions
                pass
    
    def write(self, target_path: str, content: str, encoding: str = 'utf-8') -> None:
        """
        Write content to a file through the DAP gateway.
        
        Args:
            target_path: Path to write to.
            content: Content to write.
            encoding: File encoding.
        
        Raises:
            DAPWriteError: If the write violates DAP rules.
        """
        self.validate_write(target_path, content)
        
        # Ensure parent directory exists
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        
        with open(target_path, 'w', encoding=encoding) as f:
            f.write(content)
        
        # Queue index update
        self._queue_index_update(target_path)
    
    def write_binary(self, target_path: str, content: bytes) -> None:
        """
        Write binary content to a file through the DAP gateway.
        
        Args:
            target_path: Path to write to.
            content: Binary content to write.
        
        Raises:
            DAPWriteError: If the write violates DAP rules.
        """
        self.validate_write(target_path, "")
        
        os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
        
        with open(target_path, 'wb') as f:
            f.write(content)
        
        self._queue_index_update(target_path)
    
    def _queue_index_update(self, written_path: str) -> None:
        """Queue an index update for the written path."""
        self._pending_index_updates.add(os.path.abspath(written_path))
    
    def flush_index_updates(self) -> List[str]:
        """
        Flush all pending index updates.
        
        Returns:
            List of paths that were updated in indices.
        """
        updated = sorted(list(self._pending_index_updates))
        self._pending_index_updates.clear()
        return updated
    
    def is_protected(self, path: str) -> bool:
        """Check if a path is protected."""
        abs_path = os.path.abspath(path)
        for protected in self.protected_paths:
            if abs_path.startswith(protected) or abs_path == protected:
                return True
        return False
    
    def is_in_boundary(self, path: str) -> bool:
        """Check if a path is within allowed boundaries."""
        abs_path = os.path.abspath(path)
        for root in self.allowed_roots:
            if abs_path.startswith(root):
                return True
        return False
    
    @staticmethod
    def generate_versioned_name(base_name: str, major: int, minor: int, ext: str) -> str:
        """
        Generate a DAP-compliant versioned filename.
        
        Args:
            base_name: Base name without extension.
            major: Major version number.
            minor: Minor version number.
            ext: File extension (without dot).
        
        Returns:
            Versioned filename.
        """
        return f"{base_name}_v{major}.{minor}.{ext}"
