#!/usr/bin/env python3
"""
Safe Cleanup - Enforces Isolation-by-Default for untracked files.

This script prevents accidental deletion of work products by moving unclassified 
untracked files to an isolation vault instead of deleting them.

Usage:
    python scripts/safe_cleanup.py --isolate
    python scripts/safe_cleanup.py --delete --file <path> --manifest <manifest_path> --rationale "<reason>"
"""

import os
import sys
import shutil
import subprocess
import json
import hashlib
import argparse
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.resolve()
ISOLATION_VAULT = REPO_ROOT / "artifacts" / "99_archive" / "stray"
CLEANUP_LOG = REPO_ROOT / "logs" / "cleanup_ledger.jsonl"

def run_git(args):
    result = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=REPO_ROOT)
    return result.stdout.strip()

def get_untracked_files():
    # Only get untracked files, excluding ignored ones
    output = run_git(["ls-files", "--others", "--exclude-standard"])
    if not output:
        return []
    return [REPO_ROOT / f for f in output.split("\n")]

def get_hash(file_path):
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def log_action(action, file_path, target_path=None, rationale=None, manifest=None):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "file": str(Path(file_path).relative_to(REPO_ROOT)),
        "hash": get_hash(file_path) if Path(file_path).exists() else None,
        "target": str(Path(target_path).relative_to(REPO_ROOT)) if target_path else None,
        "rationale": rationale,
        "manifest": str(Path(manifest).relative_to(REPO_ROOT)) if manifest else None
    }
    with open(CLEANUP_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")

def isolate():
    files = get_untracked_files()
    if not files:
        print("✅ No untracked files to isolate.")
        return 0

    date_str = datetime.now().strftime("%Y%m%d")
    isolation_dir = ISOLATION_VAULT / date_str
    isolation_dir.mkdir(parents=True, exist_ok=True)

    print(f"📦 Isolating {len(files)} untracked file(s) to {isolation_dir}...")
    
    for f in files:
        target = isolation_dir / f.name
        # Ensure unique name in vault
        count = 1
        while target.exists():
            target = isolation_dir / f"{f.stem}_{count}{f.suffix}"
            count += 1
        
        log_action("isolate", f, target)
        shutil.move(str(f), str(target))
        print(f"   • {f.relative_to(REPO_ROOT)} -> {target.relative_to(REPO_ROOT)}")

    return 0

def delete_file(file_path, manifest, rationale):
    p = REPO_ROOT / file_path
    if not p.exists():
        print(f"❌ Error: File not found: {file_path}")
        return 1
    
    m = REPO_ROOT / manifest
    if not m.exists():
        print(f"❌ Error: Manifest not found: {manifest}")
        return 1

    # Simple check for manifest content
    manifest_content = m.read_text()
    if str(file_path) not in manifest_content:
        print(f"❌ Error: File {file_path} not found in manifest {manifest}")
        return 1

    print(f"🗑️  Deleting {file_path}...")
    log_action("delete", p, rationale=rationale, manifest=m)
    p.unlink()
    print("   • Deleted successfully.")
    return 0

def main():
    parser = argparse.ArgumentParser(description="Safe Cleanup Wrapper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--isolate", action="store_true", help="Move untracked files to vault")
    group.add_argument("--delete", action="store_true", help="Permanently delete a file (requires manifest)")
    
    parser.add_argument("--file", help="File to delete")
    parser.add_argument("--manifest", help="Path to Review Packet containing deletion manifest")
    parser.add_argument("--rationale", help="Rationale for deletion")

    args = parser.parse_args()

    if args.isolate:
        return isolate()
    
    if args.delete:
        if not all([args.file, args.manifest, args.rationale]):
            print("❌ Error: --delete requires --file, --manifest, and --rationale")
            return 1
        return delete_file(args.file, args.manifest, args.rationale)

if __name__ == "__main__":
    sys.exit(main())
