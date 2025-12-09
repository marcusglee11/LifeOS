import os
from pathlib import Path

# Search Root
SEARCH_ROOT = Path(r"c:\Users\cabra\Projects\COOProject")

PATTERNS = {"engine.py", "state_store.py", "sign.py", "cli.py"}

def find_files():
    print(f"Searching for {PATTERNS} in {SEARCH_ROOT}...")
    
    found = 0
    for root, dirs, files in os.walk(SEARCH_ROOT):
        # optimization: skip venvs
        if "venv" in dirs:
            dirs.remove("venv")
        if "__pycache__" in dirs:
            dirs.remove("__pycache__")
            
        for f in files:
            if f in PATTERNS:
                full_path = Path(root) / f
                print(f"FOUND: {f} -> {full_path}")
                found += 1
                
    if found == 0:
        print("No files found matching patterns.")

if __name__ == "__main__":
    find_files()
