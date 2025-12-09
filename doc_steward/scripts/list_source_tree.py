import os
from pathlib import Path

ROOT = Path(r"c:\Users\cabra\Projects\COOProject")

IGNORE = {".git", ".vscode", "venv", ".venv", "__pycache__", "node_modules", "site-packages"}

def print_tree(dir_path, prefix=""):
    try:
        entries = sorted(os.listdir(dir_path))
    except PermissionError:
        return

    for entry in entries:
        if entry in IGNORE:
            continue
            
        full_path = dir_path / entry
        if full_path.is_dir():
            print(f"{prefix}[{entry}]")
            print_tree(full_path, prefix + "  ")
        elif full_path.suffix == ".py":
             print(f"{prefix}{entry}")

if __name__ == "__main__":
    print(f"Scanning {ROOT}...")
    print_tree(ROOT)
