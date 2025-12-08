import os
import re

def check_dap_compliance(doc_root: str) -> list[str]:
    errors = []
    # Pattern: Name_vX.Y.md or Name_vX.Y.Z.md
    # Strict compliance: suffix is mandatory
    
    # Relaxed pattern: _vX, _vX.Y, _vX.Y.Z, case insensitive
    version_pattern = re.compile(r'_[vV]\d+(?:\.\d+)*\.md$')
    
    # Exceptions (legacy files or READMEs if allowed, but Constitution says "All files must contain version suffixes... unless... dir structure")
    # For this pass, we will report everything that doesn't match.
    
    for root, dirs, files in os.walk(doc_root):
        for file in files:
            if not file.endswith('.md'):
                continue
                
            # Skip README.md if it's considered special? Constitution says "All files...".
            # But let's check strictness.
            if not version_pattern.search(file):
                 errors.append(f"DAP violation (no version suffix): {file}")
            
            if ' ' in file:
                 errors.append(f"DAP violation (spaces in name): {file}")

    return errors
