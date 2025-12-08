import os
from .planner import Task

class Builder:
    def build(self, task: Task) -> bool:
        if task.domain == 'docs' and task.type == 'rebuild_index':
            return self._rebuild_index()
        return False

    def _rebuild_index(self) -> bool:
        repo_root = os.getcwd() # Assume root
        docs_root = os.path.join(repo_root, "docs")
        index_path = os.path.join(docs_root, "INDEX_v1.1.md")
        
        if not os.path.exists(docs_root):
            return False

        files_to_index = []
        for root, dirs, files in os.walk(docs_root):
            for file in files:
                if file.endswith('.md') and file != "INDEX_v1.1.md":
                    # Store relative path
                    rel_path = os.path.relpath(os.path.join(root, file), docs_root).replace('\\', '/')
                    files_to_index.append(rel_path)
        
        files_to_index.sort() # Deterministic
        
        content = "# Documentation Index v1.1\n\n"
        for f in files_to_index:
            content += f"- [{f}](./{f})\n"
            
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return True
