import os
import re

def check_index(doc_root: str, index_path: str) -> list[str]:
    errors = []
    if not os.path.exists(index_path):
        return [f"Index file missing: {index_path}"]
    
    with open(index_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract links from index
    # [Label](path)
    links = re.findall(r'\[.*?\]\((.*?)\)', content)
    indexed_files = set()
    
    # Normalize doc_root
    doc_root = os.path.abspath(doc_root)
    index_dir = os.path.dirname(os.path.abspath(index_path))

    for link in links:
        if link.startswith('http') or link.startswith('file:'):
            continue
            
        # handling anchors #
        clean_link = link.split('#')[0]
        if not clean_link:
            continue
            
        # relative to index location
        abs_path = os.path.normpath(os.path.join(index_dir, clean_link))
        
        if not os.path.exists(abs_path):
            errors.append(f"Indexed file missing: {clean_link}")
        else:
            # check if it is inside doc_root
            if abs_path.startswith(doc_root):
                 # store relative path from doc_root
                rel_path = os.path.relpath(abs_path, doc_root)
                indexed_files.add(rel_path.replace('\\', '/'))

    # Check for unindexed files
    for root, dirs, files in os.walk(doc_root):
        for file in files:
            if not file.endswith('.md'):
                continue
            
            abs_file_path = os.path.join(root, file)
            # Skip the index file itself if it is in doc_root
            if os.path.abspath(abs_file_path) == os.path.abspath(index_path):
                continue

            rel_path = os.path.relpath(abs_file_path, doc_root).replace('\\', '/')
            if rel_path not in indexed_files:
                errors.append(f"Unindexed file: {rel_path}")

    return errors
