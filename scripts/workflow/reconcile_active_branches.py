#!/usr/bin/env python3
"""Reconcile active_branches.json against local git branches and live worktrees."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import git_workflow as gw


def _git_lines(repo_root: Path, args: list[str]) -> list[str]:
    code, stdout, _ = gw.run_git_in(repo_root, args)
    if code != 0:
        return []
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def _live_worktree_paths(repo_root: Path) -> set[str]:
    paths: set[str] = set()
    for line in _git_lines(repo_root, ["worktree", "list", "--porcelain"]):
        if line.startswith("worktree "):
            paths.add(line.split(" ", 1)[1].strip())
    return paths


def reconcile(data: dict, *, branch_names: set[str], live_worktrees: set[str]) -> tuple[dict, list[str]]:
    changes: list[str] = []
    rows_by_branch: dict[str, list[dict]] = {}
    for row in data.get("branches", []):
        rows_by_branch.setdefault(str(row.get("name", "")), []).append(row)

    for branch, rows in rows_by_branch.items():
        active_rows = [row for row in rows if row.get("status") == "active"]
        primary_active = None
        if branch in branch_names and active_rows:
            primary_active = max(active_rows, key=lambda row: str(row.get("created", "")))

        for row in rows:
            worktree_path = row.get("worktree_path")
            branch_exists = branch in branch_names

            if not branch_exists:
                if row.get("status") == "active":
                    row["status"] = "closed"
                    row.setdefault("closed_at", gw.datetime.now().isoformat())
                    changes.append(f"closed missing branch {branch}")
                if worktree_path:
                    row["worktree_path"] = None
                    changes.append(f"cleared missing branch worktree {branch}")
                continue

            if worktree_path and worktree_path not in live_worktrees:
                row["worktree_path"] = None
                changes.append(f"cleared stale worktree path for {branch}")

            if row is not primary_active and row.get("status") == "active":
                row["status"] = "closed"
                row.setdefault("closed_at", gw.datetime.now().isoformat())
                changes.append(f"closed duplicate active row for {branch}")

    if changes:
        gw._mark_registry_updated(data)
    return data, changes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="Repository root")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    data = gw.load_active_branches(repo_root)
    branch_names = set(_git_lines(repo_root, ["branch", "--format=%(refname:short)"]))
    live_worktrees = _live_worktree_paths(repo_root)
    data, changes = reconcile(data, branch_names=branch_names, live_worktrees=live_worktrees)

    if args.dry_run:
        if changes:
            print("\n".join(changes))
        else:
            print("No changes required.")
        return 0

    if changes:
        gw.save_active_branches(data, repo_root)
        print("\n".join(changes))
    else:
        print("No changes required.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
