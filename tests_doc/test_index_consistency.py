import pytest
import os
from doc_steward.index_checker import check_index

def test_index_consistency():
    repo_root = os.getcwd() # Assumption: running from root
    docs_root = os.path.join(repo_root, "docs")
    index_path = os.path.join(docs_root, "INDEX_v1.1.md")
    
    if not os.path.exists(index_path):
        pytest.skip(f"Index file not found at {index_path}")
        
    errors = check_index(docs_root, index_path)
    
    # If there are errors, fail with list
    assert not errors, f"Index consistency errors found: {errors}"
