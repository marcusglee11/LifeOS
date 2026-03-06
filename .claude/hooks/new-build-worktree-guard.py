#!/usr/bin/env python3
"""PreToolUse hook: block direct build branch creation in primary tree.

Redirects to start_build.py for proper worktree isolation and registration.
"""

import json
import os
import re
import sys

BRANCH_CREATE_RE = re.compile(
    r"git\s+(checkout\s+-b|switch\s+-c)\s+(build|fix|hotfix|spike)/"
)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    command = payload.get("tool_input", {}).get("command", "")
    if BRANCH_CREATE_RE.search(command):
        print(json.dumps({
            "decision": "block",
            "reason": "Use start_build.py instead: python3 scripts/workflow/start_build.py <topic>. This ensures proper worktree isolation and build record registration."
        }))
        sys.exit(2)

    print(json.dumps({"decision": "allow"}))
    sys.exit(0)


if __name__ == "__main__":
    main()
