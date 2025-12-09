import os
from pathlib import Path

# Define the root of the docs directory relative to this script
# Assuming script is in LifeOS/docs/auto_index.py
DOCS_DIR = Path(__file__).parent.resolve()
OUTPUT_FILE = DOCS_DIR / "INDEX_GENERATED.md"

EXTENSIONS = {".md"}
EXCLUDED_DIRS = {".git", "__pycache__", ".vscode", "venv"}
EXCLUDED_FILES = {"INDEX_GENERATED.md", "GEMINI.md"}

def get_file_title(file_path):
    """Extracts the H1 title from a markdown file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("# "):
                    return line.strip("# ").strip()
    except Exception:
        pass
    return file_path.name

def generate_index():
    print(f"Scanning {DOCS_DIR}...")
    
    index_lines = ["# LifeOS Documentation Index (Auto-Generated)\n"]
    index_lines.append("> [!NOTE]")
    index_lines.append("> This file is automatically maintained by `auto_index.py`. Do not edit manually.\n")
    
    # Walk the directory
    for root, dirs, files in os.walk(DOCS_DIR):
        # Modify dirs in-place to skip excluded and sort
        dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
        dirs.sort()
        files.sort()
        
        root_path = Path(root)
        rel_path = root_path.relative_to(DOCS_DIR)
        
        # Calculate indentation level (0 for root, 1 for subdirs, etc.)
        level = len(rel_path.parts)
        if rel_path == Path("."):
            level = 0
            
        indent = "  " * level
        
        # exact folder name
        if level > 0:
            folder_name = rel_path.parts[-1]
            index_lines.append(f"{indent}- **{folder_name}/**")
            
        # Process files
        file_indent = "  " * (level + (1 if level > 0 else 0))
        
        for filename in files:
            if filename in EXCLUDED_FILES:
                continue
                
            file_path = root_path / filename
            if file_path.suffix not in EXTENSIONS:
                continue
                
            title = get_file_title(file_path)
            
            # Create relative link (always forward slashes for markdown)
            link_path = os.path.relpath(file_path, DOCS_DIR).replace("\\", "/")
            
            index_lines.append(f"{file_indent}- [{title}]({link_path})")

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))
        
    print(f"Successfully generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_index()
