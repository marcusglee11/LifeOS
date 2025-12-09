import os
from .planner import Task
from typing import Optional, List

class Builder:
    """
    Builder for recursive kernel tasks.
    
    H-004: Explicitly accepts repo_root to eliminate cwd dependence.
    Only handles docs index rebuilding in this pass.
    """
    
    def __init__(self, repo_root: str):
        """
        Initialize the Builder.
        
        Args:
            repo_root: Absolute path to the repository root.
        """
        self.repo_root = repo_root
    
    def build(self, task: Task) -> bool:
        """
        Execute a build task.
        
        H-004: Only docs domain is supported in this pass.
        """
        if task.domain == "docs" and task.type == "rebuild_index":
            return self._rebuild_docs_index()
        # H-004: config, artifacts, daily_summary are out of scope
        return False

    def _rebuild_docs_index(self, exclude_paths: Optional[List[str]] = None) -> bool:
        """
        Rebuild the docs/INDEX_v1.1.md file.
        
        H-004 Invariants:
        - Only .md files are indexed
        - INDEX_v1.1.md itself is excluded
        - Paths are relative from docs/, normalized to /
        - List is sorted lexicographically
        
        Args:
            exclude_paths: Optional list of relative paths to exclude (future extension).
        
        Returns:
            True if successful, False otherwise.
        """
        if exclude_paths is None:
            exclude_paths = []
        
        docs_root = os.path.join(self.repo_root, "docs")
        index_filename = "INDEX_v1.1.md"
        index_path = os.path.join(docs_root, index_filename)
        
        if not os.path.exists(docs_root):
            return False

        files_to_index = []
        for root, dirs, files in os.walk(docs_root):
            for file in files:
                # H-004: Only .md files, excluding the index itself
                if file.endswith(".md") and file != index_filename:
                    rel_path = os.path.relpath(os.path.join(root, file), docs_root).replace('\\', '/')
                    
                    # Check exclude_paths (extension point for future use)
                    excluded = any(rel_path.startswith(ep) for ep in exclude_paths)
                    if not excluded:
                        files_to_index.append(rel_path)
        
        # H-004: Deterministic sort
        files_to_index.sort()
        
        # H-004: v1.1 format
        content = "# Documentation Index v1.1\n\n"
        for f in files_to_index:
            content += f"- [{f}](./{f})\n"
            
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return True
