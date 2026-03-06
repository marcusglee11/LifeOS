#!/usr/bin/env python3
"""One-time migration: create .git/lifeos/builds/ records from active_branches.json."""
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _git_stdout(args: list[str]) -> str:
    r = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args], capture_output=True, text=True
    )
    return r.stdout.strip() if r.returncode == 0 else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing")
    args = parser.parse_args()

    active_branches_path = REPO_ROOT / "artifacts" / "active_branches.json"
    if not active_branches_path.exists():
        print("artifacts/active_branches.json not found")
        return 1

    data = json.loads(active_branches_path.read_text())
    branches = data.get("branches", [])

    git_common_raw = _git_stdout(["rev-parse", "--git-common-dir"])
    if not git_common_raw:
        print("Cannot resolve git common dir")
        return 1

    git_common = Path(git_common_raw)
    if not git_common.is_absolute():
        git_common = REPO_ROOT / git_common

    record_dir = git_common / "lifeos" / "builds"
    migrated: list[str] = []
    skipped: list[str] = []
    already_exist: list[str] = []

    for b in branches:
        name = b.get("name", "")
        if not name or "/" not in name:
            skipped.append(f"{name!r} (invalid name)")
            continue

        ref_check = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "show-ref", "--verify", "--quiet",
             f"refs/heads/{name}"],
            capture_output=True,
        )
        if ref_check.returncode != 0:
            skipped.append(f"{name} (branch gone)")
            continue

        slug = name.replace("/", "__")
        record_path = record_dir / f"{slug}.json"
        if record_path.exists():
            already_exist.append(name)
            continue

        kind = name.split("/")[0]
        topic = name.split("/", 1)[1]
        record = {
            "version": 1,
            "branch": name,
            "kind": kind,
            "topic": topic,
            "entrypoint": "migrate",
            "created_at_utc": b.get("created", datetime.now(timezone.utc).isoformat()),
            "primary_repo": str(REPO_ROOT),
            "worktree_path": b.get("worktree_path", ""),
            "status": "active",
        }
        if not args.dry_run:
            record_dir.mkdir(parents=True, exist_ok=True)
            record_path.write_text(json.dumps(record, indent=2, sort_keys=True))
        migrated.append(name)

    prefix = "[DRY RUN] " if args.dry_run else ""
    gone = [s for s in skipped if "gone" in s]
    print(f"{prefix}Migrated: {len(migrated)} — {migrated}")
    print(f"{prefix}Skipped (branch gone): {len(gone)} — {gone}")
    print(f"{prefix}Already exist: {len(already_exist)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
