#!/usr/bin/env python3
"""PostToolUse hook: warn when a build branch is created in a dirty primary tree.

Always exits 0 (advisory only). Fast-paths non-Bash and non-branch-create calls.
"""

import json
import os
import re
import subprocess
import sys


PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
BRANCH_CREATE_RE = re.compile(
    r"git\s+(checkout\s+-b|switch\s+-c)\s+(build|fix|hotfix|spike)/\S+"
)


def run_git(args: list[str]) -> str:
    try:
        proc = subprocess.run(
            ["git", "-C", PROJECT_DIR] + args,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return proc.stdout.strip()
    except Exception:
        return ""


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        data = {}

    if data.get("tool_name") != "Bash":
        print(json.dumps({"continue": True, "systemMessage": ""}))
        return

    command = (data.get("tool_input") or {}).get("command", "")
    if not BRANCH_CREATE_RE.search(command):
        print(json.dumps({"continue": True, "systemMessage": ""}))
        return

    common_dir = run_git(["rev-parse", "--git-common-dir"])
    if common_dir != ".git":
        print(json.dumps({"continue": True, "systemMessage": ""}))
        return

    status = run_git(["status", "--porcelain", "-uall"])
    untracked = sum(1 for line in status.splitlines() if line.startswith("??"))

    if untracked < 1:
        print(json.dumps({"continue": True, "systemMessage": ""}))
        return

    msg = (
        f"⚠️  WORKTREE RECOMMENDED — {untracked} untracked file(s) in primary "
        "working tree.\n"
        "Use instead: python3 scripts/workflow/start_build.py <topic> [--kind fix|hotfix|spike]\n"
        "If you already started work in primary: python3 scripts/workflow/start_build.py --recover-primary\n"
        "Shared tree risks Article XIX blocks from concurrent agent artifacts."
    )
    print(json.dumps({"continue": True, "systemMessage": msg}))


if __name__ == "__main__":
    main()
