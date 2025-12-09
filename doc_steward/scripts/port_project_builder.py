import os
import shutil
import sys
from pathlib import Path

# Paths
SOURCE_PB = Path(r"c:\Users\cabra\Projects\COOProject\coo-agent\project_builder")
TARGET_PB = Path(r"c:\Users\cabra\Projects\LifeOS\project_builder")

def port_project_builder():
    print(f"--- Porting Project Builder ---")
    print(f"Source: {SOURCE_PB}")
    print(f"Target: {TARGET_PB}")

    if not SOURCE_PB.exists():
        print(f"ERROR: Source directory not found: {SOURCE_PB}")
        return

    if TARGET_PB.exists():
        print(f"Removing existing target: {TARGET_PB}")
        shutil.rmtree(TARGET_PB)

    # Copy the whole tree
    try:
        shutil.copytree(SOURCE_PB, TARGET_PB, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        print("Success: Copied project_builder")
    except Exception as e:
        print(f"Error copying tree: {e}")

if __name__ == "__main__":
    port_project_builder()
