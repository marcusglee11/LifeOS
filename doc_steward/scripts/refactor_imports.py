import os
from pathlib import Path

ROOT = Path(r"c:\Users\cabra\Projects\LifeOS")

REPLACEMENTS = {
    # OLD -> NEW
    "from runtime": "from runtime",
    "import runtime": "import runtime",
    "from runtime": "from runtime",
    "import runtime": "import runtime",
    # If project_builder was also namespaced differently, fix it here
    # "from coo.project_builder": "from project_builder"
}

def refactor():
    print(f"Refactoring imports in {ROOT}...")
    count = 0
    
    for root, dirs, files in os.walk(ROOT):
        if "venv" in root or ".git" in root:
            continue
            
        for file in files:
            if file.endswith(".py"):
                path = Path(root) / file
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    
                    new_content = content
                    modified = False
                    for old, new in REPLACEMENTS.items():
                        if old in new_content:
                            new_content = new_content.replace(old, new)
                            modified = True
                            
                    if modified:
                        print(f"Patching: {path}")
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(new_content)
                        count += 1
                except Exception as e:
                    print(f"Error reading {path}: {e}")
                    
    print(f"Refactor complete. Modified {count} files.")

if __name__ == "__main__":
    refactor()
