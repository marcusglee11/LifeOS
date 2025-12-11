#!/usr/bin/env python
import os
import shutil
import time

# Configuration
INCLUDE_SUBDIRS = ["docs"]  # add "prompts", "council" later if needed

EXCLUDE_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "build",
    "dist",
    ".idea",
    ".vscode",
    "venv",
    ".venv",
    "node_modules",
}

EXCLUDE_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tmp",
    ".DS_Store",
}


def should_exclude_dir(dirname: str) -> bool:
    return dirname in EXCLUDE_DIR_NAMES


def should_exclude_file(filename: str) -> bool:
    return any(filename.endswith(suffix) for suffix in EXCLUDE_FILE_SUFFIXES)


def sync_directory(src_root: str, dst_root: str, relative_subdir: str) -> None:
    src_dir = os.path.join(src_root, relative_subdir)
    dst_dir = os.path.join(dst_root, relative_subdir)

    if not os.path.isdir(src_dir):
        print(f"[sync_to_brain] Skipping missing source dir: {src_dir}")
        return

    # Walk source and copy/update files
    for current_root, dirnames, filenames in os.walk(src_dir):
        # Filter out excluded dirs in-place
        dirnames[:] = [d for d in dirnames if not should_exclude_dir(d)]

        rel_path = os.path.relpath(current_root, src_root)
        dst_current_root = os.path.join(dst_root, rel_path)

        os.makedirs(dst_current_root, exist_ok=True)

        for filename in filenames:
            if should_exclude_file(filename):
                continue

            src_file = os.path.join(current_root, filename)
            dst_file = os.path.join(dst_current_root, filename)

            if not os.path.exists(dst_file):
                shutil.copy2(src_file, dst_current_root)
                print(f"[sync_to_brain] COPIED  : {src_file} -> {dst_file}")
            else:
                src_mtime = os.path.getmtime(src_file)
                dst_mtime = os.path.getmtime(dst_file)
                # Allow a small buffer for filesystem time resolution differences
                if src_mtime > dst_mtime + 1: 
                    shutil.copy2(src_file, dst_current_root)
                    print(f"[sync_to_brain] UPDATED : {src_file} -> {dst_file}")

    # Clean up files deleted in source (Mirroring)
    for current_root, dirnames, filenames in os.walk(dst_dir, topdown=False):
        rel_path = os.path.relpath(current_root, dst_root)
        src_current_root = os.path.join(src_root, rel_path)

        # Remove files that no longer exist in source
        for filename in filenames:
            dst_file = os.path.join(current_root, filename)
            src_file = os.path.join(src_current_root, filename)
            
            if not os.path.exists(src_file):
                os.remove(dst_file)
                print(f"[sync_to_brain] REMOVED : {dst_file}")

        # Remove empty dirs that no longer exist in source
        if not os.listdir(current_root) and not os.path.exists(src_current_root):
            try:
                os.rmdir(current_root)
                print(f"[sync_to_brain] RMDIR   : {current_root}")
            except OSError:
                pass


def main() -> None:
    # Default paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming we are in docs/scripts/, go up two levels to get to repo root
    default_repo = os.path.abspath(os.path.join(current_dir, "..", ".."))
    
    repo_root = os.environ.get("LIFEOS_REPO_ROOT", default_repo)
    brain_root = os.environ.get("LIFEOS_BRAIN_MIRROR_ROOT", r"G:\My Drive\LifeOS_Mirror")

    if not repo_root or not brain_root:
        raise SystemExit(
            "LIFEOS_REPO_ROOT and LIFEOS_BRAIN_MIRROR_ROOT environment "
            "variables must be set."
        )

    start = time.time()
    print(f"[sync_to_brain] Source repo  : {repo_root}")
    print(f"[sync_to_brain] Brain mirror : {brain_root}")
    
    if not os.path.exists(brain_root):
        print(f"[sync_to_brain] Creating mirror root: {brain_root}")
        os.makedirs(brain_root, exist_ok=True)

    for subdir in INCLUDE_SUBDIRS:
        sync_directory(repo_root, brain_root, subdir)

    elapsed = time.time() - start
    print(f"[sync_to_brain] Completed in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
