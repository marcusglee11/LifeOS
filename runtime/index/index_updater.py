"""
FP-4.x CND-2: Index Updater with Atomic Writes
Updates INDEX files using atomic write pattern and shared detsort.
"""
import os
import re
from typing import List, Optional, Set
from pathlib import Path

from runtime.util.atomic_write import atomic_write_text
from runtime.util.detsort import detsort_paths


class IndexUpdater:
    """
    Maintains INDEX files with atomic write operations.
    
    Uses shared detsort utilities for deterministic ordering.
    """
    
    def __init__(self, index_path: str, root_dir: str):
        """
        Initialize Index Updater.
        
        Args:
            index_path: Path to the INDEX file.
            root_dir: Root directory to scan.
        """
        self.index_path = Path(index_path)
        self.root_dir = Path(root_dir).resolve()
    
    def scan_directory(self, extensions: Optional[List[str]] = None) -> List[str]:
        """
        Scan directory for files to index.
        
        Args:
            extensions: Extensions to include (default: ['.md']).
            
        Returns:
            Deterministically sorted list of relative paths.
        """
        if extensions is None:
            extensions = ['.md']
        
        files = []
        index_name = self.index_path.name
        
        for root, dirs, filenames in os.walk(self.root_dir):
            # Sort dirs in-place for deterministic traversal
            dirs.sort()
            
            for fname in sorted(filenames):
                # Skip index file itself
                if fname == index_name:
                    continue
                
                if any(fname.endswith(ext) for ext in extensions):
                    full_path = Path(root) / fname
                    rel_path = full_path.relative_to(self.root_dir)
                    # Normalize separators
                    files.append(str(rel_path).replace('\\', '/'))
        
        return detsort_paths(files)
    
    def generate_content(
        self,
        title: str = "Index",
        extensions: Optional[List[str]] = None
    ) -> str:
        """
        Generate INDEX file content.
        
        Args:
            title: Title for the index.
            extensions: Extensions to include.
            
        Returns:
            Markdown content for the INDEX.
        """
        files = self.scan_directory(extensions)
        
        lines = [f"# {title}", ""]
        for f in files:
            lines.append(f"- [{f}](./{f})")
        lines.append("")
        
        return "\n".join(lines)
    
    def update(
        self,
        title: str = "Index",
        extensions: Optional[List[str]] = None
    ) -> bool:
        """
        Update INDEX file atomically.
        
        Args:
            title: Title for the index.
            extensions: Extensions to include.
            
        Returns:
            True if INDEX was updated, False if no changes needed.
        """
        new_content = self.generate_content(title, extensions)
        
        # Check if update needed
        if self.index_path.exists():
            with open(self.index_path, 'r', encoding='utf-8') as f:
                existing = f.read()
            if existing == new_content:
                return False
        
        # Atomic write
        atomic_write_text(self.index_path, new_content)
        return True
    
    def verify_coherence(self) -> tuple[bool, List[str], List[str]]:
        """
        Verify INDEX matches directory contents.
        
        Returns:
            Tuple of (is_coherent, missing_from_index, orphaned_in_index).
        """
        actual_files = set(self.scan_directory())
        indexed_files: Set[str] = set()
        
        if self.index_path.exists():
            with open(self.index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract paths from markdown links
            pattern = r'\[([^\]]+)\]\(\./([^\)]+)\)'
            for match in re.finditer(pattern, content):
                indexed_files.add(match.group(2))
        
        missing = sorted(actual_files - indexed_files)
        orphaned = sorted(indexed_files - actual_files)
        
        return (len(missing) == 0 and len(orphaned) == 0, missing, orphaned)
