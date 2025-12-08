import pytest
import os
from doc_steward.link_checker import check_links

def test_link_integrity():
    repo_root = os.getcwd()
    docs_root = os.path.join(repo_root, "docs")
    
    errors = check_links(docs_root)
    
    # Filter known broken links (legacy/WIP)
    ignored_patterns = [
        "COO_Runtime_Deprecation_Notice_v1.0.md"
    ]
    
    real_errors = []
    for e in errors:
        if not any(p in e for p in ignored_patterns):
            real_errors.append(e)
            
    assert not real_errors, f"Broken internal links found: {real_errors}"
