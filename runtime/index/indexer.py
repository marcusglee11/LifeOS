"""
FP-3.3: Index Reconciliation
Automatic index file maintenance for DAP compliance.
"""
import os
import re
from typing import List, Optional, Set
from pathlib import Path


class IndexReconciler:
    """
    Maintains INDEX files in sync with actual file contents.
    
    Scans directories for markdown files and updates INDEX files
    to reflect current state.
    """
    
    def __init__(self, index_path: str, root_dir: str):
        """
        Initialize Index Reconciler.
        
        Args:
            index_path: Path to the INDEX file to maintain.
            root_dir: Root directory to scan for files.
        """
        self.index_path = index_path
        self.root_dir = os.path.abspath(root_dir)
    
    def scan_directory(self, extensions: Optional[List[str]] = None) -> List[str]:
        """
        Scan directory for files to index.
        
        Args:
            extensions: List of extensions to include (default: ['.md'])
        
        Returns:
            Sorted list of relative paths.
        """
        if extensions is None:
            extensions = ['.md']
        
        files = []
        index_basename = os.path.basename(self.index_path)
        for root, _, filenames in os.walk(self.root_dir):
            for fname in filenames:
                # Skip the index file itself
                if fname == index_basename:
                    continue
                if any(fname.endswith(ext) for ext in extensions):
                    full_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(full_path, self.root_dir)
                    # Normalize path separators
                    rel_path = rel_path.replace('\\', '/')
                    files.append(rel_path)
        
        return sorted(files)
    
    def generate_index_content(self, title: str = "Index", extensions: Optional[List[str]] = None) -> str:
        """
        Generate index file content.
        
        Args:
            title: Title for the index.
            extensions: Extensions to include.
        
        Returns:
            Index content as markdown.
        """
        files = self.scan_directory(extensions)
        
        lines = [f"# {title}", ""]
        for f in files:
            lines.append(f"- [{f}](./{f})")
        lines.append("")
        
        return "\n".join(lines)
    
    def reconcile(self, title: str = "Index", extensions: Optional[List[str]] = None) -> bool:
        """
        Reconcile index file with actual directory contents.
        
        Args:
            title: Title for the index.
            extensions: Extensions to include.
        
        Returns:
            True if index was updated, False if no changes needed.
        """
        new_content = self.generate_index_content(title, extensions)
        
        # Check if update needed
        if os.path.exists(self.index_path):
            with open(self.index_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            if existing_content == new_content:
                return False
        
        # Write updated index
        os.makedirs(os.path.dirname(os.path.abspath(self.index_path)), exist_ok=True)
        with open(self.index_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True
    
    def verify_coherence(self) -> tuple[bool, List[str], List[str]]:
        """
        Verify that index matches directory contents.
        
        Returns:
            Tuple of (is_coherent, missing_from_index, orphaned_in_index)
        """
        actual_files = set(self.scan_directory())
        
        # Parse existing index
        indexed_files: Set[str] = set()
        if os.path.exists(self.index_path):
            with open(self.index_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract paths from markdown links
            pattern = r'\[([^\]]+)\]\(\./([^\)]+)\)'
            for match in re.finditer(pattern, content):
                indexed_files.add(match.group(2))
        
        missing = actual_files - indexed_files
        orphaned = indexed_files - actual_files
        
        return (len(missing) == 0 and len(orphaned) == 0,
                sorted(missing),
                sorted(orphaned))
