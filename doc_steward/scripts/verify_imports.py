import sys
import os
from pathlib import Path

ROOT = Path(r"c:\Users\cabra\Projects\LifeOS")

def verify_imports():
    print(f"Verifying imports in {ROOT}...")
    sys.path.append(str(ROOT))
    
    try:
        import runtime
        print("SUCCESS: import runtime")
        print(f"  - runtime found at: {runtime.__file__}")
    except ImportError as e:
        print(f"FAILURE: import runtime ({e})")

    try:
        import project_builder
        print("SUCCESS: import project_builder")
        print(f"  - project_builder found at: {project_builder.__file__}")
    except ImportError as e:
        print(f"FAILURE: import project_builder ({e})")
        
    try:
        from runtime import engine
        print("SUCCESS: from runtime import engine")
    except ImportError as e:
        print(f"FAILURE: from runtime import engine ({e})")

if __name__ == "__main__":
    verify_imports()
