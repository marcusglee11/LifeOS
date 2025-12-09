import shutil
import os
from pathlib import Path

ROOT = Path(r"c:\Users\cabra\Projects\LifeOS")
ARCHIVE = ROOT / "scripts" / "archive"

FILES_TO_MOVE = [
    "Create-LifeOSDocsTree.ps1",
    "create_docs_tree.sh",
    "Fix-LifeOSDocs-Missing.ps1",
    "Migrate-LifeOSDocs.ps1",
    "migrate_docs.sh",
    "Phase1_Reversion_Moves.ps1",
    "Phase1_Reversion_Renames.ps1"
]

def archive_files():
    if not ARCHIVE.exists():
        print(f"Creating archive: {ARCHIVE}")
        ARCHIVE.mkdir(parents=True, exist_ok=True)
        
    for f in FILES_TO_MOVE:
        src = ROOT / f
        dst = ARCHIVE / f
        
        if src.exists():
            print(f"Archiving {f}...")
            shutil.move(str(src), str(dst))
        else:
            print(f"Skipping {f} (not found)")

    # Create README in archive
    readme = ARCHIVE / "README.md"
    with open(readme, "w", encoding="utf-8") as f:
        f.write("# Archive\n\nLegacy Phase 1 scaffolding scripts. Referenced for historical context only.\n")

if __name__ == "__main__":
    archive_files()
