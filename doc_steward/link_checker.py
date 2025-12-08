import os
import re

def check_links(doc_root: str) -> list[str]:
    errors = []
    doc_root = os.path.abspath(doc_root)
    
    for root, dirs, files in os.walk(doc_root):
        for file in files:
            if not file.endswith('.md'):
                continue
            
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            links = re.findall(r'\[.*?\]\((.*?)\)', content)
            for link in links:
                if link.startswith('http') or link.startswith('file:') or link.startswith('mailto:'):
                    continue
                
                clean_link = link.split('#')[0]
                if not clean_link:
                    continue
                
                # resolve relative
                target_path = os.path.normpath(os.path.join(root, clean_link))
                if not os.path.exists(target_path):
                     errors.append(f"Broken link in {os.path.relpath(filepath, doc_root)}: {link}")
    return errors
