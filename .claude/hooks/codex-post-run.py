#!/usr/bin/env python3
"""PostToolUse hook: surface git changes after Codex MCP tool runs.

Fires after mcp__codex-builder__codex completes. Runs git status and
diff --stat, then injects a systemMessage so Claude can see exactly
what Codex changed without a manual git status step.

Always exits 0 (informational — never blocks).
"""
import json
import os
import subprocess
import sys


PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())


def run_git(args: list[str]) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", PROJECT_DIR] + args,
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip()
    except Exception:
        return ""


def main() -> None:
    # Read hook input (tool_name, tool_input, tool_response) — ignored here,
    # we only care about the working-tree state after Codex ran.
    try:
        _ = json.load(sys.stdin)
    except Exception:
        pass

    status = run_git(["status", "--short"])
    diff_stat = run_git(["diff", "--stat", "HEAD"])

    if not status and not diff_stat:
        msg = "Codex run complete. Working tree is clean — no uncommitted changes."
    else:
        parts = ["Codex run complete. Working tree changes detected:"]
        if status:
            parts.append("\ngit status --short:\n" + status)
        if diff_stat:
            parts.append("\ngit diff --stat HEAD:\n" + diff_stat)
        parts.append(
            "\nReview with /review-build or fix in-place before committing."
        )
        msg = "\n".join(parts)

    print(json.dumps({"continue": True, "systemMessage": msg}))


if __name__ == "__main__":
    main()
