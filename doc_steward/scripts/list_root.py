import os
from pathlib import Path

ROOT = Path(r"c:\Users\cabra\Projects\LifeOS")

def list_root():
    print(f"Listing {ROOT}...")
    try:
        for f in os.listdir(ROOT):
            full = ROOT / f
            if full.is_file():
                print(f"FILE: {f}")
            else:
                print(f"DIR:  {f}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_root()
