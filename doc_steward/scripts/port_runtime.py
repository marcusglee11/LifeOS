import os
import shutil
import sys
from pathlib import Path

# Paths (Hardcoded based on exploration)
SOURCE_BASE = Path(r"c:\Users\cabra\Projects\COOProject\coo-agent\coo_runtime\runtime")
SOURCE_TESTS = Path(r"c:\Users\cabra\Projects\COOProject\coo-agent\tests")

TARGET_BASE = Path(r"c:\Users\cabra\Projects\LifeOS\runtime")
TARGET_TESTS = TARGET_BASE / "tests"

FILES_TO_COPY = [
    "engine.py",
    "state_store.py",
    "freeze.py",
    "sign.py",
    "invariants.py",
    "cli.py",
    "transform_state.py",
    "__init__.py"
]

def copy_runtime():
    if not SOURCE_BASE.exists():
        print(f"ERROR: Source directory not found: {SOURCE_BASE}")
        return

    if not TARGET_BASE.exists():
        print(f"Creating target directory: {TARGET_BASE}")
        TARGET_BASE.mkdir(parents=True, exist_ok=True)

    print(f"--- Porting Runtime Code ---")
    for fname in FILES_TO_COPY:
        src = SOURCE_BASE / fname
        dst = TARGET_BASE / fname
        
        if src.exists():
            print(f"Copying {fname}...")
            shutil.copy2(src, dst)
        else:
            print(f"Warning: Source file missing: {fname}")

def copy_tests():
    if not SOURCE_TESTS.exists():
        print(f"Warning: Tests source not found: {SOURCE_TESTS}")
        return

    if not TARGET_TESTS.exists():
        TARGET_TESTS.mkdir(parents=True, exist_ok=True)

    print(f"--- Porting Tests ---")
    # Basic heuristic: Copy files starting with test_
    for item in SOURCE_TESTS.glob("test_*.py"):
        dst = TARGET_TESTS / item.name
        print(f"Copying test: {item.name}")
        shutil.copy2(item, dst)
        
    # Copy conftest.py if exists
    conftest = SOURCE_TESTS / "conftest.py"
    if conftest.exists():
        shutil.copy2(conftest, TARGET_TESTS / "conftest.py")

if __name__ == "__main__":
    copy_runtime()
    copy_tests()
    print("\nDone. Please check LifeOS/runtime/")
