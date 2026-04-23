#!/usr/bin/env python3
"""
Stage and commit pending wiki updates.

Run after reviewing .context/wiki/_pending_diff.patch produced by refresh_wiki.py.
Stages all modified .context/wiki/*.md files and creates a commit.

Usage:
    python3 scripts/wiki/commit_wiki_update.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


WIKI_DIR_REL = ".context/wiki"
PENDING_DIFF = "_pending_diff.patch"


def _repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True
    )
    return Path(result.stdout.strip())


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, text=True, capture_output=True, **kwargs)


def main() -> int:
    repo_root = _repo_root()
    wiki_dir = repo_root / WIKI_DIR_REL
    pending = wiki_dir / PENDING_DIFF

    if not pending.exists() or pending.stat().st_size == 0:
        print("No pending wiki diff found. Nothing to commit.")
        return 0

    # Stage modified wiki pages (not the diff file itself)
    modified = []
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", str(wiki_dir)],
        capture_output=True, text=True, check=True
    )
    for line in result.stdout.splitlines():
        status = line[:2].strip()
        path = line[3:].strip()
        if status in {"M", "A", "??"} and path.endswith(".md") and PENDING_DIFF not in path:
            modified.append(path)

    if not modified:
        print("No modified wiki pages to stage.")
        pending.unlink()
        return 0

    _run(["git", "add"] + modified)

    # Count changed pages for commit message
    page_names = [Path(p).name for p in modified]
    summary = ", ".join(page_names[:3])
    if len(page_names) > 3:
        summary += f" (+{len(page_names) - 3} more)"

    msg = (
        f"chore(wiki): refresh {summary}\n\n"
        f"Auto-refreshed by scripts/wiki/refresh_wiki.py. "
        f"Human-reviewed diff in {PENDING_DIFF}.\n\n"
        f"Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
    )

    _run(["git", "commit", "-m", msg])
    print(f"Committed wiki update: {summary}")

    # Remove the pending diff after successful commit
    pending.unlink()
    print(f"Removed {PENDING_DIFF}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
