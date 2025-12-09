import os
import shutil
import sys
from pathlib import Path

# Validated Source Root
SOURCE_ROOT = Path(r"c:\Users\cabra\Projects\COOProject\coo-agent")
SOURCE_RUNTIME = SOURCE_ROOT / "coo_runtime" / "runtime"
SOURCE_TESTS = SOURCE_ROOT / "coo_runtime" / "tests"

TARGET_BASE = Path(r"c:\Users\cabra\Projects\LifeOS\runtime")
TARGET_TESTS = TARGET_BASE / "tests"

# Map: Source Filename -> Target Filename
FILE_MAPPING = {
    "state_machine.py": "engine.py",  # The FSM is the Engine
    "freeze.py": "freeze.py",
    "gates.py": "gates.py", 
    "rollback.py": "rollback.py",
    "migration.py": "migration.py",
    "lint_engine.py": "lint_engine.py",
    "amendment_engine.py": "amendment_engine.py",
    "__init__.py": "__init__.py"
}

def copy_runtime():
    if not SOURCE_RUNTIME.exists():
        print(f"ERROR: Source directory not found: {SOURCE_RUNTIME}")
        return

    if not TARGET_BASE.exists():
        print(f"Creating target directory: {TARGET_BASE}")
        TARGET_BASE.mkdir(parents=True, exist_ok=True)

    print(f"--- Porting Runtime Code ---")
    for src_name, dst_name in FILE_MAPPING.items():
        src = SOURCE_RUNTIME / src_name
        dst = TARGET_BASE / dst_name
        
        if src.exists():
            print(f"Copying {src_name} -> {dst_name}")
            shutil.copy2(src, dst)
        else:
            print(f"Warning: Source file missing: {src_name}")

def copy_tests():
    if not SOURCE_TESTS.exists():
        print(f"Warning: Tests source not found: {SOURCE_TESTS}")
        return

    if not TARGET_TESTS.exists():
        TARGET_TESTS.mkdir(parents=True, exist_ok=True)

    print(f"--- Porting Tests ---")
    for item in SOURCE_TESTS.glob("test_*.py"):
        dst = TARGET_TESTS / item.name
        print(f"Copying test: {item.name}")
        shutil.copy2(item, dst)

if __name__ == "__main__":
    copy_runtime()
    copy_tests()
    print("\nDone. Please check LifeOS/runtime/")
