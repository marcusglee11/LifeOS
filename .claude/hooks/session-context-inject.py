#!/usr/bin/env python3
"""SessionStart hook: inject project state context into Claude Code session.

Gathers git branch, status summary, and key fields from LIFEOS_STATE.md.
Outputs {"additionalContext": "..."} JSON to stdout.
Always exits 0 (never blocks session start).
"""

import json
import os
import re
import subprocess
import sys


PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
STATE_FILE = os.path.join(PROJECT_DIR, "docs", "11_admin", "LIFEOS_STATE.md")
MAX_CONTEXT_CHARS = 600


def run_git(args: list[str], timeout: int = 3) -> str:
    """Run a git command, return stdout or empty string on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", PROJECT_DIR] + args,
            capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def git_context() -> str:
    """Return compact git branch + status summary."""
    branch = run_git(["rev-parse", "--abbrev-ref", "HEAD"]) or "unknown"
    status_raw = run_git(["status", "--porcelain"])

    if not status_raw:
        status = "clean"
    else:
        lines = status_raw.splitlines()
        status = f"{len(lines)} changed file(s)"

    return f"Branch: {branch} | Status: {status}"


def state_context() -> str:
    """Extract key fields from LIFEOS_STATE.md."""
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return ""

    fields = []
    for pattern in [
        r"\*\*Current Focus:\*\*\s*(.+)",
        r"\*\*Active WIP:\*\*\s*(.+)",
    ]:
        m = re.search(pattern, content)
        if m:
            fields.append(m.group(1).strip())

    # Extract the "Next immediate" one-liner
    next_match = re.search(r"\*\*Next immediate:\*\*\s*(.+)", content)

    if next_match:
        fields.append("Next: " + next_match.group(1).strip())

    return " | ".join(fields)


def main() -> int:
    parts = []

    git = git_context()
    if git:
        parts.append(git)

    state = state_context()
    if state:
        parts.append(state)

    if not parts:
        # Nothing to inject
        print(json.dumps({"additionalContext": ""}))
        return 0

    context = " || ".join(parts)

    # Cap to avoid token waste
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[: MAX_CONTEXT_CHARS - 3] + "..."

    output = {"additionalContext": context}
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
