#!/usr/bin/env python3
"""
Safe Cleanup - Enforces Isolation-by-Default for untracked files.

This script prevents accidental deletion of work products by moving unclassified 
untracked files to an isolation vault instead of deleting them.

Usage:
    python scripts/safe_cleanup.py --isolate
    python scripts/safe_cleanup.py --isolate --apply --rationale "why isolation is needed"
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
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).parent.parent.resolve()
ISOLATION_VAULT = REPO_ROOT / "artifacts" / "99_archive" / "stray"
CLEANUP_LOG = REPO_ROOT / "logs" / "cleanup_ledger.jsonl"
PROTECTED_PREFIXES = (".github/", "runtime/", "scripts/", "tests/", "docs/")


def run_git(args: List[str], repo_root: Path = REPO_ROOT) -> str:
    result = subprocess.run(["git"] + args, capture_output=True, text=True, cwd=repo_root)
    return result.stdout.strip()


def get_untracked_files(repo_root: Path = REPO_ROOT) -> List[Path]:
    # Only get untracked files, excluding ignored ones
    output = run_git(["ls-files", "--others", "--exclude-standard"], repo_root=repo_root)
    if not output:
        return []
    return [repo_root / f for f in output.split("\n")]


def get_hash(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _relative_to_repo(path: Path, repo_root: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve()))


def _best_effort_parent_cmd(ppid: int) -> Optional[str]:
    if ppid <= 0:
        return None
    try:
        result = subprocess.run(
            ["ps", "-o", "command=", "-p", str(ppid)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return None
        output = result.stdout.strip()
        return output if output else None
    except Exception:
        return None


def _invoker_info() -> Dict[str, Any]:
    ppid = os.getppid()
    return {
        "pid": os.getpid(),
        "ppid": ppid,
        "argv": list(sys.argv),
        "parent_cmd": _best_effort_parent_cmd(ppid),
    }


def is_protected_path(file_path: Path, repo_root: Path = REPO_ROOT) -> bool:
    rel = file_path.resolve().relative_to(repo_root.resolve()).as_posix()
    return any(rel.startswith(prefix) for prefix in PROTECTED_PREFIXES)


def log_action(
    action: str,
    file_path: Path,
    repo_root: Path,
    target_path: Optional[Path] = None,
    rationale: Optional[str] = None,
    manifest: Optional[Path] = None,
) -> None:
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "file": _relative_to_repo(Path(file_path), repo_root),
        "hash": get_hash(file_path) if Path(file_path).exists() else None,
        "target": _relative_to_repo(Path(target_path), repo_root) if target_path else None,
        "rationale": rationale,
        "manifest": _relative_to_repo(Path(manifest), repo_root) if manifest else None,
        "invoker": _invoker_info(),
    }
    CLEANUP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(CLEANUP_LOG, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(entry) + "\n")


def isolate(
    *,
    apply: bool,
    rationale: Optional[str],
    allow_protected: bool,
    repo_root: Path = REPO_ROOT,
) -> int:
    files = get_untracked_files(repo_root=repo_root)
    if not files:
        print("✅ No untracked files to isolate.")
        return 0

    protected = [f for f in files if is_protected_path(f, repo_root=repo_root)]
    if protected and not allow_protected:
        print("🚫 BLOCKED: Protected paths detected in isolate candidate set.")
        for path in protected:
            print(f"   • {path.relative_to(repo_root)}")
        print("")
        print("Stage these files instead, or rerun with --allow-protected when intentional.")
        return 1

    if not apply:
        print(f"🔍 Dry run: {len(files)} untracked file(s) would be isolated.")
        for path in files:
            print(f"   • {path.relative_to(repo_root)}")
        print("")
        print("No files moved. Re-run with --apply --rationale \"...\" to isolate.")
        return 0

    if not rationale:
        print("❌ Error: --isolate --apply requires --rationale")
        return 1

    date_str = datetime.now().strftime("%Y%m%d")
    isolation_dir = (repo_root / "artifacts" / "99_archive" / "stray" / date_str).resolve()
    isolation_dir.mkdir(parents=True, exist_ok=True)

    print(f"📦 Isolating {len(files)} untracked file(s) to {isolation_dir}...")

    for f in files:
        target = isolation_dir / f.name
        # Ensure unique name in vault
        count = 1
        while target.exists():
            target = isolation_dir / f"{f.stem}_{count}{f.suffix}"
            count += 1

        log_action("isolate", f, repo_root=repo_root, target_path=target, rationale=rationale)
        shutil.move(str(f), str(target))
        print(f"   • {f.relative_to(repo_root)} -> {target.relative_to(repo_root)}")

    return 0


def delete_file(file_path: str, manifest: str, rationale: str, repo_root: Path = REPO_ROOT) -> int:
    p = repo_root / file_path
    if not p.exists():
        print(f"❌ Error: File not found: {file_path}")
        return 1

    m = repo_root / manifest
    if not m.exists():
        print(f"❌ Error: Manifest not found: {manifest}")
        return 1

    # Simple check for manifest content
    manifest_content = m.read_text(encoding="utf-8")
    if str(file_path) not in manifest_content:
        print(f"❌ Error: File {file_path} not found in manifest {manifest}")
        return 1

    print(f"🗑️  Deleting {file_path}...")
    log_action("delete", p, repo_root=repo_root, rationale=rationale, manifest=m)
    p.unlink()
    print("   • Deleted successfully.")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Safe Cleanup Wrapper")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--isolate", action="store_true", help="Isolate untracked files (dry-run unless --apply)")
    group.add_argument("--delete", action="store_true", help="Permanently delete a file (requires manifest)")

    parser.add_argument("--apply", action="store_true", help="Apply isolation (required to mutate)")
    parser.add_argument("--allow-protected", action="store_true", help="Allow isolation of protected paths")
    parser.add_argument("--file", help="File to delete")
    parser.add_argument("--manifest", help="Path to Review Packet containing deletion manifest")
    parser.add_argument("--rationale", help="Rationale for isolate/apply or deletion")

    args = parser.parse_args(argv)

    if args.isolate:
        if args.apply and not args.rationale:
            print("❌ Error: --isolate --apply requires --rationale")
            return 1
        return isolate(
            apply=args.apply,
            rationale=args.rationale,
            allow_protected=args.allow_protected,
            repo_root=REPO_ROOT,
        )

    if args.delete:
        if not all([args.file, args.manifest, args.rationale]):
            print("❌ Error: --delete requires --file, --manifest, and --rationale")
            return 1
        return delete_file(args.file, args.manifest, args.rationale, repo_root=REPO_ROOT)

    return 1

if __name__ == "__main__":
    sys.exit(main())
